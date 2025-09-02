import json
import math
import os
import subprocess
import asyncio
from typing import List, Dict, Any

import requests
from elasticsearch import Elasticsearch
from langchain_core.tools import tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from models import VesselData, WebSearchResult


# Haversine distance calculation
def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth in miles."""
    R = 3959  # Earth's radius in miles
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

# MCP Chrome Bridge Wrapper
class MCPChromeClient:
    def __init__(self, config_path: str = "config/mcp_desktop_config.json", llm=None):
        self.config_path = config_path
        self.llm = llm  # LLM for intelligent navigation
        self.server_params = StdioServerParameters(
            command="node",
            args=["/opt/homebrew/lib/node_modules/mcp-chrome-bridge/dist/mcp/mcp-server-stdio.js"],
            env={}
        )
    
    async def _call_mcp_async(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call MCP Chrome bridge with given method and parameters asynchronously."""
        if params is None:
            params = {}
        
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # List available tools to verify connection (only on first call)
                    if not hasattr(self, '_tools_listed'):
                        tools = await session.list_tools()
                        print(f"Available MCP tools: {[tool.name for tool in tools.tools]}")
                        self._tools_listed = True
                    
                    # Call the tool
                    result = await session.call_tool(method, params)
                    
                    # Parse the result from TextContent objects
                    parsed_result = None
                    if hasattr(result, 'content') and isinstance(result.content, list):
                        for content_item in result.content:
                            if hasattr(content_item, 'text'):
                                try:
                                    # Try to parse as JSON first
                                    import json
                                    text_content = content_item.text
                                    parsed_data = json.loads(text_content)
                                    
                                    # Extract the actual data from the response structure
                                    if isinstance(parsed_data, dict):
                                        if "data" in parsed_data:
                                            parsed_result = parsed_data["data"]
                                        elif "elements" in parsed_data:
                                            parsed_result = {"elements": parsed_data["elements"]}
                                        elif "content" in parsed_data:
                                            parsed_result = {"content": parsed_data["content"]}
                                        else:
                                            parsed_result = parsed_data
                                    else:
                                        parsed_result = parsed_data
                                    break
                                except json.JSONDecodeError:
                                    # If not JSON, use the text directly
                                    parsed_result = content_item.text
                                    break
                    
                    if parsed_result is None:
                        parsed_result = result.content
                    
                    return {"result": parsed_result}
                    
        except Exception as e:
            return {"error": f"MCP call failed: {str(e)}"}
    
    def _call_mcp(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronous wrapper for async MCP calls."""
        return asyncio.run(self._call_mcp_async(method, params))
    
    def intelligent_search_and_navigate(self, query: str, research_focus: str = "specifications") -> List[WebSearchResult]:
        """LLM-driven search that focuses on the first relevant result."""
        results = []
        
        try:
            print(f"🔍 LLM-guided search for: {query}")
            
            # Navigate to Google search
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            search_result = self._call_mcp("chrome_navigate", {"url": search_url})
            
            if "error" in search_result:
                print(f"❌ Search navigation failed: {search_result['error']}")
                return [WebSearchResult(url="error", content_snippet=search_result["error"])]
            
            print("✅ Navigated to Google search")
            
            # Get interactive elements
            links_result = self._call_mcp("chrome_get_interactive_elements")
            
            if "error" in links_result or "result" not in links_result or not links_result["result"]:
                print(f"❌ Failed to get elements")
                return [WebSearchResult(url="error", content_snippet="Failed to get search results")]
            
            # Extract search result elements
            elements_data = links_result["result"]
            if isinstance(elements_data, dict) and ("elements" in elements_data or "content" in elements_data):
                elements = elements_data.get("elements", elements_data.get("content", []))
            elif isinstance(elements_data, list):
                elements = elements_data
            else:
                elements = []
            
            # Filter search result links using broader criteria like your grep approach
            search_result_elements = []
            skip_terms = ["sign in", "images", "videos", "news", "shopping", "more", "tools", "settings"]

            nested_json = json.loads(elements[0].get("text", "{}"))
            elements = nested_json.get("elements", [])
            for element in elements:
                if isinstance(element, dict):
                    text = element.get("text", "")
                    elem_type = element.get("type", "")
                    selector = element.get("selector", "")

                    # Look for the first clickable link with 'http' or 'www.' and substantial text
                    if (elem_type == "link" and
                            element.get("isInteractive", False) and
                            not element.get("disabled", True) and
                            text and
                            len(text) > 20 and
                            ("http" in text.lower() or "www." in text.lower()) and
                            not any(skip in text.lower() for skip in skip_terms)):
                        search_result_elements.append({
                            "selector": selector,
                            "text": text[:300],
                            "type": elem_type
                        })
                        break  # Stop after the first match

            print(f"🔍 Debug - Found clickable elements with 'http':")
            for i, elem in enumerate(search_result_elements):
                print(f"  {i}: {elem['text'][:100]}...")
                print(f"     Selector: {elem['selector']}")
            print()

            if not search_result_elements:
                print("❌ No relevant search results found")
                return [WebSearchResult(url="error", content_snippet="No relevant search results")]
            
            print(f"📄 Found {len(search_result_elements)} search results")
            
            # LLM selects the best result
            if self.llm and len(search_result_elements) > 1:
                selection = self._llm_select_best_result(search_result_elements, research_focus)
                selected_index = selection.get("selected_index", 0)
            else:
                selected_index = 0
            
            if selected_index >= len(search_result_elements):
                selected_index = 0
            
            # Click on the selected result
            selected_element = search_result_elements[selected_index]
            print(f"🎯 LLM selected: {selected_element['text'][:50]}...")
            
            try:
                click_result = self._call_mcp("chrome_click_element", {
                    "selector": selected_element["selector"]
                })
                
                if "error" not in click_result:
                    import time
                    time.sleep(3)  # Wait for page load
                    
                    # Get current URL and content
                    url_result = self._call_mcp("get_windows_and_tabs")
                    current_url = "unknown"
                    if "result" in url_result and url_result["result"]:
                        tabs_data = url_result["result"]
                        if isinstance(tabs_data, dict) and "tabs" in tabs_data:
                            tabs = tabs_data["tabs"]
                            if tabs and len(tabs) > 0:
                                current_url = tabs[0].get("url", "unknown")
                    
                    content_result = self._call_mcp("chrome_get_web_content")
                    content = ""
                    if "result" in content_result and content_result["result"]:
                        content_obj = content_result["result"]
                        if isinstance(content_obj, dict) and "content" in content_obj:
                            content_list = content_obj["content"]
                            if isinstance(content_list, list):
                                content_parts = []
                                for item in content_list[:10]:
                                    if isinstance(item, dict) and "text" in item:
                                        content_parts.append(item["text"])
                                content = " ".join(content_parts)[:2000]
                    
                    if content and len(content) > 100 and "google.com" not in current_url:
                        result = WebSearchResult(
                            url=current_url,
                            title=selected_element["text"],
                            content_snippet=content,
                            images_found=[]
                        )
                        results.append(result)
                        print(f"✅ Successfully extracted {len(content)} chars from {current_url[:50]}...")
                    else:
                        print("⚠️ Page content insufficient or still on search page")
                        
            except Exception as e:
                print(f"❌ Error processing selected result: {str(e)}")
            
        except Exception as e:
            print(f"❌ Search operation failed: {str(e)}")
            results.append(WebSearchResult(
                url="error", 
                content_snippet=f"Search failed: {str(e)}"
            ))
        
        return results
    
    def _llm_select_best_result(self, search_results: List[Dict], research_focus: str) -> Dict:
        """LLM selects the most relevant search result."""
        if not self.llm:
            return {"selected_index": 0}
        
        results_text = ""
        for i, result in enumerate(search_results[:5]):  # Top 5 results
            results_text += f"{i}: {result['text']}\n"
        
        selection_prompt = f"""
        Select the best search result for vessel research focused on: {research_focus}
        
        Available results:
        {results_text}
        
        Prioritize in this order:
        1. Marine Traffic (marinetraffic.com) - vessel tracking/specs
        2. Official shipping companies or vessel operators
        3. VesselFinder or similar vessel databases
        4. Maritime industry sites
        5. Wikipedia (last resort)
        
        Respond with just the number (0-{len(search_results)-1}) of the best result.
        """
        
        try:
            response = self.llm.invoke([
                ("system", "You are a research expert. Select the most authoritative source."),
                ("user", selection_prompt)
            ])
            
            # Extract number from response
            content = response.content.strip()
            for char in content:
                if char.isdigit():
                    index = int(char)
                    if 0 <= index < len(search_results):
                        return {"selected_index": index}
            
        except Exception as e:
            print(f"⚠️ LLM selection failed: {e}")
        
        return {"selected_index": 0}

# Initialize MCP client
mcp_client = MCPChromeClient()

@tool
def search_vessels_by_distance(min_distance_miles: float = 50.0, date: str = "2022-01-01") -> List[VesselData]:
    """Search for vessels with long tracks on a specific date."""
    es = Elasticsearch(["http://localhost:9200"])
    
    # Query all vessels for the specified date
    query = {
        "query": {
            "range": {
                "BaseDateTime": {
                    "gte": f"{date}T00:00:00",
                    "lte": f"{date}T23:59:59"
                }
            }
        },
        "sort": [{"BaseDateTime": {"order": "asc"}}],
        "size": 10000
    }
    
    response = es.search(index="vessel_index", body=query)
    
    # Group by vessel (MMSI)
    vessel_tracks = {}
    for hit in response["hits"]["hits"]:
        data = hit["_source"]
        mmsi = data["MMSI"]
        
        if mmsi not in vessel_tracks:
            vessel_tracks[mmsi] = VesselData(
                mmsi=mmsi,
                vessel_name=data.get("VesselName", ""),
                imo=data.get("IMO", ""),
                call_sign=data.get("CallSign", ""),
                vessel_type=data.get("VesselType", ""),
                length=data.get("Length"),
                width=data.get("Width"),
                draft=data.get("Draft"),
                track_points=[]
            )
        
        vessel_tracks[mmsi].track_points.append({
            "timestamp": data["BaseDateTime"],
            "lat": data["LAT"],
            "lon": data["LON"],
            "sog": data.get("SOG", 0),
            "cog": data.get("COG", 0),
            "heading": data.get("Heading", 0)
        })
    
    # Calculate distances for each vessel
    long_distance_vessels = []
    for vessel in vessel_tracks.values():
        if len(vessel.track_points) > 1:
            # Sort by timestamp
            vessel.track_points.sort(key=lambda x: x["timestamp"])
            
            # Calculate total distance
            total_distance = 0.0
            for i in range(1, len(vessel.track_points)):
                prev_point = vessel.track_points[i-1]
                curr_point = vessel.track_points[i]
                
                distance = calculate_distance_miles(
                    prev_point["lat"], prev_point["lon"],
                    curr_point["lat"], curr_point["lon"]
                )
                total_distance += distance
            
            vessel.total_distance_miles = total_distance
            
            # Filter by minimum distance
            if total_distance >= min_distance_miles:
                long_distance_vessels.append(vessel)
    
    # Sort by distance (descending) and return top 10
    long_distance_vessels.sort(key=lambda x: x.total_distance_miles, reverse=True)
    return long_distance_vessels[:10]

@tool
def web_research_vessel(vessel_name: str, mmsi: str, imo: str = "", research_focus: str = "specifications") -> List[WebSearchResult]:
    """Research vessel information using LLM-guided web search."""
    search_terms = [vessel_name]
    if mmsi:
        search_terms.append(f"MMSI {mmsi}")
    if imo and imo != "IMO0000000":
        search_terms.append(f"IMO {imo}")
    
    query = " ".join(search_terms) + " ship vessel specifications"
    return mcp_client.intelligent_search_and_navigate(query, research_focus)

@tool
def download_vessel_image(image_url: str, vessel_name: str) -> str:
    """Download vessel image from URL."""
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        if response.status_code == 200:
            # Create images directory if not exists
            os.makedirs("reports/images", exist_ok=True)
            
            # Generate filename
            safe_name = "".join(c for c in vessel_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"reports/images/{safe_name}_{hash(image_url) % 10000}.jpg"
            
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filename
    except Exception as e:
        return f"Download failed: {str(e)}"
    
    return "Download failed"
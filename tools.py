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

VESSEL_INDEX = "ais_data"


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
        """LLM-driven search that focuses on the first relevant result with cookie handling."""
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
            
            # Extract and parse elements with improved nesting handling
            elements_data = links_result["result"]
            elements = []
            
            # Handle different response structures
            if isinstance(elements_data, dict):
                if "elements" in elements_data:
                    elements = elements_data["elements"]
                elif "content" in elements_data:
                    content = elements_data["content"]
                    if isinstance(content, list) and len(content) > 0:
                        # Try to parse nested JSON from first item
                        first_item = content[0]
                        if isinstance(first_item, dict) and "text" in first_item:
                            try:
                                nested_json = json.loads(first_item["text"])
                                elements = nested_json.get("elements", [])
                            except json.JSONDecodeError:
                                elements = content
                        else:
                            elements = content
            elif isinstance(elements_data, list):
                elements = elements_data
                # Check if first element contains nested JSON
                if len(elements) > 0 and isinstance(elements[0], dict) and "text" in elements[0]:
                    try:
                        nested_json = json.loads(elements[0]["text"])
                        elements = nested_json.get("elements", elements)
                    except json.JSONDecodeError:
                        pass  # Keep original elements
            
            # Filter search result links
            search_result_elements = []
            skip_terms = ["sign in", "images", "videos", "news", "shopping", "more", "tools", "settings"]
            
            for element in elements:
                if isinstance(element, dict):
                    text = element.get("text", "")
                    elem_type = element.get("type", "")
                    selector = element.get("selector", "")

                    # Look for clickable links with substantial text
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

            print(f"🔍 Found {len(search_result_elements)} clickable search results")
            for i, elem in enumerate(search_result_elements[:3]):
                print(f"  [{i}]: {elem['text'][:80]}...")

            if not search_result_elements:
                print("❌ No relevant search results found")
                return [WebSearchResult(url="error", content_snippet="No relevant search results")]
            
            # LLM selects the best result
            if self.llm and len(search_result_elements) > 1:
                selection = self._llm_select_best_result(search_result_elements, research_focus)
                selected_index = selection.get("selected_index", 0)
            else:
                selected_index = 0
            
            if selected_index >= len(search_result_elements):
                selected_index = 0
            
            # Click on the selected result and handle page content
            selected_element = search_result_elements[selected_index]
            print(f"🎯 Selected: {selected_element['text'][:50]}...")
            
            return self._navigate_and_extract_content(selected_element, query)
                        
        except Exception as e:
            print(f"❌ Search operation failed: {str(e)}")
            results.append(WebSearchResult(
                url="error", 
                content_snippet=f"Search failed: {str(e)}"
            ))
        
        return results
    
    def _navigate_and_extract_content(self, selected_element: Dict, query: str) -> List[WebSearchResult]:
        """Navigate to selected result and extract content with cookie handling."""
        results = []
        
        try:
            click_result = self._call_mcp("chrome_click_element", {
                "selector": selected_element["selector"]
            })
            
            if "error" not in click_result:
                import time
                time.sleep(3)  # Wait for page load
                
                # Check for cookie dialogs and handle them
                self._handle_cookie_dialogs()
                
                # Get current URL
                url_result = self._call_mcp("get_windows_and_tabs")
                current_url = "unknown"
                if "result" in url_result and url_result["result"]:
                    tabs_data = url_result["result"]
                    if isinstance(tabs_data, dict) and "tabs" in tabs_data:
                        tabs = tabs_data["tabs"]
                        if tabs and len(tabs) > 0:
                            current_url = tabs[0].get("url", "unknown")
                
                # Extract content
                content_result = self._call_mcp("chrome_get_web_content")
                raw_content = ""
                if "result" in content_result and content_result["result"]:
                    content_obj = content_result["result"]
                    if isinstance(content_obj, dict) and "content" in content_obj:
                        content_list = content_obj["content"]
                        if isinstance(content_list, list):
                            content_parts = []
                            for item in content_list[:15]:  # More content for better analysis
                                if isinstance(item, dict) and "text" in item:
                                    content_parts.append(item["text"])
                            raw_content = " ".join(content_parts)[:5000]  # Larger limit
                
                if raw_content and len(raw_content) > 100 and "google.com" not in current_url:
                    # Use LLM to create compact technical analysis
                    analyzed_content = self._create_technical_analysis(raw_content, query)
                    
                    result = WebSearchResult(
                        url=current_url,
                        title=selected_element["text"],
                        content_snippet=analyzed_content,
                        images_found=[]
                    )
                    results.append(result)
                    print(f"✅ Extracted and analyzed content from {current_url[:50]}...")
                else:
                    print("⚠️ Insufficient page content or still on search page")
                    
        except Exception as e:
            print(f"❌ Error navigating to result: {str(e)}")
            
        return results
    
    def _handle_cookie_dialogs(self):
        """Detect and handle cookie acceptance dialogs."""
        try:
            # Look for common cookie dialog elements
            elements_result = self._call_mcp("chrome_get_interactive_elements")
            
            if "result" in elements_result and elements_result["result"]:
                elements_data = elements_result["result"]
                
                # Parse elements similar to main function
                elements = []
                if isinstance(elements_data, dict):
                    if "elements" in elements_data:
                        elements = elements_data["elements"]
                    elif "content" in elements_data:
                        content = elements_data["content"]
                        if isinstance(content, list) and len(content) > 0:
                            first_item = content[0]
                            if isinstance(first_item, dict) and "text" in first_item:
                                try:
                                    nested_json = json.loads(first_item["text"])
                                    elements = nested_json.get("elements", [])
                                except json.JSONDecodeError:
                                    elements = content
                
                # Look for cookie-related buttons
                cookie_terms = ["accept", "allow", "agree", "consent", "continue", "ok", "got it"]
                
                for element in elements:
                    if isinstance(element, dict):
                        text = element.get("text", "").lower()
                        elem_type = element.get("type", "")
                        selector = element.get("selector", "")
                        
                        if (elem_type == "button" and
                            element.get("isInteractive", False) and
                            any(term in text for term in cookie_terms) and
                            len(text) < 50):  # Keep it short - likely a cookie button
                            
                            print(f"🍪 Found cookie dialog button: {text}")
                            self._call_mcp("chrome_click_element", {"selector": selector})
                            import time
                            time.sleep(2)  # Wait after clicking
                            break
                            
        except Exception as e:
            print(f"⚠️ Cookie dialog handling failed: {e}")
    
    def _create_technical_analysis(self, content: str, query: str) -> str:
        """Use LLM to create compact technical analysis of extracted content."""
        if not self.llm:
            return content[:1500]  # Fallback to truncated content
        
        analysis_prompt = f"""
        Create a concise technical analysis of this vessel information.
        
        Search Query: {query}
        Content: {content}
        
        Format as itemized technical specifications focusing on:
        • Vessel specifications (length, beam, draft, tonnage)
        • Propulsion and performance data
        • Operational details and capabilities
        • Construction and classification info
        • Current status and ownership
        
        Keep response under 800 characters. Use bullet points. Be precise and technical.
        """
        
        try:
            response = self.llm.invoke([
                ("system", "You are a maritime technical analyst. Extract key vessel specifications concisely."),
                ("user", analysis_prompt)
            ])
            
            analyzed = response.content.strip()
            return analyzed if len(analyzed) > 50 else content[:1500]
            
        except Exception as e:
            print(f"⚠️ LLM analysis failed: {e}")
            return content[:1500]
    
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
def search_vessels_by_distance(min_distance_miles: float = 50.0, date: str = "2022-01-01", scroll_batches: int = 3) -> List[VesselData]:
    """Search for vessels with long tracks using geohash grid aggregation and scroll API processing."""
    from typing import Dict, Set
    
    es = Elasticsearch(["http://localhost:9200"], timeout=60, max_retries=3)
    
    # Geohash precision 5 gives ~4.9km x 4.9km cells
    geohash_query = {
        "query": {
            "range": {
                "BaseDateTime": {
                    "gte": f"{date}T00:00:00",
                    "lte": f"{date}T23:59:59"
                }
            }
        },
        "size": 0,
        "aggs": {
            "vessels": {
                "terms": {
                    "field": "MMSI.keyword",
                    "size": 1000  # Process 1000 vessels per scroll batch
                },
                "aggs": {
                    "vessel_info": {
                        "top_hits": {
                            "size": 1,
                            "_source": ["VesselName", "IMO", "CallSign", "VesselType", "Length", "Width", "Draft"]
                        }
                    },
                    "geohash_grid": {
                        "geohash_grid": {
                            "field": "location",  # Assuming geo_point field exists
                            "precision": 5
                        },
                        "aggs": {
                            "representative_point": {
                                "top_hits": {
                                    "size": 1,
                                    "sort": [{"BaseDateTime": {"order": "asc"}}],
                                    "_source": ["BaseDateTime", "LAT", "LON"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Fallback query if location field doesn't exist - use LAT/LON directly
    fallback_query = {
        "query": {
            "range": {
                "BaseDateTime": {
                    "gte": f"{date}T00:00:00",
                    "lte": f"{date}T23:59:59"
                }
            }
        },
        "size": 0,
        "aggs": {
            "vessels": {
                "terms": {
                    "field": "MMSI.keyword",
                    "size": 1000
                },
                "aggs": {
                    "vessel_info": {
                        "top_hits": {
                            "size": 1,
                            "_source": ["VesselName", "IMO", "CallSign", "VesselType", "Length", "Width", "Draft"]
                        }
                    },
                    "geohash_grid": {
                        "geohash_grid": {
                            "field": "LAT",  # Use LAT field for geohash if no geo_point
                            "precision": 5
                        },
                        "aggs": {
                            "representative_point": {
                                "top_hits": {
                                    "size": 1,
                                    "sort": [{"BaseDateTime": {"order": "asc"}}],
                                    "_source": ["BaseDateTime", "LAT", "LON"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    all_vessels: Dict[str, Dict] = {}
    processed_batches = 0
    
    try:
        # First attempt with geo_point field
        try:
            response = es.search(index=("%s" % VESSEL_INDEX), body=geohash_query)
            current_query = geohash_query
        except Exception:
            # Fallback to LAT field for geohash
            print("Using fallback geohash query with LAT field")
            response = es.search(index=VESSEL_INDEX, body=fallback_query)
            current_query = fallback_query
            
        # Process first batch
        vessels_batch = _process_geohash_batch(response, min_distance_miles)
        all_vessels.update(vessels_batch)
        processed_batches += 1
        
        print(f"Processed batch {processed_batches}: {len(vessels_batch)} qualifying vessels")
        
        # Process additional scroll batches
        scroll_id = None
        while processed_batches < scroll_batches:
            try:
                if scroll_id:
                    # Continue scrolling
                    response = es.scroll(scroll_id=scroll_id, scroll="2m")
                else:
                    # Create initial scroll
                    response = es.search(
                        index=VESSEL_INDEX,
                        body=current_query,
                        scroll="2m",
                        size=0
                    )
                
                scroll_id = response.get("_scroll_id")
                
                if not response.get("aggregations"):
                    break
                    
                vessels_batch = _process_geohash_batch(response, min_distance_miles)
                all_vessels.update(vessels_batch)
                processed_batches += 1
                
                print(f"Processed batch {processed_batches}: {len(vessels_batch)} qualifying vessels")
                
            except Exception as e:
                print(f"Scroll batch {processed_batches + 1} failed: {e}")
                break
        
        # Clean up scroll context
        if scroll_id:
            try:
                es.clear_scroll(scroll_id=scroll_id)
            except Exception:
                pass
        
    except Exception as e:
        print(f"Elasticsearch query failed: {e}")
        return []
    
    # Convert to VesselData objects and sort by distance
    vessel_list = []
    for mmsi, vessel_data in all_vessels.items():
        vessel = VesselData(
            mmsi=mmsi,
            vessel_name=vessel_data.get("vessel_name", ""),
            imo=vessel_data.get("imo", ""),
            call_sign=vessel_data.get("call_sign", ""),
            vessel_type=vessel_data.get("vessel_type", ""),
            length=vessel_data.get("length"),
            width=vessel_data.get("width"), 
            draft=vessel_data.get("draft"),
            track_points=vessel_data.get("track_points", []),
            total_distance_miles=vessel_data.get("total_distance_miles", 0.0)
        )
        vessel_list.append(vessel)
    
    # Sort by distance and return top 3
    vessel_list.sort(key=lambda x: x.total_distance_miles, reverse=True)
    top_vessels = vessel_list[:3]
    
    print(f"Final results: {len(top_vessels)} vessels with tracks >= {min_distance_miles} miles")
    for i, vessel in enumerate(top_vessels, 1):
        print(f"  {i}. {vessel.vessel_name} ({vessel.mmsi}): {vessel.total_distance_miles:.1f} miles")
    
    return top_vessels


def _process_geohash_batch(response: Dict, min_distance_miles: float) -> Dict[str, Dict]:
    """Process a single batch of geohash aggregation results."""
    vessels_batch = {}
    
    if not response.get("aggregations", {}).get("vessels", {}).get("buckets"):
        return vessels_batch
    
    for vessel_bucket in response["aggregations"]["vessels"]["buckets"]:
        mmsi = vessel_bucket["key"]
        
        # Extract vessel metadata
        vessel_info_hits = vessel_bucket["vessel_info"]["hits"]["hits"]
        if not vessel_info_hits:
            continue
            
        vessel_metadata = vessel_info_hits[0]["_source"]
        
        # Process geohash cells to get representative points
        geohash_buckets = vessel_bucket.get("geohash_grid", {}).get("buckets", [])
        if not geohash_buckets:
            continue
        
        track_points = []
        for geohash_bucket in geohash_buckets:
            # Get representative point from each geohash cell
            rep_hits = geohash_bucket.get("representative_point", {}).get("hits", {}).get("hits", [])
            if rep_hits:
                point_data = rep_hits[0]["_source"]
                track_points.append({
                    "timestamp": point_data["BaseDateTime"],
                    "lat": point_data["LAT"],
                    "lon": point_data["LON"],
                    "sog": 0,  # Not available in this aggregation
                    "cog": 0,
                    "heading": 0
                })
        
        # Sort points by timestamp
        track_points.sort(key=lambda x: x["timestamp"])
        
        # Calculate total distance using external Python calculation
        if len(track_points) > 1:
            total_distance = _calculate_track_distance(track_points)
            
            if total_distance >= min_distance_miles:
                vessels_batch[mmsi] = {
                    "vessel_name": vessel_metadata.get("VesselName", ""),
                    "imo": vessel_metadata.get("IMO", ""),
                    "call_sign": vessel_metadata.get("CallSign", ""),
                    "vessel_type": str(vessel_metadata.get("VesselType", "")),
                    "length": vessel_metadata.get("Length"),
                    "width": vessel_metadata.get("Width"),
                    "draft": vessel_metadata.get("Draft"),
                    "track_points": track_points,
                    "total_distance_miles": total_distance
                }
    
    return vessels_batch


def _calculate_track_distance(track_points: List[Dict]) -> float:
    """Calculate total track distance using Haversine formula."""
    if len(track_points) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(1, len(track_points)):
        prev_point = track_points[i-1]
        curr_point = track_points[i]
        
        distance = calculate_distance_miles(
            prev_point["lat"], prev_point["lon"],
            curr_point["lat"], curr_point["lon"]
        )
        total_distance += distance
    
    return total_distance


#@tool
def search_vessels_by_distance_old(min_distance_miles: float = 50.0, date: str = "2022-01-01") -> List[VesselData]:
    """Search for vessels with long tracks on a specific date using optimized Elasticsearch aggregations."""
    es = Elasticsearch(["http://localhost:9200"], timeout=60, max_retries=3)
    
    # Use aggregations to group by MMSI and find min/max positions efficiently
    query = {
        "query": {
            "range": {
                "BaseDateTime": {
                    "gte": f"{date}T00:00:00",
                    "lte": f"{date}T23:59:59"
                }
            }
        },
        "size": 0,  # We don't need individual hits, only aggregations
        "aggs": {
            "vessels": {
                "terms": {
                    "field": "MMSI.keyword",  # Use keyword field for exact matching
                    "size": 1000  # Reduced for performance with large dataset
                },
                "aggs": {
                    # Get vessel metadata from first document
                    "vessel_info": {
                        "top_hits": {
                            "size": 1,
                            "_source": ["VesselName", "IMO", "CallSign", "VesselType", "Length", "Width", "Draft"]
                        }
                    },
                    # Find bounding box coordinates for distance calculation
                    "lat_stats": {
                        "stats": {
                            "field": "LAT"
                        }
                    },
                    "lon_stats": {
                        "stats": {
                            "field": "LON"
                        }
                    },
                    # Get track points for vessels (limited by ES index.max_inner_result_window setting)
                    "track_points": {
                        "top_hits": {
                            "size": 100,  # Limited by Elasticsearch index.max_inner_result_window setting
                            "sort": [{"BaseDateTime": {"order": "asc"}}],
                            "_source": ["BaseDateTime", "LAT", "LON", "SOG", "COG", "Heading"]
                        }
                    },
                    # Count total track points for each vessel
                    "point_count": {
                        "value_count": {
                            "field": "LAT"
                        }
                    }
                }
            }
        }
    }
    
    try:
        response = es.search(index="ais_data", body=query)
    except Exception as e:
        print(f"Elasticsearch query failed: {e}")
        return []
    
    # Process aggregation results
    long_distance_vessels = []
    
    if "aggregations" in response and "vessels" in response["aggregations"]:
        for vessel_bucket in response["aggregations"]["vessels"]["buckets"]:
            mmsi = vessel_bucket["key"]
            
            # Extract vessel metadata
            vessel_info_hits = vessel_bucket["vessel_info"]["hits"]["hits"]
            if not vessel_info_hits:
                continue
                
            vessel_data = vessel_info_hits[0]["_source"]
            
            # Get min/max coordinates for bounding box distance calculation
            lat_stats = vessel_bucket["lat_stats"]
            lon_stats = vessel_bucket["lon_stats"]
            
            if lat_stats["count"] < 2:  # Need at least 2 points for distance calculation
                continue
            
            # Calculate approximate distance using bounding box
            min_lat, max_lat = lat_stats["min"], lat_stats["max"]
            min_lon, max_lon = lon_stats["min"], lon_stats["max"]
            
            # Calculate distances between corner points of bounding box to estimate track length
            diagonal_distance = calculate_distance_miles(min_lat, min_lon, max_lat, max_lon)
            
            # For more accurate distance, we could also calculate:
            # - Horizontal distance: min_lat to max_lat at average longitude
            # - Vertical distance: min_lon to max_lon at average latitude
            lat_distance = calculate_distance_miles(min_lat, (min_lon + max_lon) / 2, max_lat, (min_lon + max_lon) / 2)
            lon_distance = calculate_distance_miles((min_lat + max_lat) / 2, min_lon, (min_lat + max_lat) / 2, max_lon)
            
            # Use the maximum of these as an approximation (will be refined later)
            approximate_distance = max(diagonal_distance, lat_distance, lon_distance)
            
            # Pre-filter using approximate distance to avoid processing unnecessary vessels
            if approximate_distance < min_distance_miles * 0.5:  # Use 50% threshold for pre-filtering
                continue
            
            # Extract track points for detailed distance calculation
            track_points = []
            track_hits = vessel_bucket["track_points"]["hits"]["hits"]
            
            for hit in track_hits:
                point_data = hit["_source"]
                track_points.append({
                    "timestamp": point_data["BaseDateTime"],
                    "lat": point_data["LAT"],
                    "lon": point_data["LON"],
                    "sog": point_data.get("SOG", 0),
                    "cog": point_data.get("COG", 0),
                    "heading": point_data.get("Heading", 0)
                })
            
            # Calculate precise total distance using sequential points
            if len(track_points) > 1:
                total_distance = 0.0
                
                for i in range(1, len(track_points)):
                    prev_point = track_points[i-1]
                    curr_point = track_points[i]
                    
                    distance = calculate_distance_miles(
                        prev_point["lat"], prev_point["lon"],
                        curr_point["lat"], curr_point["lon"]
                    )
                    total_distance += distance
                
                # Apply final distance filter
                if total_distance >= min_distance_miles:
                    vessel = VesselData(
                        mmsi=mmsi,
                        vessel_name=vessel_data.get("VesselName") or "",  # Handle None values
                        imo=vessel_data.get("IMO") or "",
                        call_sign=vessel_data.get("CallSign") or "",
                        vessel_type=str(vessel_data.get("VesselType") or ""),  # Convert to string and handle None
                        length=vessel_data.get("Length"),
                        width=vessel_data.get("Width"),
                        draft=vessel_data.get("Draft"),
                        track_points=track_points,
                        total_distance_miles=total_distance
                    )
                    
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
import json
import math
import os
import subprocess
import asyncio
import shutil
import urllib.parse
import re
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
    def __init__(self, config_path: str = "config/mcp_desktop_config.json", llm=None, num_links: int = 1):
        self.config_path = config_path
        self.llm = llm  # LLM for intelligent navigation
        self.num_links = num_links  # Number of links to process
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
    
    def intelligent_search_and_navigate(self, query: str, research_focus: str = "specifications", vessel_mmsi: str = "") -> List[WebSearchResult]:
        """Multi-step LLM-driven research workflow that processes multiple links."""
        results = []
        
        try:
            print(f"🔍 Multi-step LLM research for: {query}")
            
            # Step 1: Navigate to Google search
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            search_result = self._call_mcp("chrome_navigate", {"url": search_url})
            
            if "error" in search_result:
                print(f"❌ Search navigation failed: {search_result['error']}")
                return [WebSearchResult(url="error", content_snippet=search_result["error"])]
            
            print("✅ Navigated to Google search")
            
            # Step 2: Get search results and parse elements
            search_result_elements = self._extract_search_results()
            
            if not search_result_elements:
                print("❌ No relevant search results found")
                return [WebSearchResult(url="error", content_snippet="No relevant search results")]
            
            # Step 3: LLM First Use - Analyze search results to select top N links
            selected_links = self._llm_select_top_links(search_result_elements, query, research_focus)
            
            if not selected_links:
                print("❌ LLM failed to select links")
                return [WebSearchResult(url="error", content_snippet="Failed to select relevant links")]
            
            # Step 4: Sequential Processing - Navigate to each selected link
            for i, link_info in enumerate(selected_links[:self.num_links]):
                print(f"🌐 Processing link {i+1}/{min(len(selected_links), self.num_links)}: {link_info.get('text', '')[:50]}...")
                
                result = self._process_single_link(link_info, i+1, query, vessel_mmsi)
                if vessel_mmsi:
                    result.mmsi = vessel_mmsi  # Associate result with vessel MMSI
                results.append(result)
            
            print(f"✅ Completed processing {len(results)} links")
            return results
                        
        except Exception as e:
            print(f"❌ Multi-step research failed: {str(e)}")
            return [WebSearchResult(
                url="error", 
                content_snippet=f"Research failed: {str(e)}"
            )]
    
    def _extract_search_results(self) -> List[Dict]:
        """Extract and parse search result elements from Google search page."""
        links_result = self._call_mcp("chrome_get_interactive_elements")
        
        if "error" in links_result or "result" not in links_result or not links_result["result"]:
            print(f"❌ Failed to get elements")
            return []
        
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
        return search_result_elements
    
    def _llm_select_top_links(self, search_results: List[Dict], query: str, research_focus: str) -> List[Dict]:
        """LLM First Use: Analyze search results to identify top N links that mention the specific vessel."""
        if not self.llm:
            print("⚠️ No LLM available, selecting first results")
            return search_results[:self.num_links]
        
        results_text = ""
        for i, result in enumerate(search_results[:10]):  # Analyze up to 10 results
            results_text += f"{i}: {result['text']}\n\n"
        
        selection_prompt = f"""
        You are analyzing Google search results to find the BEST {self.num_links} links for vessel research.
        
        Search Query: {query}
        Research Focus: {research_focus}
        
        Available search results:
        {results_text}
        
        Select the TOP {self.num_links} results that are most likely to contain comprehensive vessel information. 
        Prioritize in this order:
        1. Marine Traffic (marinetraffic.com) - vessel tracking/specs
        2. Official shipping companies or vessel operators
        3. VesselFinder or similar vessel databases
        4. Maritime industry sites and shipbuilding companies
        5. Wikipedia or maritime encyclopedias
        
        Avoid generic news articles, ads, or irrelevant pages.
        
        Respond with ONLY a JSON array of the selected result indices (e.g., [0, 3, 7]).
        Maximum {self.num_links} indices.
        """
        
        try:
            response = self.llm.invoke([
                ("system", "You are a maritime research expert. Select the most authoritative vessel information sources."),
                ("user", selection_prompt)
            ])
            
            # Parse JSON response
            content = response.content.strip()
            import re
            json_match = re.search(r'\[[\d,\s]+\]', content)
            if json_match:
                indices = json.loads(json_match.group())
                selected_links = []
                for idx in indices:
                    if 0 <= idx < len(search_results):
                        selected_links.append(search_results[idx])
                
                print(f"🎯 LLM selected {len(selected_links)} links: {indices}")
                return selected_links
            
        except Exception as e:
            print(f"⚠️ LLM selection failed: {e}")
        
        # Fallback to first N results
        print(f"⚠️ Using fallback selection of first {self.num_links} results")
        return search_results[:self.num_links]
    
    def _process_single_link(self, link_info: Dict, link_number: int, query: str, vessel_mmsi: str = "") -> WebSearchResult:
        """Process a single link: navigate, extract content, save file, take screenshot, and use LLM to extract metadata."""
        try:
            # Click on the link
            click_result = self._call_mcp("chrome_click_element", {
                "selector": link_info["selector"]
            })
            
            if "error" in click_result:
                print(f"❌ Failed to click link {link_number}: {click_result['error']}")
                return WebSearchResult(
                    url="error",
                    content_snippet=f"Link {link_number}: Click failed - {click_result['error']}"
                )
            
            import time
            time.sleep(3)  # Wait for page load
            
            # Handle cookie dialogs
            self._handle_cookie_dialogs()
            
            # Get current URL
            current_url = self._get_current_url()
            
            # Take screenshot after page is fully loaded
            screenshot_path = self._capture_screenshot(link_number, vessel_mmsi, current_url)
            
            # Extract page content
            raw_content = self._extract_page_content()
            
            if not raw_content or len(raw_content) < 100:
                print(f"⚠️ Insufficient content from link {link_number}")
                return WebSearchResult(
                    url=current_url,
                    content_snippet=f"Link {link_number}: Insufficient content",
                    metadata_extracted={"screenshot_path": screenshot_path}
                )
            
            # Save content to file with URL-based filename
            content_file = self._save_content_to_file(raw_content, current_url, vessel_mmsi)
            
            # LLM Second Use: Extract comprehensive vessel metadata and distinctive details
            extraction_result = self._extract_vessel_metadata_with_llm(raw_content, query, current_url)
            
            # Extract metadata and details from combined result
            if isinstance(extraction_result, dict):
                vessel_metadata = extraction_result.get("metadata", "")
                vessel_details = extraction_result.get("details", [])
                
                # Handle case where metadata is a dict (JSON structure)
                if isinstance(vessel_metadata, dict):
                    vessel_metadata = json.dumps(vessel_metadata, indent=2)
            else:
                # Fallback for backward compatibility
                vessel_metadata = str(extraction_result)
                vessel_details = []
            
            print(f"✅ Processed link {link_number}: {current_url[:50]}...")
            return WebSearchResult(
                url=current_url,
                title=link_info.get("text", "")[:100],
                content_snippet=vessel_metadata,
                images_found=[],  # Could be enhanced to extract images
                metadata_extracted={
                    "content_file": content_file,
                    "screenshot_path": screenshot_path,
                    "textContent": raw_content[:2000],  # Store first 2000 chars for descriptions
                    "details": vessel_details
                }
            )
            
        except Exception as e:
            print(f"❌ Error processing link {link_number}: {str(e)}")
            return WebSearchResult(
                url="error",
                content_snippet=f"Link {link_number}: Processing failed - {str(e)}"
            )
    
    def _get_current_url(self) -> str:
        """Get the current URL of the active tab."""
        url_result = self._call_mcp("get_windows_and_tabs")
        current_url = "unknown"
        if "result" in url_result and url_result["result"]:
            tabs_data = url_result["result"]
            if isinstance(tabs_data, dict) and "tabs" in tabs_data:
                tabs = tabs_data["tabs"]
                if tabs and len(tabs) > 0:
                    current_url = tabs[0].get("url", "unknown")
        return current_url
    
    def _extract_page_content(self) -> str:
        """Extract cleaned text content from the current page."""
        content_result = self._call_mcp("chrome_get_web_content")
        raw_content = ""
        if "result" in content_result and content_result["result"]:
            content_obj = content_result["result"]
            if isinstance(content_obj, dict) and "content" in content_obj:
                content_list = content_obj["content"]
                if isinstance(content_list, list):
                    content_parts = []
                    for item in content_list:  # Get more content for analysis
                        if isinstance(item, dict) and "text" in item:
                            content_parts.append(item["text"])
                    raw_content = " ".join(content_parts)
        return raw_content
    
    def _save_content_to_file(self, content: str, url: str, vessel_mmsi: str = "") -> str:
        """Save content to local file in vessel-specific directory with URL-based filename."""
        try:
            # Create vessel-specific folder structure
            if vessel_mmsi:
                search_dir = os.path.join("reports", "search_results", vessel_mmsi)
            else:
                search_dir = os.path.join("reports", "search_results")
                
            os.makedirs(search_dir, exist_ok=True)
            
            # Generate URL-based filename
            safe_filename = self._sanitize_url_for_filename(url)
            filename = os.path.join(search_dir, f"{safe_filename}.html")
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"💾 Saved content to {filename}")
            return filename
            
        except Exception as e:
            print(f"⚠️ Failed to save content file: {e}")
            return ""
    
    def _extract_vessel_metadata_with_llm(self, content: str, query: str, url: str) -> Dict[str, Any]:
        """LLM Second Use: Extract comprehensive vessel metadata and distinctive details as structured information."""
        if not self.llm:
            return {
                "metadata": content[:1500],
                "details": []
            }
        
        metadata_prompt = f"""
        Extract comprehensive vessel metadata from this web page content in strict JSON format.
        
        Search Query: {query}
        Source URL: {url}
        Content: {content[:8000]}  # Limit content size for LLM
        
        Extract and structure the following vessel information with BOTH metadata AND details:
        {{
            "metadata": {{
                "vessel_name": "string",
                "imo_number": "string", 
                "mmsi": "string",
                "call_sign": "string",
                "vessel_type": "string",
                "flag": "string",
                "dimensions": {{
                    "length_overall": "string",
                    "beam": "string",
                    "draft": "string"
                }},
                "tonnage": {{
                    "gross_tonnage": "string",
                    "deadweight": "string"
                }},
                "propulsion": {{
                    "engine_type": "string",
                    "power": "string",
                    "speed": "string"
                }},
                "construction": {{
                    "built_year": "string",
                    "shipyard": "string",
                    "classification": "string"
                }},
                "operational": {{
                    "owner": "string",
                    "operator": "string",
                    "current_status": "string"
                }},
                "additional_info": "string"
            }},
            "details": [
                "Array of 3-5 distinctive vessel characteristics as concise strings (each under 80 characters)",
                "Focus on: specifications, registration, status, features, ownership",
                "Example: Container ship, 339.6m LOA, built 2018",
                "Example: Flag: Marshall Islands, IMO 9876543"
            ]
        }}
        
        For the details array, extract 3-5 most distinctive characteristics such as:
        - Vessel specifications (name, type, dimensions)  
        - Flag state and registration details
        - Current operational status or destination
        - Notable features or capabilities
        - Owner/operator information
        - Construction details if significant
        
        If information is not available for metadata, use null for that field.
        If insufficient information for details, use empty array [].
        Respond with ONLY valid JSON, no additional text.
        /no_think
        """
        
        try:
            response = self.llm.invoke([
                ("system", "You are a maritime data extraction expert. Extract vessel information and distinctive details as strict JSON."),
                ("user", metadata_prompt)
            ])
            
            content_response = re.sub(r'<[^>]+>', '', response.content.strip())

            # Try to parse JSON and validate
            try:
                vessel_data = json.loads(content_response)
                
                # Validate structure
                if isinstance(vessel_data, dict) and "metadata" in vessel_data and "details" in vessel_data:
                    # Ensure details is a list of strings, limit to 5 items and 80 chars each
                    details = vessel_data.get("details", [])
                    if isinstance(details, list):
                        clean_details = [str(detail)[:80] for detail in details[:5] if isinstance(detail, str)]
                        vessel_data["details"] = clean_details
                    else:
                        vessel_data["details"] = []
                    
                    return vessel_data
                else:
                    print("⚠️ LLM response missing metadata or details structure")
                    return self._fallback_extract_combined_info(content, query)
                
            except json.JSONDecodeError:
                print("⚠️ LLM response was not valid JSON, using fallback extraction")
                return self._fallback_extract_combined_info(content, query)
            
        except Exception as e:
            print(f"⚠️ LLM metadata extraction failed: {e}")
            return self._fallback_extract_combined_info(content, query)
    
    
    def _fallback_extract_details(self, content: str) -> List[str]:
        """Fallback extraction of vessel details without LLM."""
        # Simple keyword-based extraction for fallback
        lines = content.split('\n')
        details = []
        
        # Look for lines with key vessel information patterns
        patterns = [
            (r'(?i).*vessel\s+name[:\s]+(.*)', 'Vessel: {}'),
            (r'(?i).*imo[:\s]+(\d+)', 'IMO: {}'),
            (r'(?i).*mmsi[:\s]+(\d+)', 'MMSI: {}'),
            (r'(?i).*length[:\s]+(\d+\.?\d*\s*m)', 'Length: {}'),
            (r'(?i).*flag[:\s]+([^\n\r]{1,30})', 'Flag: {}'),
            (r'(?i).*type[:\s]+([^\n\r]{1,40})', 'Type: {}')
        ]
        
        for line in lines[:100]:  # Check first 100 lines
            line = line.strip()
            if 10 < len(line) < 150:  # Reasonable length
                for pattern, format_str in patterns:
                    match = re.search(pattern, line)
                    if match and len(details) < 4:
                        detail = format_str.format(match.group(1).strip())
                        if detail not in details:  # Avoid duplicates
                            details.append(detail[:80])  # Limit length
                        break
        
        return details if details else []
    
    def _fallback_extract_combined_info(self, content: str, query: str) -> Dict[str, Any]:
        """Fallback extraction of key vessel information and details without LLM."""
        # Extract metadata as string
        metadata_str = self._fallback_extract_key_info(content, query)
        
        # Extract details as array
        details_array = self._fallback_extract_details(content)
        
        return {
            "metadata": metadata_str,
            "details": details_array
        }
    
    def _fallback_extract_key_info(self, content: str, query: str) -> str:
        """Fallback extraction of key vessel information without LLM."""
        # Simple keyword-based extraction
        lines = content.split('\n')
        key_info = []
        
        keywords = ['vessel', 'ship', 'imo', 'mmsi', 'length', 'beam', 'draft', 'tonnage', 
                   'built', 'owner', 'operator', 'flag', 'type']
        
        for line in lines[:50]:  # Check first 50 lines
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in keywords):
                if len(line.strip()) > 10 and len(line.strip()) < 200:
                    key_info.append(line.strip())
        
        if key_info:
            return "Key Information:\n" + "\n".join(key_info[:10])
        else:
            return content[:1000]  # Fallback to truncated content
    
    
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
    
    def _capture_screenshot(self, link_number: int, vessel_mmsi: str, url: str) -> str:
        """Capture screenshot of current page and save to MMSI-specific folder."""
        try:
            print(f"📸 Capturing screenshot for link {link_number}...")
            
            # Take screenshot using MCP Chrome bridge
            screenshot_result = self._call_mcp("chrome_screenshot", {
                "format": "jpeg",
                "quality": 85
            })
            
            if "error" in screenshot_result:
                print(f"⚠️ Screenshot capture failed: {screenshot_result['error']}")
                return ""
            
            # Parse the screenshot result
            if "result" in screenshot_result and "content" in screenshot_result["result"]:
                content = screenshot_result["result"]["content"]
                if content and len(content) > 0 and "text" in content[0]:
                    try:
                        screenshot_data = json.loads(content[0]["text"])
                        
                        if screenshot_data.get("success") and "fullPath" in screenshot_data:
                            downloads_path = screenshot_data["fullPath"]
                            
                            # Check if file exists
                            if os.path.exists(downloads_path):
                                # Create destination directory
                                if vessel_mmsi:
                                    dest_dir = os.path.join("reports", "search_results", vessel_mmsi)
                                else:
                                    dest_dir = os.path.join("reports", "search_results")
                                os.makedirs(dest_dir, exist_ok=True)
                                
                                # Generate destination filename
                                dest_filename = f"screenshot_{link_number}.jpg"
                                dest_path = os.path.join(dest_dir, dest_filename)
                                
                                # Move file from downloads to destination
                                shutil.move(downloads_path, dest_path)
                                
                                print(f"✅ Screenshot saved to {dest_path}")
                                return dest_path
                            else:
                                print(f"⚠️ Screenshot file not found at {downloads_path}")
                        else:
                            print(f"⚠️ Screenshot capture unsuccessful: {screenshot_data.get('message', 'Unknown error')}")
                    
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Failed to parse screenshot response: {e}")
            
            return ""
            
        except Exception as e:
            print(f"⚠️ Screenshot capture failed with exception: {e}")
            return ""
    
    def _sanitize_url_for_filename(self, url: str) -> str:
        """Convert URL to safe filename by removing/replacing invalid characters."""
        # Parse URL to get domain and path
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            path = parsed.path.strip("/")
            
            # Create base filename from domain and path
            if path:
                filename_base = f"{domain}_{path}"
            else:
                filename_base = domain
            
            # Remove or replace invalid characters
            # Keep only alphanumeric, hyphens, underscores, and dots
            safe_filename = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', filename_base)
            
            # Remove multiple consecutive underscores
            safe_filename = re.sub(r'_{2,}', '_', safe_filename)
            
            # Remove leading/trailing underscores
            safe_filename = safe_filename.strip('_')
            
            # Limit length to avoid filesystem issues
            if len(safe_filename) > 100:
                safe_filename = safe_filename[:100]
            
            # Ensure we have a valid filename
            if not safe_filename:
                safe_filename = f"page_{hash(url) % 10000}"
            
            return safe_filename
            
        except Exception as e:
            print(f"⚠️ URL sanitization failed: {e}")
            return f"page_{hash(url) % 10000}"


# Initialize MCP client with default parameters
mcp_client = MCPChromeClient(num_links=3)

@tool
def search_vessels_by_distance(min_distance_miles: float = 50.0, date: str = "2022-01-01", scroll_batches: int = 5) -> List[VesselData]:
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
def web_research_vessel(vessel_name: str, mmsi: str, imo: str = "", research_focus: str = "specifications", num_links: int = 3) -> List[WebSearchResult]:
    """Research vessel information using multi-step LLM-guided web search.
    
    Args:
        vessel_name: Name of the vessel to research
        mmsi: MMSI identifier for the vessel
        imo: IMO identifier for the vessel (optional)
        research_focus: Focus area for research (specifications, operational_context, etc.)
        num_links: Number of web sources to process (default 3)
    
    Returns:
        List of WebSearchResult objects with mmsi field populated
    
    Examples:
        # Research a specific vessel
        results = web_research_vessel("OCEAN INTERVENTION", "366614000", "IMO9876543")
        
        # Results will include vessel-specific research data with MMSI association
        for result in results:
            print(f"Found data for MMSI {result.mmsi}: {result.url}")
    """
    search_terms = [vessel_name]
    if mmsi:
        search_terms.append(f"MMSI {mmsi}")
    if imo and imo != "IMO0000000":
        search_terms.append(f"IMO {imo}")
    
    query = " ".join(search_terms) + " ship vessel specifications"
    
    # Use the global mcp_client but ensure it has the right configuration
    # The LLM should already be set by the vessel agent
    if hasattr(mcp_client, 'num_links'):
        mcp_client.num_links = num_links
    
    # Call intelligent search with vessel MMSI for proper file organization
    results = mcp_client.intelligent_search_and_navigate(query, research_focus, mmsi)
    
    # Ensure all results have the MMSI field populated (fallback if not set in MCPChromeClient)
    for result in results:
        if not result.mmsi and mmsi:
            result.mmsi = mmsi
    
    return results

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
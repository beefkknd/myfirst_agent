"""
Chrome MCP client for intelligent web research.

Configurable MCP client that reads server configuration from config files
and provides LLM-guided web research capabilities.
"""

import json
import asyncio
import shutil
import time
import re
import urllib.parse
import os
from typing import List, Dict, Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..models.research import WebSearchResult
from ..utils.file_ops import sanitize_url_for_filename, ensure_directory, safe_move_file


class ChromeMCPClient:
    """
    Chrome MCP client for intelligent web research and content extraction.
    
    Reads MCP server configuration from JSON config files and provides
    LLM-guided multi-step web research workflows.
    """
    
    def __init__(
        self, 
        config_path: str = "config/mcp_desktop_config.json",
        llm=None,
        num_links: int = 1
    ):
        """
        Initialize Chrome MCP client with configuration file.
        
        Args:
            config_path: Path to MCP desktop configuration JSON file
            llm: LLM instance for intelligent navigation decisions
            num_links: Number of links to process per search
        """
        self.config_path = config_path
        self.llm = llm
        self.num_links = num_links
        self.server_params = self._load_mcp_configuration()
        self._tools_listed = False
        
        print(f"🌐 ChromeMCPClient initialized with {num_links} links from {config_path}")
    
    def _load_mcp_configuration(self) -> StdioServerParameters:
        """
        Load MCP server configuration from JSON config file.
        
        Returns:
            StdioServerParameters for the Chrome MCP server
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            chrome_config = config['mcpServers']['chrome-mcp-stdio']
            
            return StdioServerParameters(
                command=chrome_config['command'],
                args=chrome_config['args'],
                env=chrome_config.get('env', {})
            )
            
        except Exception as e:
            print(f"⚠️ Failed to load MCP config from {self.config_path}: {e}")
            print("🔄 Using default configuration")
            
            # Fallback to default configuration
            return StdioServerParameters(
                command="node",
                args=["/opt/homebrew/lib/node_modules/mcp-chrome-bridge/dist/mcp/mcp-server-stdio.js"],
                env={}
            )
    
    async def _call_mcp_async(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make asynchronous call to MCP Chrome bridge.
        
        Args:
            method: MCP method name
            params: Method parameters
            
        Returns:
            Parsed MCP response
        """
        if params is None:
            params = {}
        
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # List available tools on first call
                    if not self._tools_listed:
                        tools = await session.list_tools()
                        print(f"🔧 Available MCP tools: {[tool.name for tool in tools.tools]}")
                        self._tools_listed = True
                    
                    # Call the tool
                    result = await session.call_tool(method, params)
                    
                    # Parse TextContent response
                    parsed_result = self._parse_mcp_response(result)
                    return {"result": parsed_result}
                    
        except Exception as e:
            return {"error": f"MCP call failed: {str(e)}"}
    
    def _parse_mcp_response(self, result) -> Any:
        """Parse MCP response from TextContent objects"""
        parsed_result = None
        
        if hasattr(result, 'content') and isinstance(result.content, list):
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    try:
                        text_content = content_item.text
                        parsed_data = json.loads(text_content)
                        
                        # Extract data from nested response structure
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
                        parsed_result = content_item.text
                        break
        
        return parsed_result or result.content
    
    def _call_mcp(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronous wrapper for async MCP calls"""
        return asyncio.run(self._call_mcp_async(method, params))
    
    def intelligent_search_and_navigate(
        self, 
        query: str, 
        research_focus: str = "specifications", 
        vessel_mmsi: str = ""
    ) -> List[WebSearchResult]:
        """
        Multi-step LLM-driven research workflow.
        
        Args:
            query: Search query string
            research_focus: Research focus area (specifications, operational_context, etc.)
            vessel_mmsi: MMSI of vessel for result association and file organization
            
        Returns:
            List of WebSearchResult objects with extracted content
        """
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
            
            # Step 2: Extract search result elements
            search_elements = self._extract_search_results()
            
            if not search_elements:
                print("❌ No relevant search results found")
                return [WebSearchResult(url="error", content_snippet="No relevant search results")]
            
            # Step 3: LLM-guided link selection
            selected_links = self._llm_select_top_links(search_elements, query, research_focus)
            
            if not selected_links:
                print("❌ LLM failed to select links")
                return [WebSearchResult(url="error", content_snippet="Failed to select relevant links")]
            
            # Step 4: Process each selected link
            for i, link_info in enumerate(selected_links[:self.num_links]):
                print(f"🌐 Processing link {i+1}/{min(len(selected_links), self.num_links)}: {link_info.get('text', '')[:50]}...")
                
                result = self._process_single_link(link_info, i+1, query, vessel_mmsi)
                if vessel_mmsi:
                    result.mmsi = vessel_mmsi
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
        """Extract clickable search result elements from Google search page"""
        links_result = self._call_mcp("chrome_get_interactive_elements")
        
        if "error" in links_result or "result" not in links_result or not links_result["result"]:
            print("❌ Failed to get elements")
            return []
        
        # Parse elements with nested JSON handling
        elements_data = links_result["result"]
        elements = self._parse_elements_data(elements_data)
        
        # Filter for search result links
        search_result_elements = []
        skip_terms = ["sign in", "images", "videos", "news", "shopping", "more", "tools", "settings"]
        
        for element in elements:
            if self._is_search_result_link(element, skip_terms):
                search_result_elements.append({
                    "selector": element.get("selector", ""),
                    "text": element.get("text", "")[:300],
                    "type": element.get("type", "")
                })
        
        print(f"🔍 Found {len(search_result_elements)} clickable search results")
        return search_result_elements
    
    def _parse_elements_data(self, elements_data) -> List[Dict]:
        """Parse elements data handling various nested structures"""
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
                    else:
                        elements = content
        elif isinstance(elements_data, list):
            elements = elements_data
            # Check for nested JSON in first element
            if len(elements) > 0 and isinstance(elements[0], dict) and "text" in elements[0]:
                try:
                    nested_json = json.loads(elements[0]["text"])
                    elements = nested_json.get("elements", elements)
                except json.JSONDecodeError:
                    pass
        
        return elements
    
    def _is_search_result_link(self, element: Dict, skip_terms: List[str]) -> bool:
        """Check if element is a valid search result link"""
        if not isinstance(element, dict):
            return False
            
        text = element.get("text", "")
        elem_type = element.get("type", "")
        
        return (
            elem_type == "link" and
            element.get("isInteractive", False) and
            not element.get("disabled", True) and
            text and
            len(text) > 20 and
            ("http" in text.lower() or "www." in text.lower()) and
            not any(skip in text.lower() for skip in skip_terms)
        )
    
    def _llm_select_top_links(self, search_results: List[Dict], query: str, research_focus: str) -> List[Dict]:
        """Use LLM to analyze and select the best search result links"""
        if not self.llm:
            print("⚠️ No LLM available, selecting first results")
            return search_results[:self.num_links]
        
        results_text = ""
        for i, result in enumerate(search_results[:10]):
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
            
            content = response.content.strip()
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
        
        print(f"⚠️ Using fallback selection of first {self.num_links} results")
        return search_results[:self.num_links]
    
    def _process_single_link(
        self, 
        link_info: Dict, 
        link_number: int, 
        query: str, 
        vessel_mmsi: str = ""
    ) -> WebSearchResult:
        """Process a single link: navigate, extract content, save files, and use LLM for metadata extraction"""
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
            
            time.sleep(3)  # Wait for page load
            
            # Handle cookie dialogs
            self._handle_cookie_dialogs()
            
            # Get current URL
            current_url = self._get_current_url()
            
            # Take screenshot
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
            
            # Save content to file
            content_file = self._save_content_to_file(raw_content, current_url, vessel_mmsi)
            
            # LLM metadata extraction
            extraction_result = self._extract_vessel_metadata_with_llm(raw_content, query, current_url)
            
            # Process extraction result
            if isinstance(extraction_result, dict):
                vessel_metadata = extraction_result.get("metadata", "")
                vessel_details = extraction_result.get("details", [])
                
                if isinstance(vessel_metadata, dict):
                    vessel_metadata = json.dumps(vessel_metadata, indent=2)
            else:
                vessel_metadata = str(extraction_result)
                vessel_details = []
            
            print(f"✅ Processed link {link_number}: {current_url[:50]}...")
            return WebSearchResult(
                url=current_url,
                title=link_info.get("text", "")[:100],
                content_snippet=vessel_metadata,
                images_found=[],  # Could be enhanced
                metadata_extracted={
                    "content_file": content_file,
                    "screenshot_path": screenshot_path,
                    "textContent": raw_content[:2000],
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
        """Get the current URL of the active browser tab"""
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
        """Extract cleaned text content from the current page"""
        content_result = self._call_mcp("chrome_get_web_content")
        raw_content = ""
        
        if "result" in content_result and content_result["result"]:
            content_obj = content_result["result"]
            if isinstance(content_obj, dict) and "content" in content_obj:
                content_list = content_obj["content"]
                if isinstance(content_list, list):
                    content_parts = []
                    for item in content_list:
                        if isinstance(item, dict) and "text" in item:
                            content_parts.append(item["text"])
                    raw_content = " ".join(content_parts)
                    
        return raw_content
    
    def _save_content_to_file(self, content: str, url: str, vessel_mmsi: str = "") -> str:
        """Save content to local file in vessel-specific directory"""
        try:
            # Create vessel-specific folder
            if vessel_mmsi:
                search_dir = ensure_directory(f"reports/search_results/{vessel_mmsi}")
            else:
                search_dir = ensure_directory("reports/search_results")
            
            # Generate filename
            safe_filename = sanitize_url_for_filename(url)
            filename = f"{search_dir}/{safe_filename}.html"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"💾 Saved content to {filename}")
            return filename
            
        except Exception as e:
            print(f"⚠️ Failed to save content file: {e}")
            return ""
    
    def _extract_vessel_metadata_with_llm(self, content: str, query: str, url: str) -> Dict[str, Any]:
        """Use LLM to extract structured vessel metadata from page content"""
        if not self.llm:
            return {
                "metadata": content[:1500],
                "details": []
            }
        
        metadata_prompt = f"""
        Extract comprehensive vessel metadata from this web page content in strict JSON format.
        
        Search Query: {query}
        Source URL: {url}
        Content: {content[:8000]}
        
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
        """
        
        try:
            response = self.llm.invoke([
                ("system", "You are a maritime data extraction expert. Extract vessel information as strict JSON."),
                ("user", metadata_prompt)
            ])
            
            content_response = re.sub(r'<[^>]+>', '', response.content.strip())
            
            try:
                vessel_data = json.loads(content_response)
                
                if isinstance(vessel_data, dict) and "metadata" in vessel_data and "details" in vessel_data:
                    # Clean details array
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
    
    def _fallback_extract_combined_info(self, content: str, query: str) -> Dict[str, Any]:
        """Fallback extraction without LLM"""
        metadata_str = content[:1000] if content else "No content available"
        details_array = self._simple_extract_details(content)
        
        return {
            "metadata": metadata_str,
            "details": details_array
        }
    
    def _simple_extract_details(self, content: str) -> List[str]:
        """Simple pattern-based detail extraction"""
        if not content:
            return []
            
        lines = content.split('\n')
        details = []
        
        patterns = [
            (r'(?i).*vessel\s+name[:\s]+(.*)', 'Vessel: {}'),
            (r'(?i).*imo[:\s]+(\d+)', 'IMO: {}'),
            (r'(?i).*mmsi[:\s]+(\d+)', 'MMSI: {}'),
            (r'(?i).*length[:\s]+(\d+\.?\d*\s*m)', 'Length: {}'),
            (r'(?i).*flag[:\s]+([^\n\r]{1,30})', 'Flag: {}'),
            (r'(?i).*type[:\s]+([^\n\r]{1,40})', 'Type: {}')
        ]
        
        for line in lines[:100]:
            line = line.strip()
            if 10 < len(line) < 150:
                for pattern, format_str in patterns:
                    match = re.search(pattern, line)
                    if match and len(details) < 4:
                        detail = format_str.format(match.group(1).strip())
                        if detail not in details:
                            details.append(detail[:80])
                        break
        
        return details
    
    def _handle_cookie_dialogs(self):
        """Detect and handle cookie acceptance dialogs"""
        try:
            elements_result = self._call_mcp("chrome_get_interactive_elements")
            
            if "result" in elements_result and elements_result["result"]:
                elements_data = elements_result["result"]
                elements = self._parse_elements_data(elements_data)
                
                cookie_terms = ["accept", "allow", "agree", "consent", "continue", "ok", "got it"]
                
                for element in elements:
                    if isinstance(element, dict):
                        text = element.get("text", "").lower()
                        elem_type = element.get("type", "")
                        selector = element.get("selector", "")
                        
                        if (elem_type == "button" and
                            element.get("isInteractive", False) and
                            any(term in text for term in cookie_terms) and
                            len(text) < 50):
                            
                            print(f"🍪 Found cookie dialog button: {text}")
                            self._call_mcp("chrome_click_element", {"selector": selector})
                            time.sleep(2)
                            break
                            
        except Exception as e:
            print(f"⚠️ Cookie dialog handling failed: {e}")
    
    def _capture_screenshot(self, link_number: int, vessel_mmsi: str, url: str) -> str:
        """Capture and save screenshot of current page"""
        try:
            print(f"📸 Capturing screenshot for link {link_number}...")
            
            screenshot_result = self._call_mcp("chrome_screenshot", {
                "format": "jpeg",
                "quality": 85
            })
            
            if "error" in screenshot_result:
                print(f"⚠️ Screenshot capture failed: {screenshot_result['error']}")
                return ""
            
            # Parse screenshot result
            if "result" in screenshot_result and "content" in screenshot_result["result"]:
                content = screenshot_result["result"]["content"]
                if content and len(content) > 0 and "text" in content[0]:
                    try:
                        screenshot_data = json.loads(content[0]["text"])
                        
                        if screenshot_data.get("success") and "fullPath" in screenshot_data:
                            downloads_path = screenshot_data["fullPath"]
                            
                            if os.path.exists(downloads_path):
                                # Create destination directory
                                if vessel_mmsi:
                                    dest_dir = ensure_directory(f"reports/search_results/{vessel_mmsi}")
                                else:
                                    dest_dir = ensure_directory("reports/search_results")
                                
                                dest_filename = f"screenshot_{link_number}.jpg"
                                dest_path = f"{dest_dir}/{dest_filename}"
                                
                                if safe_move_file(downloads_path, dest_path):
                                    print(f"✅ Screenshot saved to {dest_path}")
                                    return dest_path
                        else:
                            print(f"⚠️ Screenshot capture unsuccessful: {screenshot_data.get('message', 'Unknown error')}")
                    
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Failed to parse screenshot response: {e}")
            
            return ""
            
        except Exception as e:
            print(f"⚠️ Screenshot capture failed with exception: {e}")
            return ""


# Global client instance (will be configured by services)
chrome_mcp_client = ChromeMCPClient()
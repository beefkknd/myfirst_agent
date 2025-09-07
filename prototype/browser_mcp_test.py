# MCP Chrome Bridge Wrapper
import asyncio
import json
import time
from typing import Dict, Any, List
from aiohttp import ClientSession
from mcp import stdio_client, StdioServerParameters
from langchain_ollama import ChatOllama


class SmartMCPChromeClient:
    def __init__(self, config_path: str = "config/mcp_desktop_config.json", llm=None):
        self.config_path = config_path
        self.llm = llm or ChatOllama(model="qwen3:8b", temperature=0.1)
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
                async with ClientSession() as session:
                    await session.initialize()

                    if not hasattr(self, '_tools_listed'):
                        tools = await session.list_tools()
                        print(f"Available MCP tools: {[tool.name for tool in tools.tools]}")
                        self._tools_listed = True

                    result = await session.call_tool(method, params)
                    parsed_result = None

                    if hasattr(result, 'content') and isinstance(result.content, list):
                        for content_item in result.content:
                            if hasattr(content_item, 'text'):
                                try:
                                    text_content = content_item.text
                                    parsed_data = json.loads(text_content)
                                    parsed_result = parsed_data
                                    break
                                except json.JSONDecodeError:
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

    def intelligent_search_and_navigate(self, query: str, research_focus: str = "specifications") -> Dict[str, Any]:
        """LLM-driven search that processes three relevant results with cookie handling."""
        results = {"result1": None, "result2": None, "result3": None}
        print(f"🔍 LLM-guided search for: {query}")

        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        search_result = self._call_mcp("chrome_navigate", {"url": search_url})
        time.sleep(3)

        content_result = self._call_mcp("chrome_get_web_content")
        raw_content = " ".join(
            item["text"] for item in content_result["result"] if isinstance(item, dict) and "text" in item)[:10000]

        with open("search_page_content.txt", "w", encoding="utf-8") as f:
            f.write(raw_content)
        print("💾 Saved search page content to search_page_content.txt")

        selected_indices = self._llm_select_best_results(raw_content, research_focus)

        for i, idx in enumerate(selected_indices[:3], 1):
            selector = f"link_{idx}"
            click_result = self._call_mcp("chrome_click_element", {"selector": selector})
            time.sleep(3)
            self._handle_cookie_dialogs()
            results[f"result{i}"] = self._navigate_and_extract_content(query, i)

        return results

    def _navigate_and_extract_content(self, query: str, result_number: int) -> Dict:
        """Extract full page content, save to file, and extract metadata."""
        url_result = self._call_mcp("get_windows_and_tabs")
        current_url = url_result["result"]["tabs"][0]["url"] if url_result["result"].get("tabs") else "unknown"

        content_result = self._call_mcp("chrome_get_web_content")
        raw_content = " ".join(
            item["text"] for item in content_result["result"] if isinstance(item, dict) and "text" in item)[:10000]

        filename = f"page_content_result{result_number}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(raw_content)
        print(f"💾 Saved page content to {filename}")

        metadata = self._extract_vessel_metadata(raw_content, query)
        return {"url": current_url, "metadata": metadata}

    def _handle_cookie_dialogs(self):
        """Detect and handle cookie dialogs (reject or accept if needed)."""
        try:
            elements_result = self._call_mcp("chrome_get_interactive_elements")
            if elements_result["result"]:
                elements_data = elements_result["result"]
                elements = elements_data["elements"] if isinstance(elements_data,
                                                                   dict) and "elements" in elements_data else elements_data

                cookie_terms = ["reject", "decline", "accept", "allow", "agree", "consent", "continue", "ok", "got it"]

                for element in elements:
                    if isinstance(element, dict):
                        text = element.get("text", "").lower()
                        elem_type = element.get("type", "")
                        selector = element.get("selector", "")

                        if (elem_type == "button" and
                                element.get("isInteractive", False) and
                                any(term in text for term in cookie_terms) and
                                len(text) < 50):
                            action = "reject" if "reject" or "decline" in text else "accept"
                            print(f"🍪 Found cookie dialog button: {text} ({action})")
                            self._call_mcp("chrome_click_element", {"selector": selector})
                            time.sleep(2)
                            break

        except Exception as e:
            print(f"⚠️ Cookie dialog handling failed: {e}")

    def _extract_vessel_metadata(self, content: str, query: str) -> Dict:
        """Use LLM to extract vessel metadata as JSON."""
        metadata_prompt = f"""
        Extract vessel metadata from the following content as JSON. Focus on:
        - Vessel name
        - MMSI number
        - IMO number
        - Type (e.g., Fishing, Cargo)
        - Flag
        - Length, beam, draft
        - Tonnage (gross, net)
        - Propulsion (engine type, power)
        - Construction details (builder, year)
        - Owner/operator
        - Current position/status

        Search Query: {query}
        Content: {content[:8000]}

        Return JSON with only available data. Use null for missing fields.
        """

        response = self.llm.invoke([
            ("system", "You are a maritime data extractor. Return valid JSON with vessel metadata."),
            ("user", metadata_prompt)
        ])

        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response as JSON", "raw_response": response.content}

    def _llm_select_best_results(self, content: str, research_focus: str) -> List[int]:
        """LLM selects the three most relevant search result links."""
        selection_prompt = f"""
        From the following Google search page content, identify the top 3 clickable links relevant to vessel research focused on: {research_focus}

        Content: {content[:8000]}

        Prioritize in this order:
        1. Marine Traffic (marinetraffic.com) - vessel tracking/specs
        2. Official shipping companies or vessel operators
        3. VesselFinder or similar vessel databases
        4. Maritime industry sites
        5. Wikipedia (last resort)

        Return a JSON array of three indices [0, 1, 2, ...] corresponding to link selectors (e.g., link_0, link_1).
        """

        response = self.llm.invoke([
            ("system", "You are a research expert. Return a JSON array of three link indices."),
            ("user", selection_prompt)
        ])

        try:
            indices = json.loads(response.content.strip())
            return indices if isinstance(indices, list) and len(indices) >= 3 else [0, 1, 2]
        except json.JSONDecodeError:
            return [0, 1, 2]

# Test script
if __name__ == "__main__":
    client = SmartMCPChromeClient()

    # Default query or input
    query = input(
        "Enter search query (default: DJP II MMSI 368066030 ship vessel specifications): ") or "DJP II MMSI 368066030 ship vessel specifications"
    research_focus = "specifications"  # Can change if needed

    results = client.intelligent_search_and_navigate(query, research_focus)

    print("\nTest Results:")
    for result in results:
        print(json.dumps(result, indent=2))
        print("======================================")
        # print(f"URL: {result.url}")
        # print(f"Title: {result.title}")
        # print(f"Content Snippet: {result.content_snippet[:500]}...")  # Truncated for console
        # print("-" * 80)

    # To debug: Observe console for LLM decisions on link selection and popups.
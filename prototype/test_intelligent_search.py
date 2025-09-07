#!/usr/bin/env python3

from tools import MCPChromeClient
import json
from langchain_ollama import ChatOllama

def test_intelligent_search_basic():
    """Test basic intelligent search without LLM."""
    print("🧪 Testing basic intelligent search...")
    client = MCPChromeClient()
    
    query = "vessel ship OCEAN INTERVENTION specifications"
    results = client.intelligent_search_and_navigate(query, "specifications")
    
    print(f"Results: {len(results)}")
    for result in results:
        print(f"- URL: {result.url}")
        print(f"- Title: {result.title[:50]}...")
        print(f"- Content: {result.content_snippet[:100]}...")
        print()

def test_intelligent_search_with_llm():
    """Test intelligent search with LLM analysis."""
    print("🧪 Testing intelligent search with LLM...")
    
    # Initialize LLM
    try:
        llm = ChatOllama(model="qwen2.5:3b", base_url="http://localhost:11434")
        client = MCPChromeClient(llm=llm)
        
        query = "vessel ship OCEAN INTERVENTION MMSI 366614000"
        results = client.intelligent_search_and_navigate(query, "specifications")
        
        print(f"LLM Results: {len(results)}")
        for result in results:
            print(f"- URL: {result.url}")
            print(f"- Title: {result.title[:50]}...")
            print(f"- Analysis: {result.content_snippet}")
            print()
    except Exception as e:
        print(f"LLM test failed: {e}")

def test_json_parsing():
    """Test JSON parsing with nested structure."""
    print("🧪 Testing JSON parsing logic...")
    
    # Simulate nested JSON structure from MCP Chrome bridge
    mock_response = {
        "result": {
            "content": [
                {
                    "text": json.dumps({
                        "elements": [
                            {
                                "type": "link",
                                "text": "Marine Traffic - OCEAN INTERVENTION vessel details",
                                "selector": "a[href*='marinetraffic']",
                                "isInteractive": True,
                                "disabled": False
                            },
                            {
                                "type": "link", 
                                "text": "Wikipedia - List of ships",
                                "selector": "a[href*='wikipedia']",
                                "isInteractive": True,
                                "disabled": False
                            }
                        ]
                    })
                }
            ]
        }
    }
    
    # Test parsing logic from the implementation
    elements_data = mock_response["result"]
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
                        print("✅ Successfully parsed nested JSON")
                    except json.JSONDecodeError:
                        elements = content
    
    print(f"Parsed {len(elements)} elements:")
    for i, element in enumerate(elements):
        if isinstance(element, dict):
            print(f"  [{i}] {element.get('type', '')}: {element.get('text', '')[:50]}...")

def test_cookie_detection():
    """Test cookie dialog detection logic."""
    print("🧪 Testing cookie dialog detection...")
    
    # Mock elements with cookie dialog
    mock_elements = [
        {
            "type": "button",
            "text": "Accept all cookies",
            "selector": "button[data-testid='cookie-accept']",
            "isInteractive": True,
            "disabled": False
        },
        {
            "type": "button", 
            "text": "Agree and continue",
            "selector": "button.cookie-consent",
            "isInteractive": True,
            "disabled": False
        },
        {
            "type": "link",
            "text": "Regular navigation link",
            "selector": "a.nav-link", 
            "isInteractive": True,
            "disabled": False
        }
    ]
    
    # Test cookie detection logic
    cookie_terms = ["accept", "allow", "agree", "consent", "continue", "ok", "got it"]
    found_cookies = []
    
    for element in mock_elements:
        if isinstance(element, dict):
            text = element.get("text", "").lower()
            elem_type = element.get("type", "")
            
            if (elem_type == "button" and
                element.get("isInteractive", False) and
                any(term in text for term in cookie_terms) and
                len(text) < 50):
                found_cookies.append(element)
    
    print(f"Found {len(found_cookies)} cookie dialog buttons:")
    for cookie in found_cookies:
        print(f"  - {cookie['text']}")

if __name__ == "__main__":
    print("🚀 Running intelligent search tests...\n")
    
    test_json_parsing()
    print()
    
    test_cookie_detection()
    print()
    
    test_intelligent_search_basic()
    print()
    
    test_intelligent_search_with_llm()
    print()
    
    print("✅ Tests completed!")
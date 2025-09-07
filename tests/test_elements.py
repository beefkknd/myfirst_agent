#!/usr/bin/env python3

from tools import MCPChromeClient
import json

def test_elements_parsing():
    """Test the improved element parsing logic."""
    print("🧪 Testing element parsing with nested JSON handling...")
    client = MCPChromeClient()
    
    # Navigate to Google
    print("📱 Navigating to Google search...")
    nav_result = client._call_mcp("chrome_navigate", {"url": "https://www.google.com/search?q=vessel+OCEAN+INTERVENTION"})
    
    if "error" in nav_result:
        print(f"❌ Navigation failed: {nav_result['error']}")
        return
    
    print("✅ Navigation successful")
    
    # Get elements using improved parsing
    print("\n🔍 Getting interactive elements...")
    elements_result = client._call_mcp("chrome_get_interactive_elements")
    
    if "error" in elements_result or "result" not in elements_result:
        print(f"❌ Failed to get elements: {elements_result.get('error', 'Unknown error')}")
        return
    
    # Use the same parsing logic as the improved implementation
    elements_data = elements_result["result"]
    elements = []
    
    print(f"📊 Raw result type: {type(elements_data)}")
    
    # Handle different response structures (same as improved code)
    if isinstance(elements_data, dict):
        print(f"📋 Dictionary keys: {list(elements_data.keys())}")
        if "elements" in elements_data:
            elements = elements_data["elements"]
            print("✅ Found direct 'elements' key")
        elif "content" in elements_data:
            content = elements_data["content"]
            print(f"📄 Found 'content' key with {len(content) if isinstance(content, list) else 'non-list'} items")
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    try:
                        nested_json = json.loads(first_item["text"])
                        elements = nested_json.get("elements", [])
                        print(f"✅ Parsed nested JSON with {len(elements)} elements")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON parse failed: {e}")
                        elements = content
                else:
                    elements = content
    elif isinstance(elements_data, list):
        elements = elements_data
        print(f"📄 Direct list with {len(elements)} items")
        # Check for nested JSON in first element
        if len(elements) > 0 and isinstance(elements[0], dict) and "text" in elements[0]:
            try:
                nested_json = json.loads(elements[0]["text"])
                elements = nested_json.get("elements", elements)
                print("✅ Found and parsed nested JSON in list")
            except json.JSONDecodeError:
                print("ℹ️ No nested JSON found in list")
    
    print(f"\n🎯 Final parsed elements count: {len(elements)}")
    
    # Filter for search result links (same logic as implementation)
    search_result_elements = []
    skip_terms = ["sign in", "images", "videos", "news", "shopping", "more", "tools", "settings"]
    
    for i, element in enumerate(elements[:10]):  # Show first 10
        if isinstance(element, dict):
            text = element.get("text", "")
            elem_type = element.get("type", "")
            selector = element.get("selector", "")
            is_interactive = element.get("isInteractive", False)
            disabled = element.get("disabled", True)
            
            print(f"[{i:2d}] {elem_type:10} | {str(is_interactive):5} | {str(not disabled):5} | {text[:60]}...")
            
            # Apply the same filtering as the implementation
            if (elem_type == "link" and
                    is_interactive and
                    not disabled and
                    text and
                    len(text) > 20 and
                    ("http" in text.lower() or "www." in text.lower()) and
                    not any(skip in text.lower() for skip in skip_terms)):
                search_result_elements.append({
                    "selector": selector,
                    "text": text[:300],
                    "type": elem_type
                })
    
    print(f"\n🔗 Found {len(search_result_elements)} valid search result links:")
    for i, elem in enumerate(search_result_elements):
        print(f"  [{i}]: {elem['text'][:80]}...")
        print(f"       Selector: {elem['selector']}")
    
    return search_result_elements

def test_intelligent_search_integration():
    """Test the full intelligent search with the new implementation."""
    print("\n🚀 Testing full intelligent search integration...")
    client = MCPChromeClient()
    
    query = "OCEAN INTERVENTION vessel ship specifications"
    results = client.intelligent_search_and_navigate(query, "specifications")
    
    print(f"\n📊 Search Results: {len(results)}")
    for i, result in enumerate(results):
        print(f"[{i}] URL: {result.url}")
        print(f"    Title: {result.title[:60]}...")
        print(f"    Content: {result.content_snippet[:100]}...")
        print()

if __name__ == "__main__":
    print("🧪 Running improved element parsing tests...\n")
    
    # Test element parsing
    search_elements = test_elements_parsing()
    
    # Test full integration if elements were found
    if search_elements:
        test_intelligent_search_integration()
    
    print("✅ Tests completed!")
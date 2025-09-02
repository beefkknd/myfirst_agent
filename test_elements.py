#!/usr/bin/env python3

from tools import MCPChromeClient
import json

def test_elements():
    client = MCPChromeClient()
    
    # Navigate to Google
    print("Navigating to Google search...")
    client._call_mcp("chrome_navigate", {"url": "https://www.google.com/search?q=vessel+ship"})
    
    # Get elements and print detailed info
    print("\nGetting elements...")
    elements_result = client._call_mcp("chrome_get_interactive_elements")
    
    if "result" in elements_result:
        result_data = elements_result["result"]
        print(f"Result data type: {type(result_data)}")
        print(f"Result data keys: {result_data.keys() if isinstance(result_data, dict) else 'not dict'}")
        
        # Debug the content
        if isinstance(result_data, dict) and "content" in result_data:
            content = result_data["content"]
            print(f"Content: {content}")
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    text_content = first_item["text"]
                    print(f"Text content: {text_content[:200]}...")
                    try:
                        parsed_json = json.loads(text_content)
                        print(f"Parsed JSON keys: {parsed_json.keys()}")
                        if "elements" in parsed_json:
                            result_data = parsed_json  # Use the parsed data instead
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
        
        if "elements" in result_data:
            elements = result_data["elements"]
            print(f"Found {len(elements)} elements")
            
            # Look for links
            links = []
            for i, element in enumerate(elements):
                if isinstance(element, dict):
                    elem_type = element.get("type", "")
                    text = element.get("text", "")
                    href = element.get("href", "")
                    
                    print(f"[{i}] Type: {elem_type}, Text: '{text[:30]}...', Href: '{href[:50]}...'")
                    
                    if elem_type == "link" and href and "google.com" not in href:
                        links.append({
                            "href": href,
                            "text": text,
                            "type": elem_type
                        })
            
            print(f"\nFound {len(links)} potential search result links:")
            for link in links[:5]:
                print(f"  - {link['text'][:50]}...")
                print(f"    {link['href'][:80]}...")
        else:
            print("No 'elements' key found in result")
            print(f"Available keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'not dict'}")

if __name__ == "__main__":
    test_elements()
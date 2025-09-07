#!/usr/bin/env python3

from tools import MCPChromeClient

def debug_mcp():
    client = MCPChromeClient()
    
    print("🔧 Debug MCP Chrome Integration")
    print("=" * 50)
    
    # Navigate to Google
    print("1. Navigating to Google search...")
    search_result = client._call_mcp("chrome_navigate", {"url": "https://www.google.com/search?q=vessel+ship"})
    print(f"   Result: {search_result}")
    
    # Get interactive elements
    print("\n2. Getting interactive elements...")
    elements_result = client._call_mcp("chrome_get_interactive_elements")
    print(f"   Result type: {type(elements_result)}")
    
    if "result" in elements_result:
        result = elements_result["result"]
        print(f"   Result object type: {type(result)}")
        print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        print(f"   Result sample: {str(result)[:300]}...")
        
        # Try different ways to access the elements
        if isinstance(result, dict):
            if "content" in result:
                content = result["content"]
                print(f"   Content type: {type(content)}")
                if isinstance(content, list) and len(content) > 0:
                    print(f"   Content length: {len(content)}")
                    for i, item in enumerate(content[:3]):
                        print(f"     [{i}] Type: {type(item)}")
                        if isinstance(item, dict):
                            print(f"         Keys: {list(item.keys())}")
                            if "text" in item:
                                print(f"         Text: {item['text'][:50]}...")
                            if "tagName" in item:
                                print(f"         Tag: {item['tagName']}")
                            if "href" in item:
                                print(f"         Href: {item['href'][:50]}...")
            elif "elements" in result:
                print(f"   Found 'elements' key")
            else:
                print(f"   No 'content' or 'elements' key found")
    
    # Get web content
    print("\n3. Getting web content...")
    content_result = client._call_mcp("chrome_get_web_content")
    print(f"   Result type: {type(content_result)}")
    
    if "result" in content_result:
        result = content_result["result"]
        print(f"   Content object type: {type(result)}")
        if hasattr(result, 'content'):
            print(f"   Content sample: {str(result.content)[:200]}...")

if __name__ == "__main__":
    debug_mcp()
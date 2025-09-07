#!/usr/bin/env python3

import json
import os

def test_mock_elements_parsing():
    """Test element parsing logic with mock data."""
    print("🧪 Testing mock element parsing logic...")
    
    # Create mock elements.json file for testing
    mock_data = [
        {
            "text": json.dumps({
                "elements": [
                    {
                        "type": "link",
                        "text": "MarineTraffic.com - OCEAN INTERVENTION (Offshore Support Vessel) IMO:1011621 MMSI:366614000 specifications and details",
                        "selector": "div.g:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1)",
                        "isInteractive": True,
                        "disabled": False,
                        "href": "https://www.marinetraffic.com/vessel/11621"
                    },
                    {
                        "type": "link", 
                        "text": "VesselFinder - OCEAN INTERVENTION vessel details and tracking information",
                        "selector": "div.g:nth-child(2) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1)",
                        "isInteractive": True,
                        "disabled": False,
                        "href": "https://www.vesselfinder.com/vessel/366614000"
                    },
                    {
                        "type": "link",
                        "text": "Images for OCEAN INTERVENTION",
                        "selector": "div.images-link",
                        "isInteractive": True,
                        "disabled": False,
                        "href": "https://www.google.com/search?tbm=isch"
                    },
                    {
                        "type": "button",
                        "text": "Accept all cookies",
                        "selector": "button[data-testid='cookie-accept']",
                        "isInteractive": True,
                        "disabled": False
                    }
                ]
            })
        }
    ]
    
    # Write mock data
    with open("elements.json", "w") as f:
        json.dump(mock_data, f, indent=2)
    
    print("✅ Created mock elements.json file")
    return mock_data

def test_parsing_logic():
    """Test the parsing logic used in the improved implementation."""
    print("\n🔍 Testing parsing logic...")
    
    try:
        # Read the JSON file
        with open("elements.json", "r") as file:
            raw_data = json.load(file)

        # Check if raw_data is a list and has the expected structure
        if not isinstance(raw_data, list) or not raw_data:
            print("❌ Error: elements.json does not contain a valid list or is empty")
            return []

        print(f"📄 Raw data is list with {len(raw_data)} items")

        # Parse the nested JSON string from the 'text' field
        nested_json = json.loads(raw_data[0].get("text", "{}"))
        elements = nested_json.get("elements", [])

        if not elements:
            print("❌ Error: No elements found in the nested JSON")
            return []

        print(f"✅ Parsed nested JSON with {len(elements)} elements")
        
        return elements

    except FileNotFoundError:
        print("❌ Error: elements.json file not found in the current directory")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error: Failed to parse JSON - {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Error: An unexpected error occurred - {str(e)}")
        return []

def test_search_result_filtering(elements):
    """Test search result filtering logic."""
    print("\n🔗 Testing search result filtering...")
    
    search_result_elements = []
    skip_terms = ["sign in", "images", "videos", "news", "shopping", "more", "tools", "settings"]
    
    print(f"📋 Processing {len(elements)} elements:")
    
    for i, element in enumerate(elements):
        if isinstance(element, dict):
            text = element.get("text", "")
            elem_type = element.get("type", "")
            selector = element.get("selector", "")
            is_interactive = element.get("isInteractive", False)
            disabled = element.get("disabled", True)
            
            print(f"[{i}] Type: {elem_type:8} | Interactive: {str(is_interactive):5} | Text: {text[:60]}...")
            
            # Apply filtering logic from improved implementation
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
                print(f"    ✅ SELECTED as search result")
            else:
                reasons = []
                if elem_type != "link":
                    reasons.append("not a link")
                if not is_interactive:
                    reasons.append("not interactive")
                if disabled:
                    reasons.append("disabled")
                if not text or len(text) <= 20:
                    reasons.append("insufficient text")
                if "http" not in text.lower() and "www." not in text.lower():
                    reasons.append("no URL indicators")
                if any(skip in text.lower() for skip in skip_terms):
                    reasons.append("contains skip terms")
                
                print(f"    ⏭️  SKIPPED: {', '.join(reasons)}")
    
    print(f"\n🎯 Found {len(search_result_elements)} valid search result links:")
    for i, elem in enumerate(search_result_elements):
        print(f"  [{i}]: {elem['text'][:80]}...")
        print(f"       Selector: {elem['selector']}")
    
    return search_result_elements

def test_cookie_detection(elements):
    """Test cookie dialog detection."""
    print("\n🍪 Testing cookie dialog detection...")
    
    cookie_terms = ["accept", "allow", "agree", "consent", "continue", "ok", "got it"]
    found_cookies = []
    
    for element in elements:
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
        print(f"  🍪 {cookie['text']} (selector: {cookie['selector']})")

def cleanup():
    """Clean up test files."""
    try:
        if os.path.exists("elements.json"):
            os.remove("elements.json")
            print("🧹 Cleaned up test files")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

if __name__ == "__main__":
    print("🚀 Running comprehensive element parsing tests...\n")
    
    try:
        # Create mock data
        mock_data = test_mock_elements_parsing()
        
        # Test parsing
        elements = test_parsing_logic()
        
        if elements:
            # Test filtering
            search_results = test_search_result_filtering(elements)
            
            # Test cookie detection
            test_cookie_detection(elements)
            
            print(f"\n📊 Summary:")
            print(f"  • Total elements parsed: {len(elements)}")
            print(f"  • Valid search results: {len(search_results)}")
            print(f"  • Cookie dialogs detected: {len([e for e in elements if e.get('type') == 'button' and any(term in e.get('text', '').lower() for term in ['accept', 'allow', 'agree'])])}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
    finally:
        cleanup()
import json

try:
    # Read the JSON file
    with open("elements.json", "r") as file:
        raw_data = json.load(file)

    # Check if raw_data is a list and has the expected structure
    if not isinstance(raw_data, list) or not raw_data:
        print("Error: elements.json does not contain a valid list or is empty")
        exit(1)

    # Parse the nested JSON string from the 'text' field
    nested_json = json.loads(raw_data[0].get("text", "{}"))
    elements = nested_json.get("elements", [])

    if not elements:
        print("Error: No elements found in the nested JSON")
        exit(1)

    # Find the first clickable link with 'http' in its text
    for element in elements:
        if (isinstance(element, dict) and
                element.get("type") == "link" and
                element.get("isInteractive", False) and
                not element.get("disabled", True) and
                "http" in element.get("text", "").lower()):
            first_link = {
                "selector": element.get("selector", ""),
                "text": element.get("text", "")[:200],
                "type": element.get("type", "")
            }
            print("First clickable link with 'http' found:")
            print(f"- Selector: {first_link['selector']}")
            print(f"- Text: {first_link['text']}")
            print(f"- Type: {first_link['type']}")
            break
    else:
        print("No clickable links with 'http' found.")

    search_result_elements = []
    skip_terms = ["sign in", "images", "videos", "news", "shopping", "more", "tools", "settings"]
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
    print(search_result_elements)

except FileNotFoundError:
    print("Error: elements.json file not found in the current directory")
except json.JSONDecodeError as e:
    print(f"Error: Failed to parse JSON - {str(e)}")
except Exception as e:
    print(f"Error: An unexpected error occurred - {str(e)}")
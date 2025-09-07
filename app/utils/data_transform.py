"""
Data transformation and formatting utilities
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse various timestamp formats into datetime object.
    
    Args:
        timestamp_str: Timestamp string in various formats
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S", 
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    return None


def format_vessel_name(name: str) -> str:
    """
    Format vessel name for consistent display.
    
    Args:
        name: Raw vessel name
        
    Returns:
        Formatted vessel name
    """
    if not name:
        return "UNKNOWN VESSEL"
    
    # Remove extra whitespace and convert to uppercase
    formatted = re.sub(r'\s+', ' ', name.strip().upper())
    
    # Remove common prefixes that might be inconsistent
    prefixes = ["M/V", "MV", "S/S", "SS", "M.V.", "S.S."]
    for prefix in prefixes:
        if formatted.startswith(prefix + " "):
            formatted = formatted[len(prefix) + 1:]
            break
    
    return formatted


def format_mmsi(mmsi: str) -> str:
    """
    Format MMSI for consistent display.
    
    Args:
        mmsi: Raw MMSI string
        
    Returns:
        Formatted MMSI (9 digits with leading zeros if needed)
    """
    if not mmsi:
        return "000000000"
    
    # Remove non-digits
    digits_only = re.sub(r'[^0-9]', '', str(mmsi))
    
    # Pad to 9 digits
    return digits_only.zfill(9)


def extract_vessel_specs(metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and format vessel specifications from metadata.
    
    Args:
        metadata: Raw metadata dictionary
        
    Returns:
        Formatted specifications dict
    """
    specs = {}
    
    # Handle nested metadata structure from LLM extraction
    if isinstance(metadata, dict):
        if "metadata" in metadata:
            vessel_meta = metadata["metadata"]
            if isinstance(vessel_meta, dict):
                # Extract key specifications
                specs["vessel_name"] = vessel_meta.get("vessel_name", "")
                specs["imo_number"] = vessel_meta.get("imo_number", "")
                specs["vessel_type"] = vessel_meta.get("vessel_type", "")
                specs["flag"] = vessel_meta.get("flag", "")
                
                # Handle dimensions
                dimensions = vessel_meta.get("dimensions", {})
                if dimensions:
                    specs["length"] = dimensions.get("length_overall", "")
                    specs["beam"] = dimensions.get("beam", "")
                    specs["draft"] = dimensions.get("draft", "")
                
                # Handle tonnage
                tonnage = vessel_meta.get("tonnage", {})
                if tonnage:
                    specs["gross_tonnage"] = tonnage.get("gross_tonnage", "")
                    specs["deadweight"] = tonnage.get("deadweight", "")
    
    # Clean up empty values
    return {k: v for k, v in specs.items() if v and v.lower() not in ["null", "none", "unknown"]}


def summarize_research_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a summary of research results for reporting.
    
    Args:
        results: List of WebSearchResult-like dictionaries
        
    Returns:
        Summary statistics and highlights
    """
    if not results:
        return {
            "total_sources": 0,
            "has_images": False,
            "content_length": 0,
            "reliability": "unknown"
        }
    
    total_sources = len(results)
    total_images = sum(len(result.get("images_found", [])) for result in results)
    total_content = sum(len(result.get("content_snippet", "")) for result in results)
    
    # Count reliability indicators
    reliability_counts = {}
    for result in results:
        reliability = result.get("reliability", "unknown")
        reliability_counts[reliability] = reliability_counts.get(reliability, 0) + 1
    
    # Determine overall reliability
    if reliability_counts.get("high", 0) > 0:
        overall_reliability = "high"
    elif reliability_counts.get("medium", 0) > 0:
        overall_reliability = "medium"
    elif reliability_counts.get("low", 0) > 0:
        overall_reliability = "low"
    else:
        overall_reliability = "unknown"
    
    return {
        "total_sources": total_sources,
        "has_images": total_images > 0,
        "total_images": total_images,
        "content_length": total_content,
        "reliability": overall_reliability,
        "reliability_breakdown": reliability_counts
    }


def clean_html_content(content: str, max_length: int = 2000) -> str:
    """
    Clean HTML content for display, removing tags and extra whitespace.
    
    Args:
        content: Raw HTML content
        max_length: Maximum length to return
        
    Returns:
        Cleaned text content
    """
    if not content:
        return ""
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', content)
    
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # Trim to max length
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length] + "..."
    
    return clean_text.strip()
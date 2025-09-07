"""
Legacy tools module for backward compatibility.

This module provides backward-compatible tool functions that use the new
modular architecture under the hood.
"""

from langchain_core.tools import tool
from typing import List

# Import new modular services
from app.tools.elasticsearch_client import elasticsearch_service
from app.tools.chrome_mcp_client import chrome_mcp_client
from app.models.vessel import VesselData
from app.models.research import WebSearchResult


@tool
def search_vessels_by_distance(min_distance_miles: float = 50.0, date: str = "2022-01-01") -> List[VesselData]:
    """Search for vessels with long tracks using optimized Elasticsearch aggregations."""
    return elasticsearch_service.search_vessels_by_distance(
        min_distance_miles=min_distance_miles,
        date=date
    )


@tool  
def web_research_vessel(
    vessel_name: str, 
    mmsi: str, 
    imo: str = "", 
    research_focus: str = "specifications",
    num_links: int = 3
) -> List[WebSearchResult]:
    """Research vessel information using multi-step LLM-guided web search."""
    # Configure client for this search
    chrome_mcp_client.num_links = num_links
    
    # Perform research
    return chrome_mcp_client.intelligent_search_and_navigate(
        query=f"{vessel_name} MMSI {mmsi} {imo} ship vessel specifications",
        research_focus=research_focus,
        vessel_mmsi=mmsi
    )


@tool
def download_vessel_image(image_url: str, vessel_name: str) -> str:
    """Download vessel image from URL."""
    import requests
    import os
    
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


# Legacy compatibility - expose the mcp_client
mcp_client = chrome_mcp_client

# For backward compatibility, also expose the services
__all__ = [
    'search_vessels_by_distance',
    'web_research_vessel', 
    'download_vessel_image',
    'mcp_client'
]
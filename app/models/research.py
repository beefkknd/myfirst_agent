"""
Research data models - External data sources and web research results
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class WebSearchResult(BaseModel):
    """
    Web research result containing extracted vessel information from external sources.
    
    Represents data gathered from web searches, including structured metadata
    extracted via LLM analysis and associated media assets.
    """
    url: str = Field(..., description="Source URL where data was extracted")
    title: Optional[str] = Field(None, description="Page title or source description")
    content_snippet: str = Field(default="", description="Raw extracted content text")
    
    # Media and assets
    images_found: List[str] = Field(
        default_factory=list,
        description="URLs or paths to vessel images found on the source page"
    )
    
    # Structured extracted data
    metadata_extracted: Dict[str, Any] = Field(
        default_factory=dict,
        description="LLM-extracted structured vessel information and metadata"
    )
    
    # Association with vessels
    mmsi: str = Field(default="", description="MMSI of vessel this research relates to")
    
    # Quality indicators
    status: Optional[str] = Field(
        None, 
        description="Processing status: success, partial, failed, unknown"
    )
    reliability: Optional[str] = Field(
        None,
        description="Data reliability assessment: high, medium, low, pending"
    )
    
    class Config:
        """Pydantic model configuration"""
        json_encoders = {
            # Custom encoders for special data types
        }
        
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Extract key metadata fields for display"""
        if not self.metadata_extracted:
            return {}
            
        # Extract commonly used metadata fields
        summary = {}
        
        # Handle structured metadata from LLM extraction
        if isinstance(self.metadata_extracted, dict):
            if "details" in self.metadata_extracted:
                summary["key_details"] = self.metadata_extracted["details"][:3]  # Top 3 details
                
            if "metadata" in self.metadata_extracted:
                metadata = self.metadata_extracted["metadata"]
                if isinstance(metadata, dict):
                    # Extract vessel specifications
                    summary.update({
                        "vessel_specs": {
                            k: v for k, v in metadata.items() 
                            if k in ["vessel_name", "vessel_type", "flag", "dimensions"]
                            and v is not None
                        }
                    })
                    
        return summary
        
    def has_quality_data(self) -> bool:
        """Check if this result contains substantial quality data"""
        return (
            len(self.content_snippet) > 200 or  # Substantial content
            (self.metadata_extracted and len(str(self.metadata_extracted)) > 100) or  # Rich metadata
            len(self.images_found) > 0  # Has media assets
        )
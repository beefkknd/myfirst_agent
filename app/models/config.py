"""
Configuration models - User preferences and system configuration
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """Supported LLM model types"""
    OLLAMA = "ollama"
    GEMINI = "gemini"


class PromptObjective(BaseModel):
    """User's analysis objective and criteria"""
    description: str = Field(..., description="What the user wants to analyze")
    criteria: Dict[str, Any] = Field(..., description="Specific criteria for vessel selection")


class VesselCriteria(BaseModel):
    """Vessel search and filtering criteria"""
    min_distance_miles: float = Field(50.0, description="Minimum distance traveled in miles")
    vessel_types: Optional[List[str]] = Field(None, description="Specific vessel types to filter")
    time_range: str = Field("2022-01-01", description="Date range for analysis")


class WebResearchConfig(BaseModel):
    """Web research configuration and parameters"""
    max_pages: int = Field(3, description="Maximum number of pages to visit per vessel")
    search_terms: List[str] = Field(default_factory=list, description="Additional search terms")
    extract_images: bool = Field(True, description="Whether to extract vessel images")
    research_focus: str = Field("specifications", description="Research focus area")


class ReportConfig(BaseModel):
    """Report generation configuration"""
    include_map: bool = Field(True, description="Include Folium map visualization")
    include_photos: bool = Field(True, description="Include vessel photos")
    output_format: str = Field("html", description="Output format for report")


class AnalysisPrompt(BaseModel):
    """
    Complete user prompt configuration combining all analysis parameters.
    
    This is the root configuration model that contains all user preferences
    and system settings for a vessel analysis run.
    """
    objective: PromptObjective = Field(..., description="User's analysis goal")
    vessel_criteria: VesselCriteria = Field(..., description="Vessel search parameters")
    web_research: WebResearchConfig = Field(..., description="Research configuration")
    report_config: ReportConfig = Field(..., description="Output preferences")
    
    class Config:
        """Pydantic model configuration"""
        use_enum_values = True
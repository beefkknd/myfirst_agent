from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"

class PromptObjective(BaseModel):
    description: str = Field(..., description="What the user wants to analyze")
    criteria: Dict[str, Any] = Field(..., description="Specific criteria for vessel selection")

class VesselCriteria(BaseModel):
    min_distance_miles: float = Field(50.0, description="Minimum distance traveled in miles")
    vessel_types: Optional[List[str]] = Field(None, description="Specific vessel types to filter")
    time_range: str = Field("2022-01-01", description="Date range for analysis")

class WebResearchConfig(BaseModel):
    max_pages: int = Field(3, description="Maximum number of pages to visit")
    search_terms: List[str] = Field(default_factory=list, description="Additional search terms")
    extract_images: bool = Field(True, description="Whether to extract vessel images")
    research_focus: str = Field("specifications", description="Research focus area")

class ReportConfig(BaseModel):
    include_map: bool = Field(True, description="Include Folium map visualization")
    include_photos: bool = Field(True, description="Include vessel photos")
    output_format: str = Field("html", description="Output format for report")

class AnalysisPrompt(BaseModel):
    objective: PromptObjective
    vessel_criteria: VesselCriteria
    web_research: WebResearchConfig
    report_config: ReportConfig

class VesselData(BaseModel):
    mmsi: str
    vessel_name: str
    imo: Optional[str] = None
    call_sign: Optional[str] = None
    vessel_type: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draft: Optional[float] = None
    track_points: List[Dict[str, Any]] = Field(default_factory=list)
    total_distance_miles: float = 0.0

class WebSearchResult(BaseModel):
    url: str
    title: Optional[str] = None
    content_snippet: str = ""
    images_found: List[str] = Field(default_factory=list)
    metadata_extracted: Dict[str, Any] = Field(default_factory=dict)
    mmsi: str = ""  # Associate research result with specific vessel MMSI
    status: Optional[str] = None  # Status for tab display (success, partial, failed, unknown)
    reliability: Optional[str] = None  # Reliability badge display

class AnalysisState(BaseModel):
    prompt: Optional[AnalysisPrompt] = None
    prompt_file: Optional[str] = None
    selected_vessels: List[VesselData] = Field(default_factory=list)
    web_research_results: List[WebSearchResult] = Field(default_factory=list)  # Keep for backward compatibility during transition
    vessel_research_results: Dict[str, List[WebSearchResult]] = Field(default_factory=dict)  # MMSI -> research results
    report_content: str = ""
    report_path: Optional[str] = None
    current_step: str = "parse_prompt"
    errors: List[str] = Field(default_factory=list)
    llm_decision: Optional[str] = None
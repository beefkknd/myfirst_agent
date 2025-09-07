"""
Workflow state models - LangGraph workflow orchestration state
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .config import AnalysisPrompt
from .vessel import VesselData
from .research import WebSearchResult


class AnalysisState(BaseModel):
    """
    Central workflow state for LangGraph vessel analysis orchestration.
    
    This model serves as the data bus between all workflow nodes,
    accumulating data and state as the analysis progresses through
    the LangGraph state machine.
    """
    
    # Input configuration
    prompt: Optional[AnalysisPrompt] = Field(
        None,
        description="Parsed user analysis configuration"
    )
    prompt_file: Optional[str] = Field(
        None,
        description="Path to source prompt file if loaded from file"
    )
    
    # Core domain data
    selected_vessels: List[VesselData] = Field(
        default_factory=list,
        description="Vessels found and selected for analysis"
    )
    
    # Research results (both legacy and new formats for compatibility)
    web_research_results: List[WebSearchResult] = Field(
        default_factory=list,
        description="Legacy research results format (backward compatibility)"
    )
    vessel_research_results: Dict[str, List[WebSearchResult]] = Field(
        default_factory=dict,
        description="Vessel-specific research results keyed by MMSI"
    )
    
    # Generated outputs
    report_content: str = Field(
        default="",
        description="Generated report content (intermediate)"
    )
    report_path: Optional[str] = Field(
        None,
        description="Path to final generated report file"
    )
    
    # Workflow state tracking
    current_step: str = Field(
        default="parse_prompt",
        description="Current workflow step identifier"
    )
    
    # Error handling
    errors: List[str] = Field(
        default_factory=list,
        description="Accumulated errors during analysis"
    )
    
    # LLM decision points
    llm_decision: Optional[str] = Field(
        None,
        description="LLM decision for workflow routing (write_report, more_research, etc.)"
    )
    
    class Config:
        """Pydantic model configuration"""
        arbitrary_types_allowed = True  # Allow complex types in fields
        
    def add_error(self, error: str) -> None:
        """Add an error to the error list"""
        self.errors.append(error)
        
    def has_errors(self) -> bool:
        """Check if any errors have occurred"""
        return len(self.errors) > 0
        
    def get_vessel_count(self) -> int:
        """Get the number of selected vessels"""
        return len(self.selected_vessels)
        
    def get_research_summary(self) -> Dict[str, Any]:
        """Get summary of research results across all vessels"""
        total_sources = sum(len(results) for results in self.vessel_research_results.values())
        vessels_with_research = len([mmsi for mmsi, results in self.vessel_research_results.items() if results])
        
        return {
            "total_research_sources": total_sources,
            "vessels_with_research": vessels_with_research,
            "total_vessels": len(self.selected_vessels),
            "legacy_results_count": len(self.web_research_results)
        }
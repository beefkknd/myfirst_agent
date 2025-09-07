"""
Data Models for Vessel Analysis System

Organized by concern:
- vessel: Core vessel domain models
- research: Web research and external data models  
- config: Configuration and user preference models
- workflow: LangGraph workflow state models
"""

from .vessel import VesselData
from .research import WebSearchResult
from .config import AnalysisPrompt, VesselCriteria, WebResearchConfig, ReportConfig, PromptObjective, ModelType
from .workflow import AnalysisState

__all__ = [
    # Domain models
    'VesselData',
    'WebSearchResult',
    
    # Configuration models
    'AnalysisPrompt', 
    'VesselCriteria',
    'WebResearchConfig', 
    'ReportConfig',
    'PromptObjective',
    'ModelType',
    
    # Workflow models
    'AnalysisState'
]
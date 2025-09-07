"""
Legacy models module for backward compatibility.

This module re-exports all models from the new modular structure
to maintain backward compatibility with existing code.
"""

# Re-export all models from the new modular structure
from app.models.vessel import VesselData
from app.models.research import WebSearchResult
from app.models.config import (
    ModelType, 
    PromptObjective, 
    VesselCriteria, 
    WebResearchConfig, 
    ReportConfig, 
    AnalysisPrompt
)
from app.models.workflow import AnalysisState

# Maintain exact same exports as original models.py
__all__ = [
    'ModelType',
    'PromptObjective', 
    'VesselCriteria',
    'WebResearchConfig',
    'ReportConfig', 
    'AnalysisPrompt',
    'VesselData',
    'WebSearchResult',
    'AnalysisState'
]
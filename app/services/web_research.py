"""
Web research service orchestration.

High-level service that orchestrates web research workflows using
the ChromeMCPClient tool.
"""

from typing import List, Dict, Any, Optional
from ..models.vessel import VesselData
from ..models.research import WebSearchResult
from ..tools.chrome_mcp_client import chrome_mcp_client


class WebResearchService:
    """
    High-level service for web research operations.
    
    Orchestrates web research workflows using the underlying
    ChromeMCPClient tool.
    """
    
    def __init__(self, llm=None):
        """
        Initialize web research service.
        
        Args:
            llm: LLM instance for intelligent research guidance
        """
        self.chrome_client = chrome_mcp_client
        if llm:
            self.chrome_client.llm = llm
        print("🌐 WebResearchService initialized")
    
    def research_vessel(
        self,
        vessel: VesselData,
        research_focus: str = "specifications",
        num_sources: int = 3
    ) -> List[WebSearchResult]:
        """
        Research a single vessel using web search.
        
        Args:
            vessel: VesselData object to research
            research_focus: Research focus area
            num_sources: Number of web sources to process
            
        Returns:
            List of WebSearchResult objects
        """
        print(f"🔍 Researching vessel: {vessel.vessel_name} ({vessel.mmsi})")
        
        try:
            # Configure client for this research
            original_num_links = self.chrome_client.num_links
            self.chrome_client.num_links = num_sources
            
            # Build search query
            search_terms = [vessel.vessel_name]
            if vessel.mmsi:
                search_terms.append(f"MMSI {vessel.mmsi}")
            if vessel.imo and vessel.imo != "IMO0000000":
                search_terms.append(f"IMO {vessel.imo}")
            
            query = " ".join(search_terms) + " ship vessel specifications"
            
            # Perform research
            results = self.chrome_client.intelligent_search_and_navigate(
                query=query,
                research_focus=research_focus,
                vessel_mmsi=vessel.mmsi
            )
            
            # Ensure all results have MMSI association
            for result in results:
                if not result.mmsi:
                    result.mmsi = vessel.mmsi
            
            # Restore original configuration
            self.chrome_client.num_links = original_num_links
            
            print(f"✅ Research complete: {len(results)} sources found")
            return results
            
        except Exception as e:
            print(f"❌ Research failed for {vessel.vessel_name}: {e}")
            return []
    
    def research_multiple_vessels(
        self,
        vessels: List[VesselData],
        research_focus: str = "specifications",
        num_sources: int = 3
    ) -> Dict[str, List[WebSearchResult]]:
        """
        Research multiple vessels and organize results by MMSI.
        
        Args:
            vessels: List of VesselData objects to research
            research_focus: Research focus area
            num_sources: Number of web sources per vessel
            
        Returns:
            Dictionary mapping MMSI to list of WebSearchResult objects
        """
        print(f"🔍 Researching {len(vessels)} vessels...")
        
        vessel_research_results = {}
        successful_research = 0
        
        for i, vessel in enumerate(vessels, 1):
            print(f"🚢 Processing vessel {i}/{len(vessels)}: {vessel.vessel_name}")
            
            try:
                results = self.research_vessel(
                    vessel=vessel,
                    research_focus=research_focus,
                    num_sources=num_sources
                )
                
                if results and not all(r.url == "error" for r in results):
                    vessel_research_results[vessel.mmsi] = results
                    successful_research += 1
                    print(f"✅ Research successful for {vessel.vessel_name}")
                else:
                    print(f"⚠️ No quality results found for {vessel.vessel_name}")
                    
            except Exception as e:
                print(f"❌ Research error for {vessel.vessel_name}: {e}")
                continue
        
        print(f"🎯 Multi-vessel research complete: {successful_research}/{len(vessels)} vessels")
        return vessel_research_results
    
    def analyze_research_quality(self, results: List[WebSearchResult]) -> Dict[str, Any]:
        """
        Analyze the quality and completeness of research results.
        
        Args:
            results: List of WebSearchResult objects
            
        Returns:
            Dictionary with quality analysis
        """
        if not results:
            return {
                "quality_score": 0.0,
                "has_quality_data": False,
                "issues": ["No research results available"]
            }
        
        quality_metrics = {
            "total_sources": len(results),
            "error_sources": len([r for r in results if r.url == "error"]),
            "quality_sources": len([r for r in results if r.has_quality_data()]),
            "has_images": len([r for r in results if r.images_found]) > 0,
            "has_metadata": len([r for r in results if r.metadata_extracted]) > 0,
            "total_content_length": sum(len(r.content_snippet) for r in results)
        }
        
        # Calculate quality score
        valid_sources = quality_metrics["total_sources"] - quality_metrics["error_sources"]
        if valid_sources == 0:
            quality_score = 0.0
        else:
            quality_score = quality_metrics["quality_sources"] / valid_sources
        
        # Identify issues
        issues = []
        if quality_metrics["error_sources"] > 0:
            issues.append(f"{quality_metrics['error_sources']} sources had errors")
        
        if quality_metrics["total_content_length"] < 500:
            issues.append("Insufficient content extracted")
        
        if not quality_metrics["has_metadata"]:
            issues.append("No structured metadata extracted")
        
        return {
            "quality_score": quality_score,
            "has_quality_data": quality_score > 0.5,
            "metrics": quality_metrics,
            "issues": issues
        }
    
    def get_research_summary(self, vessel_research: Dict[str, List[WebSearchResult]]) -> Dict[str, Any]:
        """
        Get summary statistics for vessel research results.
        
        Args:
            vessel_research: Dictionary mapping MMSI to research results
            
        Returns:
            Dictionary with summary statistics
        """
        total_sources = sum(len(results) for results in vessel_research.values())
        vessels_with_research = len([mmsi for mmsi, results in vessel_research.items() if results])
        total_images = sum(
            len(result.images_found) 
            for results in vessel_research.values() 
            for result in results
        )
        
        # Quality analysis
        quality_sources = 0
        error_sources = 0
        for results in vessel_research.values():
            for result in results:
                if result.url == "error":
                    error_sources += 1
                elif result.has_quality_data():
                    quality_sources += 1
        
        return {
            "total_vessels_researched": len(vessel_research),
            "vessels_with_results": vessels_with_research,
            "total_sources": total_sources,
            "quality_sources": quality_sources,
            "error_sources": error_sources,
            "total_images": total_images,
            "average_sources_per_vessel": total_sources / len(vessel_research) if vessel_research else 0,
            "success_rate": vessels_with_research / len(vessel_research) if vessel_research else 0
        }
    
    def configure_llm(self, llm) -> None:
        """
        Configure the LLM for intelligent research guidance.
        
        Args:
            llm: LLM instance to use for research decisions
        """
        self.chrome_client.llm = llm
        print("🧠 LLM configured for intelligent research guidance")
    
    def check_service_health(self) -> Dict[str, Any]:
        """
        Check the health of the web research service.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Basic service check
            has_llm = self.chrome_client.llm is not None
            config_loaded = self.chrome_client.server_params is not None
            
            return {
                "service_status": "operational",
                "chrome_mcp_configured": config_loaded,
                "llm_available": has_llm,
                "config_path": self.chrome_client.config_path,
                "dependencies": {
                    "mcp_chrome_bridge": config_loaded,
                    "llm": has_llm
                }
            }
        except Exception as e:
            return {
                "service_status": "error", 
                "error": str(e),
                "dependencies": {
                    "mcp_chrome_bridge": False,
                    "llm": False
                }
            }


# Global service instance
web_research_service = WebResearchService()
import argparse
import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

# Import from new modular structure
from app.models import AnalysisPrompt, AnalysisState, VesselCriteria, WebResearchConfig, ReportConfig, PromptObjective
from app.tools import ReportWriter, ElasticsearchService, ChromeMCPClient
from app.services import VesselSearchService, WebResearchService

load_dotenv()

class VesselAnalysisAgent:
    def __init__(self, model_type: str = "ollama"):
        self.model_type = model_type
        
        # Initialize LLM based on type
        if model_type.lower() == "ollama":
            self.llm = ChatOllama(model="qwen3:8b", temperature=0.1)
        else:  # gemini
            self.llm = ChatOllama(model="qwen3:8b", temperature=0.1)
        
        # Initialize services with LLM
        self.report_writer = ReportWriter()
        self.vessel_search_service = VesselSearchService()
        self.web_research_service = WebResearchService(llm=self.llm)
        
        # Create tool functions for LangGraph
        self.tools = [self._search_vessels_tool(), self._research_vessel_tool(), self._download_image_tool()]
        self.tool_node = ToolNode(self.tools)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    # Tool Functions for LangGraph
    def _search_vessels_tool(self):
        """Tool function for vessel search"""
        from langchain_core.tools import tool
        
        @tool
        def search_vessels_by_distance(min_distance_miles: float = 50.0, date: str = "2022-01-01"):
            """Search for vessels with long tracks using optimized Elasticsearch aggregations."""
            return self.vessel_search_service.find_long_distance_vessels(
                min_distance_miles=min_distance_miles,
                date=date,
                max_vessels=10
            )
        return search_vessels_by_distance
    
    def _research_vessel_tool(self):
        """Tool function for vessel research"""
        from langchain_core.tools import tool
        
        @tool
        def web_research_vessel(vessel_name: str, mmsi: str, imo: str = "", research_focus: str = "specifications"):
            """Research vessel information using multi-step LLM-guided web search."""
            from app.models.vessel import VesselData
            vessel = VesselData(mmsi=mmsi, vessel_name=vessel_name, imo=imo)
            return self.web_research_service.research_vessel(
                vessel=vessel,
                research_focus=research_focus,
                num_sources=3
            )
        return web_research_vessel
    
    def _download_image_tool(self):
        """Tool function for image download"""
        from langchain_core.tools import tool
        import requests
        import os
        
        @tool
        def download_vessel_image(image_url: str, vessel_name: str) -> str:
            """Download vessel image from URL."""
            try:
                response = requests.get(image_url, stream=True, timeout=10)
                if response.status_code == 200:
                    os.makedirs("reports/images", exist_ok=True)
                    safe_name = "".join(c for c in vessel_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    filename = f"reports/images/{safe_name}_{hash(image_url) % 10000}.jpg"
                    
                    with open(filename, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return filename
            except Exception as e:
                return f"Download failed: {str(e)}"
            return "Download failed"
        return download_vessel_image

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with LLM-driven decision points."""
        workflow = StateGraph(AnalysisState)
        
        # Add nodes with node_ prefix
        workflow.add_node("node_parse_prompt", self.node_parse_prompt)
        workflow.add_node("node_fetch_tracks", self.node_fetch_tracks)
        workflow.add_node("node_internet_search", self.node_internet_search)
        workflow.add_node("node_evaluate_info", self.node_evaluate_info)
        workflow.add_node("node_write_report", self.node_write_report)
        workflow.add_node("node_review_report", self.node_review_report)
        workflow.add_node("node_publish_report", self.node_publish_report)
        workflow.add_node("tool_node", self.tool_node)
        
        # Set entry point
        workflow.set_entry_point("node_parse_prompt")
        
        # Sequential flow to evaluation point
        workflow.add_edge("node_parse_prompt", "node_fetch_tracks")
        workflow.add_edge("node_fetch_tracks", "node_internet_search")
        workflow.add_edge("node_internet_search", "node_evaluate_info")
        
        # LLM decision point: continue or need more research
        workflow.add_conditional_edges(
            "node_evaluate_info",
            self.llm_decide_next_step,
            {
                "write_report": "node_write_report",
                "more_research": "node_internet_search",  # Cycle back for more research
                "different_vessel": "node_fetch_tracks",  # Try different vessel
                "end": END
            }
        )
        
        # Report generation flow
        workflow.add_edge("node_write_report", "node_review_report")
        workflow.add_edge("node_review_report", "node_publish_report")
        workflow.add_edge("node_publish_report", END)
        
        # Tool usage (simplified)
        workflow.add_edge("tool_node", "node_write_report")
        
        return workflow

    def node_parse_prompt(self, state: AnalysisState) -> AnalysisState:
        """LLM-driven parsing of structured prompt into analysis configuration."""
        print("🔍 LLM parsing analysis prompt...")
        
        # Read prompt file if provided, otherwise use default prompt text
        prompt_text = ""
        if hasattr(state, 'prompt_file') and state.prompt_file:
            try:
                with open(state.prompt_file, 'r') as f:
                    prompt_text = f.read()
            except:
                prompt_text = "Find vessels with exceptionally long tracks on 2022-01-01 to understand operational patterns."
        else:
            prompt_text = "Find vessels with exceptionally long tracks on 2022-01-01 to understand operational patterns."
        
        # LLM analyzes prompt and extracts requirements
        parsing_template = """
        Analyze this vessel analysis request and extract structured requirements:
        
        Prompt: {prompt_text}
        
        Extract and respond with JSON:
        {{
            "min_distance_miles": number (default 100),
            "date_range": "YYYY-MM-DD format",
            "vessel_focus": "longest_distance|most_unusual|specific_route",
            "research_priority": "specifications|operational_context|route_analysis",
            "max_web_pages": number (1-3, prefer 1 for focused research),
            "next_state": "fetch_tracks"
        }}
        """
        
        response = self.llm.invoke([
            ("system", "You are an expert vessel analysis task planner. Extract requirements from user prompts."),
            ("user", parsing_template.format(prompt_text=prompt_text))
        ])
        
        try:
            import json
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
            else:
                raise ValueError("No JSON found")
            
            parsed_req = json.loads(json_str)
            
            # Build structured prompt from LLM analysis
            state.prompt = AnalysisPrompt(
                objective=PromptObjective(
                    description=f"Vessel analysis focusing on {parsed_req.get('vessel_focus', 'longest_distance')}",
                    criteria={"min_distance_miles": parsed_req.get('min_distance_miles', 100)}
                ),
                vessel_criteria=VesselCriteria(min_distance_miles=float(parsed_req.get('min_distance_miles', 100))),
                web_research=WebResearchConfig(
                    max_pages=parsed_req.get('max_web_pages', 1), 
                    extract_images=True,
                    research_focus=parsed_req.get('research_priority', 'specifications')
                ),
                report_config=ReportConfig(include_map=True, include_photos=True)
            )
            
            print(f"✅ LLM extracted: {parsed_req.get('min_distance_miles', 100)} mile minimum, focus on {parsed_req.get('vessel_focus', 'longest_distance')}")
            
        except Exception as e:
            print(f"⚠️ LLM parsing failed, using defaults: {e}")
            # Fallback to defaults
            state.prompt = AnalysisPrompt(
                objective=PromptObjective(
                    description="Find vessels with long tracks to understand their operational patterns",
                    criteria={"min_distance_miles": 100, "focus": "longest distance"}
                ),
                vessel_criteria=VesselCriteria(min_distance_miles=100.0),
                web_research=WebResearchConfig(max_pages=1, extract_images=True),
                report_config=ReportConfig(include_map=True, include_photos=True)
            )
        
        state.current_step = "node_fetch_tracks"
        return state

    def node_fetch_tracks(self, state: AnalysisState) -> AnalysisState:
        """Fetch vessel tracks from Elasticsearch."""
        print("🚢 Fetching vessel tracks from Elasticsearch...")
        
        try:
            # Use the service to search vessels
            min_distance = state.prompt.vessel_criteria.min_distance_miles
            vessels = self.vessel_search_service.find_long_distance_vessels(
                min_distance_miles=min_distance,
                date="2022-01-01",
                max_vessels=5
            )
            
            state.selected_vessels = vessels[:5]  # Top 5 vessels
            print(f"Found {len(state.selected_vessels)} vessels with long tracks")
            
            for i, vessel in enumerate(state.selected_vessels[:3]):  # Show top 3
                print(f"{i+1}. {vessel.vessel_name} (MMSI: {vessel.mmsi}) - {vessel.total_distance_miles:.1f} miles")
                
        except Exception as e:
            state.errors.append(f"Error fetching tracks: {str(e)}")
            print(f"❌ Error: {e}")
        
        state.current_step = "node_internet_search"
        return state

    def node_internet_search(self, state: AnalysisState) -> AnalysisState:
        """Research ALL vessels using web search with multi-vessel processing."""
        print("🌐 Researching vessels on the internet...")
        
        if not state.selected_vessels:
            state.errors.append("No vessels to research")
            return state
        
        # Initialize vessel_research_results if not exists
        if not hasattr(state, 'vessel_research_results'):
            state.vessel_research_results = {}
        
        # Use the web research service for multi-vessel research
        try:
            research_focus = getattr(state.prompt.web_research, 'research_focus', 'specifications')
            num_sources = getattr(state.prompt.web_research, 'max_pages', 3)
            
            # Research all vessels using the service
            vessel_research_results = self.web_research_service.research_multiple_vessels(
                vessels=state.selected_vessels,
                research_focus=research_focus,
                num_sources=num_sources
            )
            
            # Update state with results
            state.vessel_research_results = vessel_research_results
            
            # Maintain backward compatibility with first vessel
            if vessel_research_results and state.selected_vessels:
                first_vessel_mmsi = state.selected_vessels[0].mmsi
                if first_vessel_mmsi in vessel_research_results:
                    state.web_research_results = vessel_research_results[first_vessel_mmsi]
            
            successful_research = len(vessel_research_results)
            total_vessels = len(state.selected_vessels)
            
        except Exception as e:
            error_msg = f"Multi-vessel research failed: {str(e)}"
            state.errors.append(error_msg)
            print(f"❌ {error_msg}")
            successful_research = 0
            total_vessels = len(state.selected_vessels)
        
        print(f"🎯 Multi-vessel research complete: {successful_research}/{total_vessels} vessels successfully researched")
        
        state.current_step = "node_evaluate_info"
        return state

    def node_evaluate_info(self, state: AnalysisState) -> AnalysisState:
        """LLM evaluates information sufficiency and decides next action."""
        print("🧠 LLM evaluating information sufficiency...")
        
        # Prepare data summary for LLM
        vessel_data = ""
        if state.selected_vessels:
            top_vessel = state.selected_vessels[0]
            vessel_data = f"Vessel: {top_vessel.vessel_name}, Distance: {top_vessel.total_distance_miles:.1f} miles"
        
        research_summary = ""
        if state.web_research_results:
            for i, result in enumerate(state.web_research_results[:2]):
                research_summary += f"Source {i+1}: {len(result.content_snippet)} chars from {result.url[:50]}\n"
        else:
            research_summary = "No research results found"
        
        evaluation_template = """
        Evaluate if we have sufficient information for a comprehensive vessel analysis report.
        
        Original Objective: Find and analyze vessels with exceptionally long tracks
        
        Current Data:
        - {vessel_data}
        - Research Results: {research_summary}
        - Errors: {errors}
        
        Assessment Questions:
        1. Do we have vessel identification and basic specifications?
        2. Do we have operational context for the long journey?
        3. Is the research data substantial enough (>500 chars)?
        4. Are there critical gaps that would make the report incomplete?
        
        Respond with one word only:
        - "write_report" if information is sufficient
        - "more_research" if we need more research on same vessel
        - "different_vessel" if current vessel has insufficient data
        - "end" if analysis should stop due to errors
        """
        
        try:
            response = self.llm.invoke([
                ("system", "You are an information quality assessor. Be decisive."),
                ("user", evaluation_template.format(
                    vessel_data=vessel_data,
                    research_summary=research_summary,
                    errors=str(state.errors) if state.errors else "None"
                ))
            ])
            
            decision = response.content.strip().lower()
            if decision not in ["write_report", "more_research", "different_vessel", "end"]:
                decision = "write_report"  # Default to continue
            
            state.llm_decision = decision
            print(f"🎯 LLM decision: {decision}")
            
        except Exception as e:
            print(f"⚠️ LLM evaluation failed: {e}")
            state.llm_decision = "write_report"  # Default to continue
        
        return state

    def llm_decide_next_step(self, state: AnalysisState) -> str:
        """Return the LLM's decision for workflow routing."""
        return getattr(state, 'llm_decision', 'write_report')

    def node_write_report(self, state: AnalysisState) -> AnalysisState:
        """Generate the vessel analysis report."""
        print("📝 Writing vessel analysis report...")
        
        try:
            report_path = self.report_writer.generate_report(state)
            state.report_path = report_path
            print(f"✅ Report generated: {report_path}")
            
        except Exception as e:
            state.errors.append(f"Report generation error: {str(e)}")
            print(f"❌ Report error: {e}")
        
        state.current_step = "node_review_report"
        return state

    def node_review_report(self, state: AnalysisState) -> AnalysisState:
        """Review and validate the generated report."""
        print("🔍 Reviewing report quality...")
        
        # Simple validation
        if state.report_path and os.path.exists(state.report_path):
            file_size = os.path.getsize(state.report_path)
            if file_size > 1000:  # At least 1KB
                print("✅ Report quality check passed")
            else:
                state.errors.append("Report file too small")
        else:
            state.errors.append("Report file not found")
            
        state.current_step = "node_publish_report"
        return state

    def node_publish_report(self, state: AnalysisState) -> AnalysisState:
        """Finalize and publish the report."""
        print("🚀 Publishing report...")
        
        if state.report_path:
            print(f"📊 Report available at: {state.report_path}")
            print(f"🎯 Analysis completed for {len(state.selected_vessels)} vessels")
            if state.selected_vessels:
                top_vessel = state.selected_vessels[0]
                print(f"🏆 Top vessel: {top_vessel.vessel_name} traveled {top_vessel.total_distance_miles:.1f} miles")
        
        return state

    def should_use_tools(self, state: AnalysisState) -> str:
        """Determine if tools should be used."""
        # For simplicity, don't use additional tools in conditional flow
        return "continue"

    def run_analysis(self, prompt_file: str = None) -> str:
        """Run the complete vessel analysis."""
        print("🚢 Starting Vessel Analysis Agent")
        print("=" * 50)
        
        # Load prompt if provided
        initial_state = AnalysisState()
        if prompt_file and os.path.exists(prompt_file):
            print(f"📋 Using prompt file: {prompt_file}")
            initial_state.prompt_file = prompt_file
        
        # Execute workflow
        final_state = None
        try:
            for output in self.app.stream(initial_state):
                final_state = list(output.values())[0]
                
        except Exception as e:
            print(f"❌ Workflow error: {e}")
            return None
        
        report_path = None
        # First, check if final_state is a dictionary and contains 'report_path'
        if isinstance(final_state, dict) and "report_path" in final_state:
            report_path = final_state["report_path"]
        # Then, check if final_state is an object with a 'report_path' attribute
        elif hasattr(final_state, "report_path"):
            report_path = final_state.report_path
        # Finally, handle the case where 'report_path' might be nested in 'messages' within a dictionary
        elif isinstance(final_state, dict) and "messages" in final_state:
            last_message = final_state["messages"][-1]
            if isinstance(last_message, dict) and "report_path" in last_message:
                report_path = last_message["report_path"]
            elif hasattr(last_message, "report_path"):
                report_path = last_message.report_path

        if report_path:
            return report_path
        else:
            print("❌ Analysis failed")
            if final_state and final_state.errors:
                for error in final_state.errors:
                    print(f"   - {error}")
            return None

def main():
    parser = argparse.ArgumentParser(description="Vessel Analysis Agent")
    parser.add_argument("--model", choices=["ollama", "gemini"], default="ollama",
                        help="Choose LLM model (default: ollama)")
    parser.add_argument("--prompt", type=str, help="Path to prompt file")
    parser.add_argument("--list-prompts", action="store_true", 
                        help="List available prompt files")
    
    args = parser.parse_args()
    
    if args.list_prompts:
        print("Available prompt files:")
        if os.path.exists("prompts"):
            for file in os.listdir("prompts"):
                if file.endswith(".md"):
                    print(f"  - {file}")
        else:
            print("  No prompts directory found")
        return
    
    # Initialize agent
    print(f"🤖 Initializing agent with {args.model.upper()} model...")
    agent = VesselAnalysisAgent(model_type=args.model)
    
    # Run analysis
    report_path = agent.run_analysis(args.prompt)
    
    if report_path:
        print("\n" + "=" * 50)
        print("🎉 ANALYSIS COMPLETE!")
        print(f"📊 Report saved to: {report_path}")
        print(f"🌐 Open in browser: file://{os.path.abspath(report_path)}")
    else:
        print("\n❌ Analysis failed. Check the logs above for details.")

if __name__ == "__main__":
    main()
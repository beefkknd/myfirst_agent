# LLM Task Unpacking System Design

## Overview
Design for LLM-driven prompt parsing and dynamic task sequence planning based on user requirements from structured markdown prompts.

## Prompt Structure Analysis (from prompt1.md)

### Current Structure
```markdown
# Vessel Analysis Prompt 1: Long Distance Investigation

## Objective
User intent and analysis goal

## Vessel Selection Criteria  
- Minimum distance: X miles
- Time range: YYYY-MM-DD
- Vessel types: [types]
- Priority: [ranking criteria]

## Web Research Configuration
- Maximum pages to visit: N
- Search terms: [terms]
- Extract vessel images: Yes/No
- Focus on: [research priorities]

## Report Requirements
- Include map: Yes/No
- Include photos: Yes/No  
- Output format: [format]
- Sections needed: [list]
```

## LLM Task Unpacking Architecture

### 1. Prompt Parser with Structured Output

```python
class PromptParser:
    def __init__(self, llm):
        self.llm = llm
        
    def parse_prompt(self, prompt_text: str) -> TaskSequence:
        """LLM parses user prompt and generates task sequence"""
        
        parsing_template = """
        You are a vessel analysis task planner. Analyze the user's request and extract:

        1. OBJECTIVE ANALYSIS:
        - What does the user want to investigate?
        - What's their main question or hypothesis?
        - What type of analysis is this? (distance, behavioral, comparative, etc.)

        2. VESSEL CRITERIA EXTRACTION:
        - Distance thresholds
        - Time ranges  
        - Vessel type preferences
        - Selection priorities

        3. RESEARCH SCOPE PLANNING:
        - Information priorities (specs, history, route analysis)
        - Quality vs quantity preferences
        - Special focus areas

        4. TASK SEQUENCE RECOMMENDATION:
        Based on the objectives, recommend which LangGraph states to execute and in what order.
        Consider whether this analysis needs:
        - Simple linear workflow
        - Iterative vessel comparison
        - Deep dive on single vessel
        - Comparative multi-vessel analysis

        User Prompt:
        {prompt_text}

        Respond in JSON format:
        {{
            "objective": {{
                "type": "distance_investigation|behavioral_analysis|comparative_study|route_analysis",
                "description": "detailed user intent",
                "hypothesis": "what user wants to prove/discover"
            }},
            "vessel_criteria": {{
                "min_distance_miles": float,
                "date_range": "YYYY-MM-DD or range",
                "vessel_types": ["list"],
                "selection_priority": "longest_distance|most_unusual|specific_route"
            }},
            "research_scope": {{
                "information_priorities": ["specs", "history", "route", "operational_context"],
                "depth_vs_breadth": "deep_single|broad_multiple",
                "special_focus": ["specific areas of interest"]
            }},
            "recommended_task_sequence": [
                {{
                    "state": "state_name",
                    "purpose": "why this state",
                    "success_criteria": "how to know it succeeded",
                    "can_repeat": true/false
                }}
            ]
        }}
        """
        
        response = self.llm.invoke([
            ("system", "You are an expert vessel analysis task planner."),
            ("user", parsing_template.format(prompt_text=prompt_text))
        ])
        
        return self._parse_llm_response(response.content)
```

### 2. Dynamic State Orchestration

```python
class DynamicWorkflowOrchestrator:
    def __init__(self, llm):
        self.llm = llm
        
    def plan_next_state(self, current_state: str, analysis_state: AnalysisState) -> str:
        """LLM decides next state based on current progress"""
        
        decision_template = """
        You are managing a vessel analysis workflow. Based on current progress, decide the next state.

        Current State: {current_state}
        Analysis Progress: {progress_summary}
        
        Available States:
        - fetch_tracks: Get vessel data from Elasticsearch
        - assess_vessels: Analyze which vessel(s) to research  
        - intelligent_research: Web research with MCP browser
        - evaluate_information: Check if we have enough data
        - write_report: Generate final report
        - quality_review: Validate report completeness
        
        Termination States:
        - END: Analysis complete
        - RETRY: Restart with different approach
        
        Decision Criteria:
        - Information sufficiency
        - User objective fulfillment  
        - Resource efficiency
        - Error handling
        
        Respond with JSON:
        {{
            "next_state": "state_name",
            "reasoning": "why this state is needed",
            "parameters": {{"any": "state-specific params"}},
            "max_iterations": int,
            "fallback_state": "if this state fails"
        }}
        """
        
        # Build progress summary
        progress = self._summarize_progress(analysis_state)
        
        response = self.llm.invoke([
            ("system", "You are a workflow orchestration expert."),
            ("user", decision_template.format(
                current_state=current_state,
                progress_summary=progress
            ))
        ])
        
        return self._parse_decision(response.content)
```

### 3. Intelligent Information Assessment  

```python
class InformationQualityAssessor:
    def __init__(self, llm):
        self.llm = llm
        
    def assess_research_sufficiency(self, 
                                  objective: str, 
                                  collected_data: List[WebSearchResult],
                                  vessel_data: VesselData) -> AssessmentResult:
        """LLM evaluates if we have enough information for the report"""
        
        assessment_template = """
        Evaluate research sufficiency for this vessel analysis objective.
        
        Original Objective: {objective}
        
        Vessel Data Available:
        - Track Points: {track_count}
        - Distance: {distance} miles
        - Specifications: {specs_available}
        
        Web Research Results:
        {research_summary}
        
        Assessment Criteria:
        1. Can we answer the user's main question?
        2. Do we have enough context for the vessel's long journey?
        3. Are there critical information gaps?
        4. Would additional research significantly improve the report?
        
        Respond with JSON:
        {{
            "sufficiency_score": 0.0-1.0,
            "decision": "sufficient|need_more_research|change_approach",
            "missing_information": ["list of gaps"],
            "next_research_focus": "if more research needed",
            "confidence": 0.0-1.0
        }}
        """
        
        research_summary = self._summarize_research(collected_data)
        specs_available = bool(vessel_data.length or vessel_data.vessel_type)
        
        response = self.llm.invoke([
            ("system", "You are a research quality assessment expert."),
            ("user", assessment_template.format(
                objective=objective,
                track_count=len(vessel_data.track_points),
                distance=vessel_data.total_distance_miles,
                specs_available=specs_available,
                research_summary=research_summary
            ))
        ])
        
        return self._parse_assessment(response.content)
```

### 4. Adaptive Browser Navigation

```python
class IntelligentBrowserNavigator:
    def __init__(self, llm, mcp_client):
        self.llm = llm
        self.mcp_client = mcp_client
        
    def select_search_result(self, 
                           search_results: List[Dict], 
                           research_focus: List[str]) -> Dict:
        """LLM selects the most promising search result"""
        
        selection_template = """
        Select the best search result for vessel research.
        
        Research Focus: {focus_areas}
        
        Available Results:
        {results_list}
        
        Selection Criteria:
        - Relevance to vessel specifications
        - Likelihood of operational context
        - Authority of source
        - Content depth indicators
        
        Respond with JSON:
        {{
            "selected_index": int,
            "reasoning": "why this result",
            "expected_information": ["what we expect to find"],
            "backup_selections": [int, int]
        }}
        """
        
        results_summary = self._format_results(search_results)
        
        response = self.llm.invoke([
            ("system", "You are a research source selection expert."),
            ("user", selection_template.format(
                focus_areas=research_focus,
                results_list=results_summary
            ))
        ])
        
        return self._parse_selection(response.content)
    
    def evaluate_page_content(self, content: str, research_goals: List[str]) -> ContentEvaluation:
        """LLM evaluates if current page meets research needs"""
        
        evaluation_template = """
        Evaluate this webpage content for vessel research value.
        
        Research Goals: {goals}
        
        Page Content Preview:
        {content_preview}
        
        Evaluation Criteria:
        1. Contains vessel specifications?
        2. Explains operational context?
        3. Provides route/journey details?
        4. Includes historical information?
        5. Has visual content (images)?
        
        Respond with JSON:
        {{
            "value_score": 0.0-1.0,
            "information_extracted": {{"key": "value"}},
            "continue_here": true/false,
            "missing_from_goals": ["unfulfilled research goals"],
            "recommendation": "extract_and_continue|need_different_source|sufficient"
        }}
        """
        
        content_preview = content[:1000] if len(content) > 1000 else content
        
        response = self.llm.invoke([
            ("system", "You are a content evaluation specialist."),
            ("user", evaluation_template.format(
                goals=research_goals,
                content_preview=content_preview
            ))
        ])
        
        return self._parse_evaluation(response.content)
```

## Implementation Integration Points

### Modified LangGraph Workflow

```python
def _build_dynamic_workflow(self) -> StateGraph:
    """Build LLM-driven dynamic workflow"""
    workflow = StateGraph(AnalysisState)
    
    # Core states with LLM decision points
    workflow.add_node("parse_and_plan", self.llm_parse_and_plan)
    workflow.add_node("fetch_tracks", self.fetch_tracks_node)
    workflow.add_node("assess_vessels", self.llm_assess_vessels) 
    workflow.add_node("intelligent_research", self.llm_driven_research)
    workflow.add_node("evaluate_information", self.llm_evaluate_info)
    workflow.add_node("write_report", self.write_report_node)
    workflow.add_node("quality_review", self.llm_quality_review)
    
    # Entry point
    workflow.set_entry_point("parse_and_plan")
    
    # Dynamic conditional edges
    workflow.add_conditional_edges(
        "parse_and_plan",
        self.llm_plan_next_state,
        {
            "fetch_tracks": "fetch_tracks",
            "direct_research": "intelligent_research"  # if user has specific vessel
        }
    )
    
    workflow.add_conditional_edges(
        "evaluate_information", 
        self.llm_assess_sufficiency,
        {
            "sufficient": "write_report",
            "need_more_research": "intelligent_research",
            "different_vessel": "assess_vessels",
            "end": END
        }
    )
    
    return workflow
```

## Success Metrics

1. **Prompt Understanding**: LLM correctly interprets 95%+ of user objectives
2. **Adaptive Navigation**: Finds relevant information with 50% fewer page visits
3. **Quality Assessment**: Accurately determines information sufficiency 90%+ of the time  
4. **Workflow Efficiency**: Completes analyses 30% faster while maintaining quality

This design transforms the vessel analysis system from a hardcoded pipeline into a truly intelligent, adaptive agent that can understand user intent and dynamically plan its research strategy.
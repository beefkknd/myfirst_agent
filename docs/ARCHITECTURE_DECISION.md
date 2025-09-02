# Architecture Decision: LLM-Driven Dynamic Workflow

## Decision Summary
**Date**: 2025-09-01  
**Status**: Approved  
**Decision**: Transition from hardcoded sequential workflow to LLM-driven dynamic task planning and execution

## Problem Statement

### Current Issues with Hardcoded Approach
1. **LLM Underutilization**: The Ollama Qwen3:8b model is initialized but never used for intelligent decision-making
   - `parse_prompt_node()` hardcodes default prompt instead of parsing user requirements
   - No LLM involvement in workflow orchestration or task planning

2. **Rigid Browser Navigation**: MCP Chrome bridge uses fixed search patterns
   - Hardcoded element selection logic (`tools.py:142-160`)
   - Visits multiple pages (3 max) without intelligent content assessment
   - No LLM evaluation of page relevance or information sufficiency

3. **Sequential-Only Workflow**: Linear state transitions without decision points
   - No ability to revisit states based on quality assessment
   - Cannot adapt workflow based on intermediate results
   - Missing feedback loops for information gathering

## Proposed Solution: LLM-Driven Dynamic Workflow

### Core Principles
1. **LLM as Workflow Orchestrator**: Parse user prompts and dynamically plan task sequences
2. **Intelligent Browser Navigation**: LLM analyzes search results and selects optimal pages
3. **Cyclic Workflow with Decision Points**: Allow revisiting states based on LLM assessment
4. **Quality-Driven Information Gathering**: Continue research only if information is insufficient

### Key Components

#### 1. LLM-Driven Prompt Parsing
```python
def parse_prompt_node(self, state: AnalysisState) -> AnalysisState:
    """LLM extracts user requirements and plans task sequence."""
    prompt_parsing_template = """
    Analyze this vessel analysis request and extract:
    1. User objective and intent
    2. Vessel selection criteria  
    3. Research scope and priorities
    4. Report requirements
    5. Recommended task sequence
    
    Prompt: {user_prompt}
    """
    # Use self.llm to parse and plan
```

#### 2. Intelligent Browser Navigation
```python
def intelligent_web_research(self, query: str, state: AnalysisState) -> List[WebSearchResult]:
    """LLM-driven browser navigation with content assessment."""
    # Step 1: LLM analyzes search results and selects best candidate
    # Step 2: Navigate to selected page and extract content
    # Step 3: LLM evaluates information sufficiency
    # Step 4: Only visit additional pages if needed
```

#### 3. Cyclic Workflow Architecture
```python
# Dynamic state transitions based on LLM decisions
workflow.add_conditional_edges(
    "internet_search",
    self.llm_assess_information_quality,
    {
        "sufficient": "write_report",
        "need_more_research": "internet_search", 
        "change_vessel": "fetch_tracks"
    }
)
```

### Workflow State Machine

**Dynamic States**:
- `parse_and_plan`: LLM unpacks prompt → plans task sequence
- `fetch_tracks`: Query Elasticsearch based on LLM-parsed criteria
- `assess_vessels`: LLM selects most interesting vessel for research
- `intelligent_research`: LLM-driven browser navigation
- `evaluate_information`: LLM assesses information sufficiency
- `write_report`: Generate report with LLM-analyzed content
- `quality_review`: LLM validates report completeness

**Decision Points**:
- Information sufficiency assessment
- Vessel selection optimization  
- Research scope adjustment
- Report completeness validation

### Implementation Strategy

#### Phase 1: LLM Prompt Parsing
- Replace hardcoded `AnalysisPrompt` with LLM-parsed user requirements
- Implement structured LLM output parsing using Pydantic models
- Add task sequence planning based on user intent

#### Phase 2: Intelligent Browser Navigation
- LLM-driven search result analysis and selection
- Content quality assessment before proceeding
- Focus on single high-quality source rather than multiple pages

#### Phase 3: Cyclic Workflow Implementation
- Add conditional edges with LLM decision functions
- Implement state revisiting logic
- Add termination conditions based on information quality

## Expected Benefits

1. **True AI-Driven Analysis**: LLM actively participates in planning and decision-making
2. **Adaptive Information Gathering**: Quality-driven research instead of fixed page limits
3. **Better Resource Utilization**: Focus effort on most relevant sources
4. **Flexible Workflow**: Adapt to different analysis types and user requirements
5. **Improved Results**: Higher quality reports through intelligent content curation

## Risks and Mitigations

**Risk**: LLM decision-making may be inconsistent
**Mitigation**: Implement structured prompts with validation schemas

**Risk**: Cyclic workflow may create infinite loops  
**Mitigation**: Add maximum iteration limits and termination conditions

**Risk**: Increased LLM API costs
**Mitigation**: Use local Ollama model and optimize prompt efficiency

## Success Metrics

- **Prompt Parsing Accuracy**: LLM correctly interprets 90%+ of user requirements
- **Research Efficiency**: Achieve same information quality with fewer page visits
- **Workflow Adaptability**: Handle diverse analysis types without code changes
- **Report Quality**: Improved relevance and completeness scores

## Implementation Timeline

- **Week 1**: Implement LLM prompt parsing and task planning
- **Week 2**: Develop intelligent browser navigation
- **Week 3**: Convert to cyclic workflow with decision points
- **Week 4**: Testing and optimization

---
*This decision enables the vessel analysis system to leverage its AI capabilities fully, transforming from a hardcoded pipeline into a truly intelligent analysis agent.*
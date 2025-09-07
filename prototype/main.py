import datetime
from typing import List, TypedDict

from dotenv import load_dotenv

load_dotenv()

from duckduckgo_search import DDGS
from elasticsearch import Elasticsearch
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

# --- Elasticsearch Tool ---
@tool
def search_vessel_data(query: str) -> List[dict]:
    """Searches the vessel_index for vessel data."""
    es = Elasticsearch(["http://localhost:9200"])
    today = datetime.date.today().strftime("%Y-%m-%d")
    # It's a demo, so we just search for today's data
    response = es.search(
        index="vessel_index",
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {"VesselName": query}},
                        {
                            "range": {
                                "BaseDateTime": {
                                    "gte": f"{today}T00:00:00",
                                    "lte": f"{today}T23:59:59",
                                }
                            }
                        },
                    ]
                }
            }
        },
    )
    return [hit["_source"] for hit in response["hits"]["hits"]]


# --- Browser Tool ---
@tool
def find_vessel_image(vessel_name: str) -> str:
    """Finds an image of a vessel using a web search."""
    with DDGS() as ddgs:
        for r in ddgs.images(f"{vessel_name} photo", max_results=1):
            return r["image"]
    return "No image found."


# --- Agent State ---
class AgentState(TypedDict):
    messages: List[BaseMessage]


# --- Agent --- #
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
tools = [search_vessel_data, find_vessel_image]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)


def agent(state: AgentState):
    """Invokes the agent to generate a response."""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": messages + [response]}

def should_continue(state: AgentState):
    """Determines whether to continue the workflow."""
    if not isinstance(state["messages"][-1], AIMessage):
        return "continue"
    if not state["messages"][-1].tool_calls:
        return "end"
    return "continue"


# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("action", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)
workflow.add_edge("action", "agent")
app = workflow.compile()


# --- Main Execution ---
if __name__ == "__main__":
    inputs = {
        "messages": [HumanMessage(content="Generate a report for vessels with the name 'EVER GIVEN'")],
    }
    for output in app.stream(inputs):
        for key, value in output.items():
            print(f"Output from node '{key}':")
            print("---")
            print(value)
        print("\n---\n")
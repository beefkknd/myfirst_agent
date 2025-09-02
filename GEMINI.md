Task: Build a LangChain/LangGraph Agent Prototype for Vessel Report Generation
You are an expert AI developer specializing in building agentic systems using LangChain and LangGraph. Your goal is to create a complete, working Python prototype for an AI agent that follows a specific use case involving vessel data. The agent must use the Google Gemini model as its underlying LLM. It will integrate custom tools: one for querying an Elasticsearch index (for vessel data) and a browser tool (for fetching vessel images from the web). The agent should be built using LangGraph for stateful multi-step workflows.
Key Requirements

Framework: Use LangChain for tool integration and LangGraph for defining the agent's graph-based workflow (e.g., nodes for planning, tool execution, and report generation).
LLM: Integrate Google Gemini (use langchain_google_genai library, specifically the ChatGoogleGenerativeAI model). Assume the user has a Google API key set as an environment variable GOOGLE_API_KEY.
Tools:

Elasticsearch Tool: A tool to query an Elasticsearch index for today's vessel data. Assume a local or cloud Elasticsearch instance at http://localhost:9200 with an index named vessel_index. The tool should take a query (e.g., "today's vessels") and return a list of vessel names or details (e.g., in JSON format). Use elasticsearch Python client library.
Browser Tool: A tool to browse the web and find an image/photo of a specific vessel. Use a simple web search or browsing library like duckduckgo-search or beautifulsoup4 to search for "vessel_name photo" and extract the first image URL. Avoid full browser automation if possible for simplicity (e.g., no Playwright/Selenium unless necessary).


Use Case / Workflow:

The agent starts by querying the Elasticsearch tool for "today's vessel index" (filter by current date).
It selects one or more vessels from the results (e.g., the first one or based on criteria).
For each selected vessel, it uses the browser tool to search for and retrieve an image URL (e.g., via web search).
Combine the vessel data (from Elasticsearch) and image URL into a simple report (e.g., Markdown format with vessel details and embedded image).
The agent should handle the flow reactively: plan steps, execute tools, and decide when to end (e.g., using a conditional edge in LangGraph).


Input/Output: The agent takes a user query like "Generate report for today's vessels." and outputs the final report.
Dependencies: List all required pip-installable packages (e.g., langchain, langgraph, langchain_google_genai, elasticsearch, duckduckgo-search, beautifulsoup4, requests).
Error Handling: Include basic error handling for tool failures (e.g., retry or fallback).
Best Practices: Make the code modular, commented, and runnable as a standalone script. Use typing hints where appropriate. Assume today's date can be fetched via datetime.date.today().
Testing: Include a sample execution at the end of the script to test the agent with a dummy query.

Output Format

Provide the complete Python code as a single script.
Do not include any explanations outside the code; embed comments in the code for clarity.
If assumptions are needed (e.g., Elasticsearch setup), note them in comments.

import argparse
import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from models import AnalysisPrompt, VesselCriteria, WebResearchConfig, ReportConfig, PromptObjective
from report_generator import VesselReportGenerator
from tools import search_vessels_by_distance, web_research_vessel, download_vessel_image

load_dotenv()

class VesselAnalysisAgent:
    def __init__(self, model_type: str = "ollama"):
        self.model_type = model_type
        self.report_generator = VesselReportGenerator()
        
        # Initialize LLM
        if model_type.lower() == "ollama":
            self.llm = ChatOllama(model="qwen2.5:7b", temperature=0.1)
        else:  # fallback to ollama
            self.llm = ChatOllama(model="qwen2.5:7b", temperature=0.1)
        
        # Tools
        self.tools = [search_vessels_by_distance, web_research_vessel, download_vessel_image]
        
        # Create agent with system prompt
        system_prompt = """You are a vessel analysis agent that helps analyze maritime vessel tracking data.

Your workflow should be:
1. Search for vessels with long tracks using search_vessels_by_distance tool
2. Research the top vessels using web_research_vessel tool  
3. Download vessel images using download_vessel_image tool
4. Provide a summary of findings

Always be thorough in your analysis and provide specific details about vessel movements and characteristics."""

        # Create the React agent
        self.agent = create_react_agent(self.llm, self.tools, state_modifier=system_prompt)
        
    def run_analysis(self, prompt_file: str = None) -> str:
        """Run the complete vessel analysis."""
        print("🚢 Starting Vessel Analysis Agent (New LangGraph Approach)")
        print("=" * 60)
        
        # Create analysis prompt
        user_prompt = """Please analyze vessel tracking data with these requirements:

1. Find vessels that have traveled at least 100 miles
2. Focus on the top 5 vessels by distance
3. Research the top vessel online to get more information
4. Download any vessel images you find
5. Provide a detailed summary of your findings

Please be methodical and explain each step as you work through the analysis."""
        
        print("📋 Starting analysis with new React agent...")
        
        try:
            # Run the agent
            result = self.agent.invoke({
                "messages": [HumanMessage(content=user_prompt)]
            })
            
            print("✅ Agent execution completed")
            print("\n" + "=" * 60)
            print("🎉 ANALYSIS COMPLETE!")
            
            # Print the final result
            if result and "messages" in result:
                final_message = result["messages"][-1]
                print("\n📊 Final Analysis:")
                print(final_message.content)
                
                # Try to generate report if we have vessel data
                return self._generate_report_from_result(result)
            else:
                print("❌ No result returned from agent")
                return None
                
        except Exception as e:
            print(f"❌ Agent execution error: {e}")
            return None
    
    def _generate_report_from_result(self, result) -> str:
        """Extract vessel data from agent result and generate report."""
        try:
            # This is a simplified approach - in practice you'd need to
            # extract structured data from the agent's tool calls
            print("📝 Generating HTML report...")
            
            # For now, create a simple HTML report with the agent's output
            report_dir = "reports"
            os.makedirs(report_dir, exist_ok=True)
            
            report_path = os.path.join(report_dir, "vessel_analysis_report.html")
            
            final_message = result["messages"][-1] if result.get("messages") else None
            content = final_message.content if final_message else "No analysis results"
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Vessel Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        .content {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .timestamp {{ color: #7f8c8d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>🚢 Vessel Analysis Report</h1>
    <div class="timestamp">Generated on: {os.popen('date').read().strip()}</div>
    <div class="content">
        <pre>{content}</pre>
    </div>
</body>
</html>
"""
            
            with open(report_path, 'w') as f:
                f.write(html_content)
            
            print(f"✅ Report saved to: {report_path}")
            return report_path
            
        except Exception as e:
            print(f"❌ Report generation error: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description="Vessel Analysis Agent (New LangGraph)")
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
        print(f"🌐 Open in browser: file://{os.path.abspath(report_path)}")
    else:
        print("\n❌ Analysis failed. Check the logs above for details.")

if __name__ == "__main__":
    main()
import vertexai
from google.adk.agents import LlmAgent
from vertexai.preview import agent_engines

vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")

# 1. Define the 'Shell' Agent
# We don't add ServiceNow tools here; we add them at runtime.
base_agent = LlmAgent(
    name="SecOps-Dynamic-Agent",
    model="gemini-2.0-flash",
    instruction="""
    You are a SecOps assistant. You will be provided with tools at runtime. 
    Always check your available tools to answer user questions about tickets or systems.
    If you use a tool, explain briefly what you found.
    """
)

# 2. Deploy to Vertex AI Agent Engine
remote_agent = agent_engines.AgentEngine.create(
    agent=base_agent,
    requirements=["google-adk", "google-cloud-aiplatform"]
)

print(f"Agent Deployed! Resource Name: {remote_agent.resource_name}")
# Save this ID for Part 2
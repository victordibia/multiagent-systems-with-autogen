# uv tool install mcp-server-fetch
# verify it in path by running uv tool update-shell
import asyncio
from pathlib import Path
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console

async def main() -> None:
    # Setup server params for local filesystem access
    fetch_mcp_server = StdioServerParams(command="uvx", args=["mcp-server-fetch"])
    tools = await mcp_server_tools(fetch_mcp_server)

    # Create an agent that can use the fetch tool.
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    agent = AssistantAgent(name="fetcher", model_client=model_client, tools=tools, reflect_on_tool_use=True)  # type: ignore

    print(agent.dump_component())

    # The agent can now use any of the filesystem tools
    await Console(agent.run_stream(task="Summarize the content of https://newsletter.victordibia.com/p/you-have-ai-fatigue-thats-why-you", cancellation_token=CancellationToken()))
    
if __name__ == "__main__":
    asyncio.run(main())
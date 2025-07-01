# Combined MCP Server and Client Example
# This file contains both server and client in one file for easy testing and demonstration.
# 
# NOTE: In production environments, you should separate the server and client:
# - See server.py for a standalone MCP server implementation
# - See client.py for a standalone MCP client implementation  
# - See app.py for a production host application that connects to a remote server 

import asyncio
import json
import os
from openai import AsyncOpenAI
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session
import requests


def create_techcrunch_server() -> FastMCP:
    """Create a FastMCP server with TechCrunch news tools."""
    mcp = FastMCP("TechCrunch News Server")

    @mcp.tool(title="Fetch from TechCrunch")
    def fetch_from_techcrunch(category: str = "latest") -> str:
        """Fetch the latest news from TechCrunch for a given category."""
        allowed = {"ai", "startup", "security", "venture", "latest"}
        cat = category.lower()
        if cat not in allowed:
            cat = "latest"
        url = f"https://techcrunch.com/tag/{cat}/" if cat != "latest" else "https://techcrunch.com/"
        try:
            response = requests.get(url)
            if response.ok:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, "html.parser") 
                    text = soup.get_text(separator=' ', strip=True)
                    return text[:1000] + ("..." if len(text) > 1000 else "")
                except ImportError:
                    # If bs4 is not installed, return raw HTML (truncated)
                    return response.text[:1000] + ("..." if len(response.text) > 1000 else "")
            return "Failed to fetch news."
        except Exception as e:
            print(f"Error fetching news: {str(e)}")
            return f"Error fetching news: {str(e)}"

    return mcp


def convert_mcp_tools_to_openai_format(tools):
    """Convert MCP tools to OpenAI function calling format"""
    openai_tools = []
    for tool in tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # Add parameters if they exist in the tool schema
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            schema = tool.inputSchema
            if 'properties' in schema:
                openai_tool["function"]["parameters"]["properties"] = schema["properties"]
            if 'required' in schema:
                openai_tool["function"]["parameters"]["required"] = schema["required"]
        
        openai_tools.append(openai_tool)
    
    return openai_tools


async def handle_user_request(session, openai_client, tools, user_input: str):
    """Process user request using OpenAI with function calling"""
    try:
        openai_tools = convert_mcp_tools_to_openai_format(tools)
        
        # Call OpenAI with the user's message and available tools
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that can fetch news from TechCrunch. Use the available tools to help answer user questions."},
                {"role": "user", "content": user_input}
            ],
            tools=openai_tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # Check if the model wants to call a function
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"🔧 Calling tool: {function_name} with args: {function_args}")
            
            # Call the MCP tool
            result = await session.call_tool(function_name, arguments=function_args) 
            
            # Get final response from OpenAI including the tool result
            final_response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that can fetch news from TechCrunch."},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                    {"role": "tool", "tool_call_id": tool_call.id, "content": str(result.content)}
                ]
            )
            
            return final_response.choices[0].message.content
        else:
            return message.content
            
    except Exception as e:
        return f"Error processing request: {str(e)}"


async def run_combined_app():
    """Main application with combined server and client"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY environment variable")
        return

    import sys
    user_input = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "What is the latest news on AI?"
    openai_client = AsyncOpenAI()
    mcp_server = create_techcrunch_server()
    async with create_connected_server_and_client_session(mcp_server._mcp_server) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        print(f"Task: {user_input}")
        response = await handle_user_request(session, openai_client, tools, user_input)
        print(response)


if __name__ == "__main__":
    asyncio.run(run_combined_app())

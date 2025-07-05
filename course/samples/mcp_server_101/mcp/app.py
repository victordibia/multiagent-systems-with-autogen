# host app # to the client code, which uses the MCP server to fetch news from TechCrunch using OpenAI's function calling capabilities. 
# see server.py and client.py for independent server and client implementations.
# !! note: this requires the MCP server to be running and the OpenAI API key to be set in the environment. 

import asyncio
import json
import os
from openai import AsyncOpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import os
host = os.environ.get("MCP_SERVER_HOST", "localhost")
port = os.environ.get("MCP_SERVER_PORT", "8011")
server_url = os.getenv("MCP_SERVER_URL", f"http://{host}:{port}/mcp")
 
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


async def run_app():
    """Main application with combined server and client"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY environment variable")
        return

    import sys
    user_input = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "What is the latest news on AI?"
    
    openai_client = AsyncOpenAI()
    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            tools = (await session.list_tools()).tools
            print(f"Task: {user_input}")
            response = await handle_user_request(session, openai_client, tools, user_input)
            print(response)


if __name__ == "__main__":
    asyncio.run(run_app())

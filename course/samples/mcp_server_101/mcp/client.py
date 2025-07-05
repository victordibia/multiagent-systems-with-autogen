# client.py - HTTP version
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import asyncio

async def run_client():
    # Connect to the HTTP MCP server using configurable host and port
    import os
    host = os.environ.get("MCP_SERVER_HOST", "localhost")
    port = os.environ.get("MCP_SERVER_PORT", "8011")
    server_url = os.getenv("MCP_SERVER_URL", f"http://{host}:{port}/mcp")

    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # List available tools
            tools_response = await session.list_tools()
            print("Available tools:")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")
            
            # Call a tool
            result = await session.call_tool(
                "fetch_from_techcrunch", 
                arguments={"category": "ai"}
            )
            print(f"Tool result: {result.content}")

if __name__ == "__main__":
    asyncio.run(run_client())

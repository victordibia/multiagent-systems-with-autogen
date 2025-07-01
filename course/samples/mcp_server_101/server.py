# server.py
import os
from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("TechCrunch News Server", host=os.environ.get("MCP_SERVER_HOST", "localhost"), port=int(os.environ.get("MCP_SERVER_PORT", 8011)))

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
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string if soup.title else "No title found"
            return f"TechCrunch ({cat}) Page Title: {title}"
        return "Failed to fetch news."
    except Exception as e:
        return f"Error fetching news: {str(e)}"

if __name__ == "__main__":
    # Use streamable HTTP transport for remote scenarios
    host = os.environ.get("MCP_SERVER_HOST", "localhost")
    port = int(os.environ.get("MCP_SERVER_PORT", 8011))
    print(f"🚀 Starting MCP Server with streamable HTTP transport")
    print(f"📡 Server configured for {host}:{port}")
    print(f"🔗 Client connection URL: http://{host}:{port}/sse")
    mcp.run(transport="streamable-http")

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
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=' ', strip=True) 
                return text  + ("..." if len(text) > 1000 else "")
            except ImportError:
                return response.text[:1000] + ("..." if len(response.text) > 1000 else "")
        return "Failed to fetch news."
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return f"Error fetching news: {str(e)}"


@mcp.tool(title="dummy too")
def dummy_tool() -> str:
    """A dummy tool that does nothing."""
    return "This is a dummy tool response."


if __name__ == "__main__":  
    mcp.run(transport="streamable-http")

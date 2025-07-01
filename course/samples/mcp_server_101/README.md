# MCP Tutorial: Building Your First Client and Server

This folder contains the complete code examples from the MCP tutorial article.

## Files

- `app.py` - Complete MCP application with combined server, client, and OpenAI integration. Takes a task from the command line or defaults to "What is the latest news on AI?" and prints a single result.
- `requirements.txt` - Python dependencies

**Note**: This example combines both MCP server and client in a single file for simplicity and easy testing. In production environments, you would typically separate these into distinct services.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

## Running the Application

You can run the app with a custom task or let it use the default:

```bash
# With a custom task
python app.py "Show me startup news from TechCrunch"

# Or with no arguments (defaults to: What is the latest news on AI?)
python app.py
```

The app will print the result for the single task and exit. Perfect for learning, testing, and automation!

## Transport Configuration

This example uses **in-memory transport** for simplicity and easy testing:

- **Combined Approach**: Both server and client run in the same process
- **Benefits**: No network configuration needed, perfect for learning and development
- **Production Note**: For production deployments, consider separating server and client with HTTP transport

In production environments, you might want to:

- Run the server as a separate service with `mcp.run(transport="streamable-http")`
- Connect clients via HTTP/SSE for better scalability and separation of concerns

## Example Usage

The application accepts a task from the command line and returns a single result. If no task is provided, it defaults to:

    What is the latest news on AI?

You can also provide your own task:

    python app.py "Show me startup news from TechCrunch"
    python app.py "Any security news today?"
    python app.py "What's happening in venture capital?"

The application uses OpenAI's function calling to intelligently decide which MCP tool to use based on your request, fetches the appropriate news from TechCrunch, and returns the result.

## Architecture

```
Command Line Task → Host App (OpenAI LLM) → MCP Client (In-Memory) → MCP Server → TechCrunch API
```

The host application orchestrates the entire flow, using the LLM to determine when and how to call the MCP tools. The communication happens over in-memory transport within the same process, making it perfect for learning and development.

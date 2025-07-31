# Advanced MCP Server Implementation

This folder contains an advanced MCP server implementation demonstrating sophisticated features that go beyond simple request-response patterns.

## What's Included

This server showcases:

- **Interactive & Long-Running Tools**: Tools that can run for extended periods, request user input, and provide real-time progress updates
- **Resource Management**: Server-side resources with client subscription capabilities for real-time updates
- **Prompts**: Reusable LLM interaction templates with dynamic arguments
- **Session Resumption**: Full event store support for resuming interrupted operations

## Key Features Demonstrated

### Tools
- **Elicitation**: Tools that pause to request structured user input
- **Sampling**: Tools that request LLM assistance during execution
- **Progress Notifications**: Real-time status updates for long-running operations
- **Cancellation**: Graceful handling of interrupted tool calls
- **Annotations**: Metadata to help clients understand tool behavior

### Resources
- Server-side resource definition and management
- Client operations: list, read, and subscribe to resources
- Real-time notifications when resources change

### Advanced Capabilities
- Event store for session resumption
- Transport security settings
- Comprehensive error handling

## Blog Post

For a detailed walkthrough of these concepts and implementation details, see the accompanying blog post:

**[MCP For Software Engineers | Part 2: Interactive & Long-Running Tools](https://newsletter.victordibia.com/p/mcp-for-software-engineers-part-2)**

This post explains the theory behind these advanced MCP features and provides step-by-step implementation guidance.

## Running the Server

```bash
# Navigate to the advanced directory
cd mcp/advanced

# Start the server with event store support (default)
python -m server.server

# Start on a different port
python -m server.server --port 8007

# Start without event store (no resumption support)
python -m server.server --no-event-store
```

The server will be available at `http://127.0.0.1:8006/mcp` (or your specified port).

## Related

- [Part 1: Getting Started with MCP](https://newsletter.victordibia.com/p/mcp-for-software-engineers-part-1)
- [MCP Python SDK Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
#!/usr/bin/env python3
"""
Resumable MCP Server Implementation

This server provides full session resumption capabilities using an event store.
It supports long-running tasks that can be resumed after client disconnection.
"""

import argparse
import asyncio
import logging
import re
from turtle import st
from typing import Optional

import anyio
import uvicorn
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.routing import Mount
from pydantic import BaseModel, Field
from mcp.server import Server
from mcp.server.streamable_http import EventStore
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import (
    TextContent, Tool, SamplingMessage, Resource, Prompt, PromptArgument, 
    PromptMessage, GetPromptResult, ToolAnnotations
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

from .event_store import SimpleEventStore

logger = logging.getLogger(__name__)


                            
class PriceConfirmationSchema(BaseModel):
    confirm: bool = Field(description="Confirm the price for this trip")
    notes: str = Field(default="", description="Any additional notes about the price")
                            
class ResumableServer(Server):
    """Server implementation with long-running tools and notifications for resumption testing."""

    def __init__(self, name: str = "resumable_mcp_server"):
        super().__init__(name)
        logger.info(f"ResumableServer '{name}' initialized")

        @self.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools including resumable ones."""
            return [
                Tool(
                    name="travel_agent",
                    description="Book a travel trip with progress updates and price confirmation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "description": "Travel destination",
                                "default": "Paris"
                            }
                        }
                    },
                    annotations=ToolAnnotations(
                        title="Travel Booking Agent",
                        readOnlyHint=False,
                        destructiveHint=False,  # Creates bookings but doesn't destroy data
                        idempotentHint=False,   # Each booking is unique
                        openWorldHint=True      # Interacts with external booking systems
                    )
                ),
                Tool(
                    name="research_agent",
                    description="Research a topic with progress updates and interactive summaries",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Research topic",
                                "default": "AI trends"
                            }
                        }
                    },
                    annotations=ToolAnnotations(
                        title="Research Assistant",
                        readOnlyHint=True,      # Only reads and analyzes data
                        destructiveHint=False,  # Never modifies or deletes anything
                        idempotentHint=True,    # Same topic produces similar results
                        openWorldHint=True      # Searches external sources
                    )
                ),
                Tool(
                    name="long_running_agent",
                    description="A long-running task for testing resumption (50 steps, 2 seconds each)",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    },
                    annotations=ToolAnnotations(
                        title="Long-Running Task Processor",
                        readOnlyHint=False,     # Generates logs and status updates
                        destructiveHint=False,  # Safe processing task
                        idempotentHint=True,    # Can be safely resumed/restarted
                        openWorldHint=False     # Self-contained processing
                    )
                ),
            ]

        @self.call_tool()
        async def handle_call_tool(name: str, args: dict) -> list[TextContent]:
            """Handle tool execution with support for long-running tasks."""
            ctx = self.request_context
            logger.info(f"Tool called: {name} with args: {args}")

            if name == "travel_agent":
                destination = args.get("destination", "Paris")
                logger.info(f"Travel agent: destination={destination}")
                
                # Simple travel booking flow with progress updates
                steps = [
                    "Checking flights...",
                    "Finding available dates...", 
                    "Confirming prices...",
                    "Booking flight..."
                ]
                
                elicitation_result = None
                booking_cancelled = False
                
                for i, step in enumerate(steps):
                    await ctx.session.send_progress_notification(
                        progress_token=ctx.request_id,
                        progress=i * 25,
                        total=100,
                        message=step, 
                        related_request_id=str(ctx.request_id)   
                    )
                    
                    # Add elicitation request at step 3 (Confirming prices)
                    if i == 2:  # "Confirming prices..." step
                        try:
                            elicit_result = await ctx.session.elicit(
                                message=f"Please confirm the estimated price of $1200 for your trip to {destination}",
                                requestedSchema=PriceConfirmationSchema.model_json_schema(),
                                related_request_id=ctx.request_id,
                            )
                            
                            elicitation_result = elicit_result
                            
                            if elicit_result and elicit_result.action == "accept":
                                logger.info(f"User confirmed price: {elicit_result.content}")
                                # Continue with booking
                            elif elicit_result and elicit_result.action == "decline":
                                logger.info(f"User declined price confirmation: {elicit_result.content}")
                                booking_cancelled = True
                                # Stop the booking process
                                await ctx.session.send_progress_notification(
                                    progress_token=ctx.request_id,
                                    progress=100,
                                    total=100,
                                    message="Booking cancelled by user",
                                    related_request_id= str(ctx.request_id)
                                )
                                break
                            else:
                                logger.info("User cancelled elicitation")
                                booking_cancelled = True
                                await ctx.session.send_progress_notification(
                                    progress_token=ctx.request_id,
                                    progress=100,
                                    total=100,
                                    message="Booking cancelled"
                                )
                                break
                                
                        except Exception as e:
                            logger.info(f"Elicitation request failed (this is normal in tests): {e}")
                            # Continue with booking anyway for fallback
                    
                    if not booking_cancelled:
                        await anyio.sleep(5)  # Fixed 0.5 second delay between steps
                
                # Generate final result based on elicitation outcome
                if booking_cancelled:
                    if elicitation_result and hasattr(elicitation_result, 'content') and elicitation_result.content:
                        notes = elicitation_result.content.get('notes', 'No reason provided')
                        result_text = f"❌ Booking cancelled for trip to {destination}. Reason: {notes}"
                    else:
                        result_text = f"❌ Booking cancelled for trip to {destination}."
                else:
                    # Final progress update for successful booking
                    await ctx.session.send_progress_notification(
                        progress_token=ctx.request_id,
                        progress=100,
                        total=100,
                        message="Trip booked successfully"
                    )
                    
                    # Include confirmation details in success message
                    if elicitation_result and elicitation_result.action == "accept" and elicitation_result.content:
                        notes = elicitation_result.content.get('notes', 'No additional notes')
                        result_text = f"✅ Trip booked successfully to {destination}! Price confirmed with notes: '{notes}'"
                    else:
                        result_text = f"✅ Trip booked successfully to {destination}!"

                return [TextContent(type="text", text=result_text)]

            elif name == "research_agent":
                topic = args.get("topic", "AI trends")
                logger.info(f"Research agent: topic={topic}")
                
                # Simple research flow with progress updates
                steps = [
                    "Gathering sources...",
                    "Analyzing data...", 
                    "Summarizing findings...",
                    "Finalizing report..."
                ]
                
                sampling_summary = None
                
                for i, step in enumerate(steps):
                    await ctx.session.send_progress_notification(
                        progress_token=ctx.request_id,
                        progress=i * 25,
                        total=100,
                        message=step
                    )
                    
                    # Add sampling request at step 3 (Summarizing findings)
                    if i == 2:  # "Summarizing findings..." step
                        try:
                            sampling_result = await ctx.session.create_message(
                                messages=[
                                    SamplingMessage(
                                        role="user",
                                        content=TextContent(type="text", text=f"Please summarize the key findings for research on: {topic}")
                                    )
                                ],
                                max_tokens=100,
                                related_request_id=ctx.request_id,
                            )
                            
                            if sampling_result and sampling_result.content:
                                if sampling_result.content.type == "text":
                                    sampling_summary = sampling_result.content.text
                                    logger.info(f"Received sampling summary: {sampling_summary}")
                                    
                        except Exception as e:
                            logger.info(f"Sampling request failed (this is normal in tests): {e}")
                    
                    await anyio.sleep(5)  # Fixed 0.5 second delay between steps
                
                # Final progress update
                await ctx.session.send_progress_notification(
                    progress_token=ctx.request_id,
                    progress=100,
                    total=100,
                    message="Research completed successfully"
                )

                # Use sampling summary if available, otherwise default message
                if sampling_summary:
                    result_text = f"🔍 Research on '{topic}' completed successfully!\n\n📊 Key Findings (from user input): {sampling_summary}"
                else:
                    result_text = f"🔍 Research on '{topic}' completed successfully!"
                
                return [TextContent(type="text", text=result_text)]

            elif name == "long_running_agent":
                # Fixed values optimized for resumption testing
                steps = 50
                duration = 2.0
                logger.info(f"Long running agent: {steps} steps, {duration}s each")
                
                # Send initial log message
                await ctx.session.send_log_message(
                    level="info",
                    data="Long-running task started",
                    logger="long_running_agent",
                    related_request_id=ctx.request_id,
                )
                
                # Execute the long-running task
                for i in range(steps):
                    current_step = i + 1
                    # Use integer arithmetic to avoid floating point precision issues
                    progress_percent = (current_step * 100) // steps
                    
                    # Send log message for each step
                    await ctx.session.send_log_message(
                        level="info",
                        data=f"Processing step {current_step}/{steps} ({progress_percent}%)",
                        logger="long_running_agent",
                        related_request_id=ctx.request_id,
                    )
                    
                    # Wait for 2 seconds
                    await anyio.sleep(duration)
                
                # Send completion log message
                await ctx.session.send_log_message(
                    level="info",
                    data=f"Task completed successfully! Processed {steps} steps in {steps * duration:.0f} seconds.",
                    logger="long_running_agent",
                    related_request_id=ctx.request_id,
                )
                
                # Final completion message
                result_text = f"✅ Long-running task completed successfully! Processed {steps} steps in {steps * duration:.0f} seconds."
                return [TextContent(type="text", text=result_text)]

            else:
                raise ValueError(f"Unknown tool: {name}")

        @self.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List available resources including research data and logs."""
            return [
                Resource(
                    uri=AnyUrl("research://data/sources"),
                    name="Research Data Sources",
                    description="Collection of research sources and references",
                    mimeType="application/json"
                ),
                Resource(
                    uri=AnyUrl("travel://bookings/history"),
                    name="Travel Booking History", 
                    description="Historical travel booking records",
                    mimeType="application/json"
                ),
                Resource(
                    uri=AnyUrl("logs://server/activity"),
                    name="Server Activity Logs",
                    description="Real-time server activity and performance logs",
                    mimeType="text/plain"
                )
            ]

        @self.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
            """Read resource content based on URI."""
            uri_str = str(uri)
            
            if uri_str == "research://data/sources":
                # Mock research data
                research_data = {
                    "sources": [
                        {"title": "AI Trends 2024", "url": "https://example.com/ai-trends"},
                        {"title": "Machine Learning Advances", "url": "https://example.com/ml-advances"}
                    ],
                    "last_updated": "2024-01-15T10:30:00Z"
                }
                return [ReadResourceContents(
                    content=str(research_data).replace("'", '"'),
                    mime_type="application/json"
                )]
            
            elif uri_str == "travel://bookings/history":
                # Mock travel booking data
                booking_data = {
                    "bookings": [
                        {"destination": "Paris", "date": "2024-03-15", "status": "confirmed"},
                        {"destination": "Tokyo", "date": "2024-02-10", "status": "completed"}
                    ],
                    "total_bookings": 2
                }
                return [ReadResourceContents(
                    content=str(booking_data).replace("'", '"'),
                    mime_type="application/json"
                )]
            
            elif uri_str == "logs://server/activity":
                # Mock server logs
                log_content = """2024-01-15 10:30:00 - Server started successfully
2024-01-15 10:31:15 - Tool 'travel_agent' executed for destination: Paris
2024-01-15 10:32:30 - Tool 'research_agent' executed for topic: AI trends
2024-01-15 10:33:45 - Progress notification sent for request_id: req_123"""
                return [ReadResourceContents(
                    content=log_content,
                    mime_type="text/plain"
                )]
            
            else:
                raise ValueError(f"Unknown resource: {uri_str}")

        @self.list_prompts()
        async def handle_list_prompts() -> list[Prompt]:
            """List available prompt templates."""
            return [
                Prompt(
                    name="task_summary",
                    description="Generate a summary for any completed task",
                    arguments=[
                        PromptArgument(
                            name="task_name",
                            description="Name of the completed task",
                            required=True
                        ),
                        PromptArgument(
                            name="outcome",
                            description="The result or outcome of the task",
                            required=False
                        )
                    ]
                )
            ]

        @self.get_prompt()
        async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
            """Generate prompt content based on template name and arguments."""
            if name != "task_summary":
                raise ValueError(f"Unknown prompt: {name}")
            
            if arguments is None:
                arguments = {}
            
            task_name = arguments.get("task_name", "Unknown Task")
            outcome = arguments.get("outcome", "task completed successfully")
            
            prompt_text = f"""Please create a concise summary for the following completed task:

Task: {task_name}
Outcome: {outcome}

Please provide:
1. What was accomplished
2. Key results or deliverables
3. Any important observations or lessons learned

Keep the summary brief and professional."""
            
            return GetPromptResult(
                description=f"Task summary prompt for {task_name}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=prompt_text)
                    )
                ]
            )


def create_server_app(event_store: Optional[EventStore] = None) -> Starlette:
    """Create the Starlette application with resumable MCP server."""
    # Create server instance
    server = ResumableServer()

    # Create security settings
    security_settings = TransportSecuritySettings(
        allowed_hosts=["127.0.0.1:*", "localhost:*"],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*"]
    )

    # Create session manager with event store
    session_manager = StreamableHTTPSessionManager(
        app=server,
        event_store=event_store,
        json_response=False,  # Use SSE streams
        security_settings=security_settings,
    )

    # Create ASGI application
    app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=session_manager.handle_request),
        ],
        lifespan=lambda app: session_manager.run(),
    )

    return app


async def run_server(port: int = 8006, with_event_store: bool = True) -> None:
    """Run the resumable HTTP server."""
    # Create event store if requested
    event_store = SimpleEventStore() if with_event_store else None
    
    # Create application
    app = create_server_app(event_store)

    # Configure server
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        limit_concurrency=10,
        timeout_keep_alive=30,
        access_log=True,
    )

    logger.info(f"Starting Resumable HTTP MCP Server on http://127.0.0.1:{port}/mcp")
    if event_store:
        logger.info("Event store enabled - resumption supported")
    else:
        logger.info("Event store disabled - no resumption support")

    # Start the server
    server = uvicorn.Server(config=config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Resumable HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8006, help="Port to listen on (default: 8006)")
    parser.add_argument("--no-event-store", action="store_true", help="Disable event store (no resumption)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the server
    asyncio.run(run_server(
        port=args.port,
        with_event_store=not args.no_event_store
    ))


if __name__ == "__main__":
    main()

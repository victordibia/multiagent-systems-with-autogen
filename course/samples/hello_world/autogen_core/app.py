import asyncio
from dataclasses import dataclass
from typing import List, Optional

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from autogen_core.tool_agent import ToolAgent, tool_agent_caller_loop
from autogen_core.tools import FunctionTool, Tool, ToolSchema
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Message types for our agents to communicate


@dataclass
class Message:
    content: str

# Calculator function to be used as a tool


async def calculator(a: float, b: float, operator: str) -> str:
    """Perform basic arithmetic operations."""
    try:
        if operator == '+':
            return str(a + b)
        elif operator == '-':
            return str(a - b)
        elif operator == '*':
            return str(a * b)
        elif operator == '/':
            if b == 0:
                return 'Error: Division by zero'
            return str(a / b)
        else:
            return 'Error: Invalid operator. Please use +, -, *, or /'
    except Exception as e:
        return f'Error: {str(e)}'


class AssistantAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        tool_schema: List[ToolSchema],
        tool_agent_type: str,
        max_messages: Optional[int] = None
    ) -> None:
        super().__init__("An assistant agent with calculator capabilities")
        self._system_messages = [
            SystemMessage(content=(
                "You are a helpful AI assistant that can perform calculations. "
                "When calculations are needed, use the calculator tool. "
                "If you see 'TERMINATE', stop the conversation."
            ))
        ]
        self._model_client = model_client
        self._tool_schema = tool_schema
        self._tool_agent_id = AgentId(tool_agent_type, self.id.key)
        self._message_count = 0
        self._max_messages = max_messages

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> Optional[Message]:
        # Check for termination conditions
        if "TERMINATE" in message.content:
            return None

        if self._max_messages and self._message_count >= self._max_messages:
            return None

        self._message_count += 1

        # Create a session of messages
        session = [UserMessage(content=message.content, source="user")]

        # Run the tool caller loop to handle calculations
        messages = await tool_agent_caller_loop(
            self,
            tool_agent_id=self._tool_agent_id,
            model_client=self._model_client,
            input_messages=session,
            tool_schema=self._tool_schema,
            cancellation_token=ctx.cancellation_token,
        )

        # Return the final response
        assert isinstance(messages[-1].content, str)
        return Message(content=messages[-1].content)


async def main() -> None:
    # Create runtime
    runtime = SingleThreadedAgentRuntime()

    # Create the calculator tool
    calculator_tool = FunctionTool(
        calculator,
        description="A calculator that can perform basic arithmetic operations"
    )
    tools: List[Tool] = [calculator_tool]

    # Create model client
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-11-20")

    # Register the tool agent
    await ToolAgent.register(
        runtime,
        "calculator_tool_agent",
        lambda: ToolAgent("Calculator tool agent", tools)
    )

    # Register the assistant agent
    await AssistantAgent.register(
        runtime,
        "assistant",
        lambda: AssistantAgent(
            model_client=model_client,
            tool_schema=[tool.schema for tool in tools],
            tool_agent_type="calculator_tool_agent",
            max_messages=10
        )
    )

    # Start the runtime
    runtime.start()

    # Send the calculation request
    assistant_id = AgentId("assistant", "default")
    response = await runtime.send_message(
        Message("What is the result of 545.34567 * 34555.34"),
        assistant_id
    )

    if response:
        print(f"Response: {response.content}")

    # Stop the runtime
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())

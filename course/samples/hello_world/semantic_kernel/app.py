# pip install semantic-kernel httpx python-dotenv
import asyncio
from typing import Annotated
import httpx
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions import kernel_function
from dotenv import load_dotenv

load_dotenv()

# Define a calculator plugin for Semantic Kernel
class CalculatorPlugin:
    @kernel_function(
        description="Perform basic arithmetic operations."
    )
    def calculate(
        self,
        a: Annotated[float, "First number"],
        b: Annotated[float, "Second number"],
        operator: Annotated[str, "One of '+', '-', '*', '/'"],
    ) -> str:
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

def sk_agent() -> ChatCompletionAgent:
    agent = ChatCompletionAgent(
        service=OpenAIChatCompletion(ai_model_id="gpt-4o-mini"),
        name="calculator_agent",
        instructions="You are a helpful calculator assistant that can perform arithmetic operations using the calculator tool.",
        plugins=[CalculatorPlugin()],
    )
    return agent

async def main():
    agent = sk_agent()
    result = await agent.get_response(messages="What is the result of 545.34567 * 34555.34?")
    print("\nFinal result:", result)

if __name__ == "__main__":
    asyncio.run(main())

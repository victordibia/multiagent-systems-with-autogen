# pip install openai-agents
from agents import Agent, Runner, function_tool
import asyncio

# Define a calculator function to be used as a tool
@function_tool
async def calculator(a: float, b: float, operator: str) -> str:
    """
    Perform basic arithmetic operations.
    
    Args:
        a: First number
        b: Second number
        operator: The operation to perform (+, -, *, /)
    """
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

# Create a single assistant agent with the calculator tool
assistant = Agent(
    name="Calculator Assistant",
    instructions=(
        "You are a helpful AI assistant that can perform calculations. "
        "When calculations are needed, use the calculator tool. "
        "If you see 'TERMINATE', respond with a goodbye message."
    ),
    tools=[calculator]
)

async def main():
    # Run the agent with a calculation request
    result = await Runner.run(
        assistant, 
        "What is the result of 545.34567 * 34555.34?"
    )
    
    print(f"Result: {result.final_output}")

if __name__ == "__main__":
    # Ensure you have set the OPENAI_API_KEY environment variable
    # export OPENAI_API_KEY=sk-...
    asyncio.run(main())
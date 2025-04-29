# pip install pydantic-ai

import asyncio
from pydantic_ai import Agent, RunContext

# Define a calculator function to be used as a tool
def calculator(a: float, b: float, operator: str) -> str:
    """Perform basic arithmetic operations.
    
    Args:
        a: First number
        b: Second number
        operator: One of '+', '-', '*', '/'
        
    Returns:
        The result of the calculation as a string
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

# Create the agent
calculator_agent = Agent(
    # You can use various models: 'openai:gpt-4o', 'anthropic:claude-3-opus', etc.
    'openai:gpt-4o',
    # System prompt to define the agent's behavior
    system_prompt=(
        "You are a helpful calculator assistant that can perform arithmetic operations. "
        "When a calculation is needed, use the calculator tool. "
        "If you see 'TERMINATE', respond with a goodbye message."
    )
)

# Register the calculator tool with the agent
@calculator_agent.tool_plain
def calculator_tool(a: float, b: float, operator: str) -> str:
    """Perform basic arithmetic operations.
    
    Args:
        a: First number
        b: Second number
        operator: One of '+', '-', '*', '/'
        
    Returns:
        The result of the calculation
    """
    return calculator(a, b, operator)

async def main():
    # Run the agent asynchronously
    result = await calculator_agent.run("What is the result of 545.34567 * 34555.34?") 
    print("\nFinal result:", result.output) 
 
if __name__ == "__main__": 
    asyncio.run(main()) 
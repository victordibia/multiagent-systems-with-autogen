# pip install -U llama-index llama-index-llms-openai
import asyncio
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI


def calculator(a: float, b: float, operator: str) -> str:  
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


async def main():
    # Create the LLM client - using OpenAI's model
    llm = OpenAI(model="gpt-4o")
    
    # Create an agent with the calculator tool
    agent = FunctionAgent(
        tools=[calculator],
        llm=llm,
        system_prompt="You are a helpful assistant that can perform calculations.When calculations are needed, use the calculator tool"
    )
     
    response = await agent.run("What is the result of 545.34567 * 34555.34?") 
    print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
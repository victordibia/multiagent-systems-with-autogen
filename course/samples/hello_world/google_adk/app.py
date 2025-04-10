# pip install google-adk
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import asyncio

# Define a calculator function to be used as a tool
def calculator(a: float, b: float, operator: str) -> str:
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
    # App constants
    APP_NAME = "calculator_app"
    USER_ID = "test_user"
    SESSION_ID = "test_session"
    
    # Create a session service
    session_service = InMemorySessionService()
    session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    # Create an agent with the calculator tool
    calculator_agent = LlmAgent(
        model="gemini-2.0-flash-exp",  # Using Google's Gemini model
        name="calculator_agent",
        description="A helpful assistant that can perform calculations",
        instruction="""You are a helpful AI assistant that can perform calculations.
When calculations are needed, use the calculator tool.
If you see 'TERMINATE', respond with a goodbye message.""",
        tools=[calculator]
    )
    
    # Create a runner for the agent with the session service
    runner = Runner(
        agent=calculator_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # Create a properly formatted user message
    user_message = types.Content(
        role='user',
        parts=[types.Part(text="What is the result of 545.34567 * 34555.34?")]
    )
    
    # Run the agent with a calculation query (matching the exact query from the original example)
    print("Running calculation...")
    response = None
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response = event.content.parts[0].text
    
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
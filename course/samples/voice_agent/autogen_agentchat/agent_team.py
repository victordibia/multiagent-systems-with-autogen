"""
Agent team configuration for Chainlit application.
This module creates and configures the agent team that processes user requests.
"""
import yaml
import os
from typing import List, Optional, Callable, Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Sample tools - add more as needed
def calculator(a: float, b: float, operator: str) -> str:
    """
    A simple calculator tool that performs basic operations.
    
    Args:
        a: First number
        b: Second number
        operator: Operation to perform (+, -, *, /)
        
    Returns:
        Result of the operation as a string
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

def weather_lookup(location: str) -> str:
    """
    Simulated weather lookup tool.
    In a real application, this would call a weather API.
    
    Args:
        location: Location to get weather for
        
    Returns:
        Weather information as a string
    """
    # This is a stub - replace with actual API call
    return f"Weather information for {location}: Simulated weather data (replace with API call)"


# Advanced configuration with multiple agents
def create_agent_team(
    model_name: str = "gpt-4o-2024-11-20", 
) -> RoundRobinGroupChat:
    """
    Create a team with multiple specialized agents.
    
    Args:
        model_name: Name of the OpenAI model to use
        tools: List of tools to provide to the assistant
        
    Returns:
        Configured RoundRobinGroupChat with multiple agents
    """
    # Use default tools if none provided
    tools = [calculator, weather_lookup]
    
    # Create the model client
    model_client = OpenAIChatCompletionClient(model=model_name)
    
    # Define termination condition
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(max_messages=15)
    
    # Create specialßized agents
    assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="""You are a helpful voice assistant. You help coordinate 
        the efforts of specialized agents to address user requests.
        When you've completed a task, end with TERMINATE to indicate completion.
        """,
        model_client_stream=True,
        tools=tools,
    ) 
    
    # Create the team
    team = RoundRobinGroupChat(
        participants=[assistant],
        termination_condition=termination
    )
    
    return team
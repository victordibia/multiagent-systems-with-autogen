from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

# Define the calculator tool


@tool
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


# Set up tools and model
tools = [calculator]
tool_node = ToolNode(tools)
model = ChatOpenAI(
    model="gpt-4o-2024-11-20",
    temperature=0
).bind_tools(tools)

# Define the routing logic


def should_continue(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]

    # Check for termination condition
    if "TERMINATE" in last_message.content:
        return END

    # If the LLM makes a tool call, route to the "tools" node
    if last_message.tool_calls:
        return "tools"

    # If no tool calls and no termination, continue the conversation
    return END

# Define the model calling function


def call_model(state: MessagesState):
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}


# Create the graph
workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Set up graph structure
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
)
workflow.add_edge("tools", "agent")

# Initialize memory
checkpointer = MemorySaver()

# Compile the graph
app = workflow.compile(checkpointer=checkpointer)

# Example usage


def run_calculation(expression: str):
    final_state = app.invoke(
        {"messages": [HumanMessage(content=expression)]},
        config={"configurable": {"thread_id": 42}}
    )
    return final_state["messages"][-1].content


# Test the calculator
result = run_calculation("What is 545.34567 * 34555.34?")
print(result)

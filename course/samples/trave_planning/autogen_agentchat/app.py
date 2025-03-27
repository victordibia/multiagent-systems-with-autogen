import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogenstudio.gallery.tools import google_search_tool, fetch_webpage_tool 


async def main() -> None:
    # Initialize the model client
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    # Set up termination conditions
    termination = MaxMessageTermination(max_messages=30) | TextMentionTermination("TERMINATE")

    # Planner Agent
    planner_agent = AssistantAgent(
        name="planner_agent",
        description="A helpful assistant that can plan trips",
        model_client=model_client,
        tools=[google_search_tool, fetch_webpage_tool],
        reflect_on_tool_use=True,
        system_message="""You are a helpful assistant that can suggest a travel plan for a user based on their request.
        Your responsibilities include:
        1. Analyzing traveler requirements and preferences
        2. Researching destination information and attractions
        3. Creating logical travel routes and timing
        4. Suggesting appropriate accommodations
        5. Developing a comprehensive itinerary
        
        Present your plan in a structured format with clear sections for each day.
        End your planning with "INITIAL PLAN COMPLETE" when finished."""
    )

    # Local Agent
    local_agent = AssistantAgent(
        name="local_agent",
        description="A local assistant that can suggest local activities or places to visit",
        model_client=model_client,
        tools=[google_search_tool, fetch_webpage_tool],
        reflect_on_tool_use=True,
        system_message="""You are a helpful assistant that can suggest authentic and interesting local activities or places to visit for a user and can utilize any context information provided.
        Your responsibilities include:
        1. Recommending authentic local experiences
        2. Suggesting hidden gems not found in typical tourist guides
        3. Recommending local cuisine and dining experiences
        4. Providing cultural context and etiquette tips
        5. Suggesting seasonal or special local events
        
        Focus on experiences that provide genuine insight into local culture.
        End your recommendations with "LOCAL RECOMMENDATIONS COMPLETE" when finished."""
    )

    # Language Agent
    language_agent = AssistantAgent(
        name="language_agent",
        description="A helpful assistant that can provide language tips for a given destination",
        model_client=model_client,
        system_message="""You are a helpful assistant that can review travel plans, providing feedback on important/critical tips about how best to address language or communication challenges for the given destination. If the plan already includes language tips, you can mention that the plan is satisfactory, with rationale.
        Your responsibilities include:
        1. Providing essential phrases for travelers
        2. Explaining potential communication challenges
        3. Suggesting language apps or resources
        4. Offering pronunciation guides for key phrases
        5. Advising on non-verbal communication customs
        
        Focus on practical communication advice specific to the destination.
        End your language tips with "LANGUAGE TIPS COMPLETE" when finished."""
    )

    # Travel Summary Agent
    travel_summary_agent = AssistantAgent(
        name="travel_summary_agent",
        description="A helpful assistant that can summarize the travel plan",
        model_client=model_client,
        system_message="""You are a helpful assistant that can take in all of the suggestions and advice from the other agents and provide a detailed final travel plan. You must ensure that the final plan is integrated and complete. YOUR FINAL RESPONSE MUST BE THE COMPLETE PLAN. When the plan is complete and all perspectives are integrated, you can respond with TERMINATE.
        Your responsibilities include:
        1. Integrating all planning elements into a cohesive itinerary
        2. Ensuring all traveler preferences are addressed
        3. Incorporating local recommendations appropriately
        4. Including relevant language and communication tips
        5. Providing a comprehensive day-by-day schedule
        6. Adding practical information (transportation, costs, etc.)
        
        Present the final plan in a clean, professional format with clear sections.
        End with "TERMINATE" when the complete plan is finalized."""
    )

    # User Proxy
    user_proxy = UserProxyAgent(
        name="user_proxy",
        description="A traveler seeking travel planning assistance", 
    )

    # Create selector prompt
    selector_prompt = """You are coordinating a travel planning team. The following roles are available:
    {roles}

    Process flow:
    1. planner_agent develops initial travel plan based on user requirements
    2. local_agent enhances the plan with authentic local experiences
    3. language_agent adds language and communication tips
    4. travel_summary_agent creates the final comprehensive plan

    Important guidelines for selecting user_proxy:
    - Only involve user_proxy when critical feedback or clarification is needed
    - Situations requiring user input include:
      * Major decision points that significantly affect the travel experience
      * Resolving conflicting priorities or preferences
      * Clarifying ambiguous requirements
      * Confirming budget constraints for expensive recommendations
      * Final approval of the complete plan
    - Avoid unnecessary user involvement for minor details or standard planning elements
    - When in doubt, let the agents continue their work without interruption

    Select the next appropriate role based on:
    - Current stage in the process
    - Last speaker's output
    - Whether critical user input is genuinely needed
    - Completion status of current task

    Read the following conversation and select the next role from {participants}. Only return the role.

    {history}

    Read the above conversation. Then select the next role from {participants} to play. ONLY RETURN THE ROLE."""

    # Create the team
    team = SelectorGroupChat(
        participants=[planner_agent, local_agent, language_agent, travel_summary_agent, user_proxy],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True
    )

    # Example task
    task = """I'm planning a 10-day trip to Japan in April with my family (2 adults, 2 teenagers). We're interested in experiencing both traditional culture and modern attractions. We enjoy food experiences, light hiking, and interactive museums. Our budget is mid-range. We don't speak Japanese. Please help create a detailed travel plan.""" 

    await Console(team.run_stream(task=task))

if __name__ == "__main__":
    asyncio.run(main())
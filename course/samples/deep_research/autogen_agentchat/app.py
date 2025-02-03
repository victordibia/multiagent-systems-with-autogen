# create a virtual env e.g conda create -n autogen python=3.12
# pip install -U autogen-agentchat autogen-ext[openai,web-surfer] 
# playwright install 
# This snippet uses the Google Search API. You need to set your google search engine id and api key
# os.environ["GOOGLE_CSE_ID"] = "your_google_cse_id"
# os.environ["GOOGLE_API_KEY"] = "your_google_api_key"


import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import the google_search_tool from your implementation
from google_search import google_search_tool
from fetch_webpage import fetch_webpage_tool
 

async def main() -> None:
    # Initialize the model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        temperature=0.7,
    )

    # Create the Research Assistant agent
    research_assistant = AssistantAgent(
        name="research_assistant",
        description="A research assistant that performs web searches and analyzes information",
        model_client=model_client,
        tools=[google_search_tool, fetch_webpage_tool],
        system_message="""You are a research assistant focused on finding accurate information.
        Use the google_search tool to find relevant information.
        Break down complex queries into specific search terms.
        Always verify information across multiple sources when possible.
        When you find relevant information, explain why it's relevant and how it connects to the query. When you get feedback from the a verifier agent, use your tools to act on the feedback and make progress."""
    )

    # Create the Verifier agent
    verifier = AssistantAgent(
        name="verifier",
        description="A verification specialist who ensures research quality and completeness",
        model_client=model_client,
        system_message="""You are a research verification specialist.
        Your role is to:
        1. Verify that search queries are effective and suggest improvements if needed
        2. Explore drill downs where needed e.g, if the answer is likely in a link in the returned search results, suggest clicking on the link
        3. Suggest additional angles or perspectives to explore. Be judicious in suggesting new paths to avoid scope creep or wasting resources, if the task appears to be addressed and we can provide a report, do this and respond with "TERMINATE".
        4. Track progress toward answering the original question
        5. When the research is complete, provide a detailed summary in markdown format
        
        For incomplete research, end your message with "CONTINUE RESEARCH". 
        For complete research, end your message with APPROVED.
        
        Your responses should be structured as:
        - Progress Assessment
        - Gaps/Issues (if any)
        - Suggestions (if needed)
        - Next Steps or Final Summary"""
    )

    summary_agent = AssistantAgent(
        name="summary_agent",
        description="A summary agent that provides a detailed markdown summary of the research as a report to the user.",
        model_client=model_client,
        system_message="""You are a summary agent. Your role is to provide a detailed markdown summary of the research as a report to the user. Your report should have a reasonable title that matches the research question and should summarize the key details in the results found in natural an actionable manner. The main results/answer should be in the first paragraph.
        Your report should end with the word "TERMINATE" to signal the end of the conversation."""
    )

    # Set up termination conditions
    text_termination = TextMentionTermination("TERMINATE")
    max_messages = MaxMessageTermination(max_messages=30)
    termination = text_termination | max_messages

    # Create the selector prompt
    selector_prompt = """You are coordinating a research team by selecting the team member to speak/act next. The following team member roles are available:
    {roles}.
    The research_assistant performs searches and analyzes information.
    The verifier evaluates progress and ensures completeness.
    The summary_agent provides a detailed markdown summary of the research as a report to the user.

    Given the current context, select the most appropriate next speaker.
    The research_assistant should search and analyze.
    The verifier should evaluate progress and guide the research (select this role is there is a need to verify/evaluate progress). You should ONLY select the summary_agent role if the research is complete and it is time to generate a report.

    Base your selection on:
    1. Current stage of research
    2. Last speaker's findings or suggestions
    3. Need for verification vs need for new information
        
    Read the following conversation. Then select the next role from {participants} to play. Only return the role.

    {history}

    Read the above conversation. Then select the next role from {participants} to play. ONLY RETURN THE ROLE."""

    # Create the team
    team = SelectorGroupChat(
        participants=[research_assistant, verifier, summary_agent],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True
    )

    task = "There is a TV show that I watched a while ago. I forgot the name but I do remember what happened in one of the episodes. Can you help me find the name? Here is what I remember in one of the episodes: Two men play poker. One folds after another tells him to bet. The one who folded actually had a good hand and fell for the bluff. On the second hand, the same man folds again, but this time with a bad hand. A man gets locked in the room, and then his daughter knocks on the door. Two men go to a butcher shop, and one man brings a gift of vodka. Please browse the web deeply to find the TV show episode where this happened exactly" 

    await Console(team.run_stream(task=task))



asyncio.run(main())
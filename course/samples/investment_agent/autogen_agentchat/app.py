# ppip install -U autogen-agentchat autogen-ext[openai,web-surfer] autogenstudio
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogenstudio.gallery.tools import google_search_tool, fetch_webpage_tool 


async def main() -> None:
    # Initialize the model client
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-11-20")

    # Set up termination conditions
    termination = MaxMessageTermination(max_messages=30) | TextMentionTermination("TERMINATE")

    # Client Profile Agent
    client_profiler = AssistantAgent(
        name="client_profiler",
        description="Financial advisor specialized in client profiling and risk assessment",
        model_client=model_client,
        system_message="""You are a financial advisor specialized in client profiling and risk assessment.
        Your responsibilities include:
        1. Gathering and analyzing client information
        2. Assessing risk tolerance
        3. Understanding investment goals and time horizons
        4. Identifying constraints and preferences
        5. Creating comprehensive client profiles
        
        Present findings in a structured format and recommend a suitable investment approach. Make as little assumptions as possible to avoid bias, only work with the information provided.
        End your analysis with "PROFILE COMPLETE" when finished."""
    )

    # Research Strategy Agent
    research_strategist = AssistantAgent(
        name="research_strategist",
        description="Investment research strategist that plans and directs market research",
        model_client=model_client,
        system_message="""You are an investment research strategist.
        Your role is to:
        1. Analyze client profiles and determine key research areas
        2. Create specific, targeted search queries for the research agent
        3. Provide context and priority for each query
        4. Specify important data points to extract
        5. Validate if gathered information meets client needs

        For each research request:
        - Break down into specific search queries
        - Prioritize queries by importance
        - Specify required data points
        - Provide context for interpretation
        
        Example queries:
        - "Top performing moderate-risk ETFs 2024 5-year returns expense ratios"
        - "Tax-efficient retirement investment vehicles comparison current year"
        - "Industry sector analysis technology healthcare finance recent trends"
        Be as brief as possible, and avoid unnecessary details. Just the exact queries and a short rationale.
        End strategy with "RESEARCH PLAN READY" when complete."""
    )

    # Research Agent
    research_agent = AssistantAgent(
        name="research_agent",
        description="Market research agent that executes research plans and analyzes findings",
        model_client=model_client,
        tools=[google_search_tool, fetch_webpage_tool],
        reflect_on_tool_use=True,
        system_message="""You are a market research agent equipped with web search capabilities.
        Your responsibilities:
        1. Execute at most 2 search queries provided by the research strategist
        2. Extract relevant data points and metrics
        3. Synthesize information from multiple sources
        4. Provide structured findings
        5. Request query refinement if needed
        
        For each search:
        - Use search tools to gather information
        - Extract specified data points
        - Validate source credibility
        - Structure findings clearly
        - Note any information gaps
        
        Present findings in a clear, structured format.
        End research with "RESEARCH COMPLETE" when finished."""
    )

    # Portfolio Construction Agent
    portfolio_constructor = AssistantAgent(
        name="portfolio_constructor",
        description="Investment strategist specialized in portfolio construction",
        model_client=model_client,
        system_message="""You are an investment strategist specialized in portfolio construction.
        Your responsibilities include:
        1. Analyzing research findings
        2. Developing asset allocation strategies
        3. Selecting specific investment vehicles
        4. Optimizing portfolios for risk-return
        5. Considering tax efficiency
        
        Based on the client profile and research:
        - Create strategic asset allocation
        - Select specific investments
        - Optimize for risk-adjusted returns
        - Consider tax implications
        - Calculate expected returns and risks
        
        Present recommendations with clear rationale.
        End with "PORTFOLIO READY" when complete."""
    )

    # Verification Agent
    verifier = AssistantAgent(
        name="verifier",
        description="Compliance and verification specialist",
        model_client=model_client,
        system_message="""You are a compliance and verification specialist.
        Your responsibilities include:
        1. Reviewing investment recommendations
        2. Ensuring regulatory compliance
        3. Validating suitability
        4. Checking investment restrictions
        5. Verifying documentation
        
        Respond with "VERIFIED" if approved or "REVISION NEEDED" with specific concerns."""
    )

    # Summary Agent
    summary_agent = AssistantAgent(
        name="summary_agent",
        description="Investment proposal specialist",
        model_client=model_client,
        system_message="""You are an investment proposal specialist.
        Create clear, comprehensive investment proposals including:
        1. Executive summary
        2. Client profile overview
        3. Investment strategy
        4. Portfolio recommendations
        5. Risk analysis
        6. Implementation plan
        
        Format in professional markdown with clear sections.
        End with "TERMINATE" when proposal is complete."""
    )

    # User Proxy
    user_proxy = UserProxyAgent(
        name="user_proxy",
        description="A banker/advisor working with a client", 
    )

    # Create selector prompt
    selector_prompt = """You are coordinating an investment advisory team. The following roles are available:
    {roles}

    Process flow:
    1. client_profiler gathers and analyzes client information
    2. research_strategist develops research plan
    3. research_agent executes research and analyzes findings
    4. portfolio_constructor develops investment strategy
    5. verifier reviews for compliance and suitability
    6. summary_agent creates final proposal
    7. user_proxy provides feedback and approvals

    Select the next appropriate role based on:
    - Current stage in the process
    - Last speaker's output
    - Need for human input/feedback
    - Completion status of current task

    Read the following conversation and select the next role from {participants}. Only return the role.

    {history}

    Read the above conversation. Then select the next role from {participants} to play. ONLY RETURN THE ROLE."""

    # Create the team
    team = SelectorGroupChat(
        participants=[client_profiler, research_strategist, research_agent, portfolio_constructor, verifier, summary_agent, user_proxy],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True
    )

    # Example task
    task = """I need an investment portfolio for a client with the following profile:
    - 45-year-old professional
    - Income: $200,000/year
    - Investment horizon: 20 years
    - Risk tolerance: Moderate
    - Goal: Retirement planning
    Please analyze and provide a comprehensive investment proposal.""" 

    await Console(team.run_stream(task=task))

if __name__ == "__main__":
    asyncio.run(main())


# pip install -U autogen-core
# Mock implementation of Sales Multi-Agent System using a Router Pattern
# A Router Agent receives user messages and routes them to specialized agents - LeadQualificationAgent, QuotationAgent, ProductInfoAgent, and SalesFollowupAgent

from dataclasses import dataclass
from typing import List, Dict
import asyncio

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
    DefaultTopicId,
    default_subscription
)

# Message Types
@dataclass
class Message:
    content: str

@dataclass
class LeadInquiry:
    customer_name: str
    inquiry_text: str
    contact_info: str

@dataclass
class QuoteRequest:
    product_id: str
    quantity: int
    customer_details: Dict[str, str]
    special_requirements: str

@dataclass
class ProductQuery:
    product_id: str
    query_type: str
    specific_questions: List[str]

@dataclass
class FollowupTask:
    lead_id: str
    task_type: str
    priority: str
    details: str

@dataclass
class UserMessage:
    content: str
    metadata: Dict[str, str]

# Router Agent
@default_subscription
class RouterAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Sales Router Agent")

    @message_handler
    async def handle_user_message(self, message: UserMessage, ctx: MessageContext) -> Message:
        content = message.content.lower()
        
        if any(word in content for word in ["price", "quote", "cost", "pricing"]):
            quote_request = QuoteRequest(
                product_id="default",
                quantity=1,
                customer_details={"source": "user"},
                special_requirements=message.content
            )
            print(">>> [RouterAgent] Delegating to QuotationAgent for pricing request")
            await self.publish_message(quote_request, topic_id=DefaultTopicId())
            
        elif any(word in content for word in ["product", "specs", "features", "compare"]):
            product_query = ProductQuery(
                product_id="default",
                query_type="specs",
                specific_questions=[message.content]
            )
            print(">>> [RouterAgent] Delegating to ProductInfoAgent for product information")
            await self.publish_message(product_query, topic_id=DefaultTopicId())
            
        elif any(word in content for word in ["interested", "inquiry", "learn more"]):
            lead_inquiry = LeadInquiry(
                customer_name="User",
                inquiry_text=message.content,
                contact_info="user@example.com"
            )
            print(">>> [RouterAgent] Delegating to LeadQualificationAgent for new inquiry")
            await self.publish_message(lead_inquiry, topic_id=DefaultTopicId())
            
        else:
            followup_task = FollowupTask(
                lead_id="default",
                task_type="general",
                priority="medium",
                details=message.content
            )
            print(">>> [RouterAgent] Delegating to SalesFollowupAgent for follow-up task")
            await self.publish_message(followup_task, topic_id=DefaultTopicId())
        
        return Message(content="Processed")

# Specialized Agents
@default_subscription
class LeadQualificationAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Lead Qualification Agent")

    @message_handler
    async def handle_lead(self, message: LeadInquiry, ctx: MessageContext) -> Message:
        print(f">>> [LeadQualificationAgent] Qualifying lead: {message.customer_name} interested in {message.inquiry_text}")
        return Message(content="Lead processed")

@default_subscription
class QuotationAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Quotation Agent")

    @message_handler
    async def handle_quote(self, message: QuoteRequest, ctx: MessageContext) -> Message:
        print(f">>> [QuotationAgent] Generating quote for {message.product_id}, quantity: {message.quantity}")
        return Message(content="Quote generated")

@default_subscription
class ProductInfoAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Product Information Agent")

    @message_handler
    async def handle_product_query(self, message: ProductQuery, ctx: MessageContext) -> Message:
        print(f">>> [ProductInfoAgent] Providing {message.query_type} information for product {message.product_id}")
        return Message(content="Product info provided")

@default_subscription
class SalesFollowupAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Sales Followup Agent")

    @message_handler
    async def handle_followup(self, message: FollowupTask, ctx: MessageContext) -> Message:
        print(f">>> [SalesFollowupAgent] Scheduling {message.task_type} task (Priority: {message.priority})")
        return Message(content="Followup scheduled")

async def main() -> None:
    # Create runtime
    runtime = SingleThreadedAgentRuntime()

    # Register all agents
    await RouterAgent.register(
        runtime,
        "router",
        lambda: RouterAgent()
    )

    for agent_class, agent_type in [
        (LeadQualificationAgent, "lead_qualifier"),
        (QuotationAgent, "quotation"),
        (ProductInfoAgent, "product_info"),
        (SalesFollowupAgent, "sales_followup")
    ]:
        await agent_class.register(
            runtime,
            type=agent_type,
            factory=lambda a=agent_class: a()
        )

    # Start the runtime
    runtime.start()

    # Test with some example messages
    router_id = AgentId("router", "default")
    
    test_messages = [
        "I'm interested in learning more about your products",
        "What's the price for 100 units?",
        "Can you compare Model A vs Model B?",
        "Please schedule a follow-up meeting",
    ]

    for msg in test_messages:
        print(f"\n>>> User: {msg}")
        await runtime.send_message(
            UserMessage(content=msg, metadata={}),
            router_id
        )
        print("--------------------------------")
        await asyncio.sleep(1)  # Give time for message processing

    # Stop the runtime
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
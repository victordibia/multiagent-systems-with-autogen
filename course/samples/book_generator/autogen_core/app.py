from typing import List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
import os, asyncio, tempfile
from pathlib import Path
from tools import generate_images, generate_pdf_report
from dotenv import load_dotenv
from autogen_core import (
    MessageContext, RoutedAgent, SingleThreadedAgentRuntime,
    TopicId, type_subscription, message_handler
)

load_dotenv()
OUTPUT_DIR = Path(tempfile.gettempdir()) / "story_generator"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class Section(BaseModel):
    title: str
    level: str
    content: str
    image: Optional[str]

class BookSections(BaseModel):
    sections: List[Section]

class StoryRequest(BaseModel):
    prompt: str

@type_subscription(topic_type="StoryGeneratorAgent")
class StoryGeneratorAgent(RoutedAgent):
    def __init__(self, api_key: str) -> None:
        super().__init__("Story generator agent")
        self.client = genai.Client(api_key=api_key)

    @message_handler
    async def handle_story_request(self, message: StoryRequest, ctx: MessageContext) -> None:
        try:
            print(f">>> StoryGeneratorAgent: {message.prompt}")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=f"Create a children's story book based on this prompt: {message.prompt}",
                config=types.GenerateContentConfig(
                    system_instruction="""You are a creative children's book writer.
                                Create engaging, age-appropriate stories structured as a book with clear sections.
                                Each section needs a descriptive image that matches the story content. The book MUST HAVE:
                    1. Exactly 2 chapter sections
                    2. Each section must have an engaging title, a level (e.g., "title", "h1", "h2"), appropriate content, and a vivid image description.""",
                    response_mime_type="application/json",
                    response_schema={
                        "required": ["sections"],
                        "properties": {
                            "sections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["title", "level", "content", "image"],
                                    "properties": {
                                        "title": {"type": "STRING"},
                                        "level": {"type": "STRING"},
                                        "content": {"type": "STRING"},
                                        "image": {"type": "STRING"}
                                    }
                                }
                            }
                        },
                        "type": "OBJECT",
                    },
                ),
            )
            book_content = BookSections.model_validate_json(response.text)
            await self.publish_message(
                book_content,
                topic_id=TopicId("ImageGeneratorAgent", source=self.id.key)
            )
        except Exception as e:
            print(f"Error in story generation: {str(e)}")

@type_subscription(topic_type="ImageGeneratorAgent")
class ImageGeneratorAgent(RoutedAgent):
    def __init__(self, api_key: str) -> None:
        super().__init__("Image generator agent")
        self.client = genai.Client(api_key=api_key)

    async def generate_image(self, prompt: str) -> str:
        try:
            images = generate_images(prompt, output_dir=OUTPUT_DIR)
            return images[0] if images else ""
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return ""

    @message_handler
    async def handle_book_sections(self, message: BookSections, ctx: MessageContext) -> None:
        try:
            print(">>> ImageGeneratorAgent: Generating images for book sections")
            sections_with_images = []
            for section in message.sections:
                image_path = await self.generate_image(section.image) if section.image else None
                sections_with_images.append(Section(
                    title=section.title,
                    level=section.level,
                    content=section.content,
                    image=image_path
                ))
            
            await self.publish_message(
                BookSections(sections=sections_with_images),
                topic_id=TopicId("BookGeneratorAgent", source=self.id.key)
            )
        except Exception as e:
            print(f"Error in image generation: {str(e)}")

@type_subscription(topic_type="BookGeneratorAgent")
class BookGeneratorAgent(RoutedAgent):
    def __init__(self, api_key: str) -> None:
        super().__init__("Book generator agent")
    
    @message_handler
    async def handle_book_content(self, message: BookSections, ctx: MessageContext) -> None:
        try:
            print(">>> BookGeneratorAgent: Generating story book pdf")
            pdf_path = OUTPUT_DIR / "story_book.pdf"
            generate_pdf_report(
                sections=[s.model_dump() for s in message.sections],
                output_file=str(pdf_path),
                report_title=message.sections[0].title
            )
            print(f"Generated story book at: {pdf_path}")
        except Exception as e:
            print(f"Error in book generation: {str(e)}")

async def main(prompt: str) -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY environment variable")
    
    runtime = SingleThreadedAgentRuntime()
    
    for agent_class, topic in [
        (StoryGeneratorAgent, "StoryGeneratorAgent"),
        (ImageGeneratorAgent, "ImageGeneratorAgent"),
        (BookGeneratorAgent, "BookGeneratorAgent")
    ]:
        await agent_class.register(
            runtime, type=topic,
            factory=lambda a=agent_class: a(api_key=api_key)
        )
    
    runtime.start()
    await runtime.publish_message(
        StoryRequest(prompt=prompt),
        topic_id=TopicId("StoryGeneratorAgent", source="user")
    )
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main("Generate a children's story book on the wonders of the amazon rain forest"))
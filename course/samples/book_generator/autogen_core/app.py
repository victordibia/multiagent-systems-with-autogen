from typing import List, Optional
import json
from pydantic import BaseModel
from google import genai
from google.genai import types
import os
from pathlib import Path
import asyncio
import tempfile
from tools import generate_images, generate_pdf_report
from dotenv import load_dotenv

load_dotenv()

from autogen_core import (
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    type_subscription,
    message_handler,
)

# Create temp directory for outputs
OUTPUT_DIR = Path(tempfile.gettempdir()) / "story_generator"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Data Models
class Section(BaseModel):
    title: str
    level: str
    content: str
    image: Optional[str]

class BookSections(BaseModel):
    sections: List[Section]

# Message type for initial request
class StoryRequest(BaseModel):
    prompt: str

# Topic Types
story_generator_topic = "StoryGeneratorAgent"
book_generator_topic = "BookGeneratorAgent"

# Story Generator Agent
@type_subscription(topic_type=story_generator_topic)
class StoryGeneratorAgent(RoutedAgent):
    def __init__(self, api_key: str) -> None:
        super().__init__("A story generator agent")
        self.client = genai.Client(api_key=api_key)

    @message_handler
    async def handle_story_request(self, message: StoryRequest, ctx: MessageContext) -> None:
        try:
            print("-" * 60)
            print(f"\nStoryGeneratorAgent: Received story request: {message.prompt}")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=f"""Create a children's story book based on this prompt: {message.prompt}
                             """,
                config=types.GenerateContentConfig(
                    system_instruction="""You are a creative children's book writer.
                                Create engaging, age-appropriate stories structured as a book with clear sections.
                                Each section needs a descriptive image that matches the story content. The book MUST HAVE:
                    1. Exactly 2 chapter sections
                    2. Each section must have an engaging title,  a level (e.g., "title", "h1", "h2"), appropriate content, and a vivid image description. The first section title should be the title of the story.
                    Each section must have an engaging title, appropriate content, and a vivid image description.
                    Make it engaging and suitable for young readers.""",
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
            
            # Parse and validate the response
            book_content = BookSections.model_validate_json(response.text)
            print(f"\nGenerated story structure with {len(book_content.sections)} sections")
            print("-" * 60)
            
            # Pass to Book Generator
            await self.publish_message(
                book_content,
                topic_id=TopicId(book_generator_topic, source=self.id.key)
            )
            
        except Exception as e:
            print(f"Error in story generation: {str(e)}")

# Book Generator Agent
@type_subscription(topic_type=book_generator_topic)
class BookGeneratorAgent(RoutedAgent):
    def __init__(self, api_key: str) -> None:
        super().__init__("A book generator agent")
        self.client = genai.Client(api_key=api_key)
        
    async def generate_image(self, prompt: str) -> str:
        """Generate image using Gemini and return the path"""
        try:
            print("-" * 60)
            images = generate_images(prompt)
            print(f"Generated image for prompt: {prompt}")
            print("-" * 60)
            return images[0] if images else ""
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return ""

    @message_handler
    async def handle_book_content(self, message: BookSections, ctx: MessageContext) -> None:
        print("-" * 60)
        print(f"\nBookGeneratorAgent: Received book content with {len(message.sections)} sections")
        try:
            # Generate images for each section that has an image prompt
            sections_with_images = []
            for section in message.sections:
                if section.image:
                    image_path = await self.generate_image(section.image)
                    sections_with_images.append({
                        "title": section.title,
                        "level": section.level,
                        "content": section.content,
                        "image": image_path
                    })
                else:
                    sections_with_images.append({
                        "title": section.title,
                        "level": section.level,
                        "content": section.content
                    })  
            # save sections_with_images to json file 
            json_path = OUTPUT_DIR / 'sections_with_images.json'
            with open(json_path, 'w') as f:
                json.dump(sections_with_images, f)
            
            pdf_path = OUTPUT_DIR / "story_book.pdf"
            generate_pdf_report(
                sections=sections_with_images,
                output_file=str(pdf_path),
                report_title=message.sections[0].title
            ) 
            print(f"\nGenerated files in {OUTPUT_DIR}:")
            print(f"- PDF: {pdf_path}")
            print(f"- JSON: {json_path}")
            print("-" * 60)
            
        except Exception as e:
            print(f"Error in book generation: {str(e)}")

# Setup and run the system
async def setup_story_book_system(api_key: str):
    runtime = SingleThreadedAgentRuntime()
    
    # Register agents
    await StoryGeneratorAgent.register(
        runtime,
        type=story_generator_topic,
        factory=lambda: StoryGeneratorAgent(api_key=api_key)
    )
    
    await BookGeneratorAgent.register(
        runtime,
        type=book_generator_topic,
        factory=lambda: BookGeneratorAgent(api_key=api_key)
    )
    
    return runtime

async def main(prompt: str) -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY environment variable")
    
    # Initialize the system
    runtime = await setup_story_book_system(api_key)
    
    # Start the runtime
    runtime.start()
    
    # Send a story request
    await runtime.publish_message(
        StoryRequest(prompt=prompt),
        topic_id=TopicId(story_generator_topic, source="user")
    )
    
    # Wait for completion
    await runtime.stop_when_idle()

if __name__ == "__main__":
    task = "Generate a children's story books on the wonders of the amazon rain forest"
    asyncio.run(main(task))
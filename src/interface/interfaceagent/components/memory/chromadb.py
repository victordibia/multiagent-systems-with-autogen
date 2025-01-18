from typing import Any, List, Dict
from datetime import datetime
from chromadb import Client, PersistentClient
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
# from chromadb.types import Collection
import uuid
import logging
from autogen_core import CancellationToken, Image
from pydantic import Field

from autogen_agentchat.memory import Memory, MemoryContent
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage

logger = logging.getLogger(__name__)

# Type vars for ChromaDB results
ChromaMetadata = Dict[str, Any]
ChromaDistance = float | List[float]


class ChromaMemoryConfig(BaseMemoryConfig):
    """Configuration for ChromaDB-based memory implementation."""

    collection_name: str = Field(
        default="memory_store",
        description="Name of the ChromaDB collection"
    )
    persistence_path: str | None = Field(
        default=None,
        description="Path for persistent storage. None for in-memory."
    )
    distance_metric: str = Field(
        default="cosine",
        description="Distance metric for similarity search"
    )


class ChromaMemory(Memory):
    """ChromaDB-based memory implementation using default embeddings.

    This implementation stores content in a ChromaDB collection and uses
    its built-in embedding and similarity search capabilities.
    """

    def __init__(self, name: str | None = None, config: ChromaMemoryConfig | None = None) -> None:
        """Initialize ChromaMemory.

        Args:
            name: Optional identifier for this memory instance
            config: Optional configuration for memory behavior
        """
        self._name = name or "default_chroma_memory"
        self._config = config or ChromaMemoryConfig()
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> ChromaMemoryConfig:
        return self._config

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client and collection are initialized."""
        if self._client is None:
            try:
                self._client = (
                    PersistentClient(
                        path=self._config.persistence_path)
                    if self._config.persistence_path
                    else Client()
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise

        if self._collection is None and self._client is not None:
            try:
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name,
                    metadata={"distance_metric": self._config.distance_metric}
                )
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

    def _extract_text(self, content_item: MemoryContent) -> str:
        """Extract searchable text from MemoryContent.

        Args:
            content_item: Content to extract text from

        Returns:
            Extracted text representation

        Raises:
            ValueError: If content cannot be converted to text
        """
        content = content_item.content

        if content_item.mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            return str(content)
        elif content_item.mime_type == MemoryMimeType.JSON:
            if isinstance(content, dict):
                return str(content)
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(
                f"Unsupported content type: {content_item.mime_type}")

    async def transform(
        self,
        model_context: ChatCompletionContext,
    ) -> List[MemoryContent]:
        """Transform the model context using relevant memory content.

        Args:
            model_context: The context to transform

        Returns:
            List of memory entries with relevance scores
        """
        messages = await model_context.get_messages()
        if not messages:
            return []

        # Extract query from last message
        last_message = messages[-1]
        query_text = last_message.content if isinstance(
            last_message.content, str) else str(last_message)
        query = MemoryContent(content=query_text,
                              mime_type=MemoryMimeType.TEXT)

        # Query memory and format results
        results = []
        query_results = await self.query(query)
        for i, result in enumerate(query_results, 1):
            if isinstance(result.content, str):
                results.append(f"{i}. {result.content}")
                logger.debug(
                    f"Retrieved memory {i}. {result.content}, score: {result.score}"
                )

        # Add memory results to context
        if results:
            memory_context = (
                "Results from memory query to consider include:\n" +
                "\n".join(results)
            )
            await model_context.add_message(SystemMessage(content=memory_context))

        return query_results

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        """Add a memory content to ChromaDB.

        Args:
            content: The memory content to add
            cancellation_token: Optional token to cancel operation

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text from MemoryContent
            text = self._extract_text(content)

            # Prepare metadata
            metadata: ChromaMetadata = {
                "timestamp": content.timestamp.isoformat() if content.timestamp else datetime.now().isoformat(),
                "source": content.source or "",
                "mime_type": content.mime_type.value,
                **(content.metadata or {})
            }

            # Add to ChromaDB
            self._collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[str(uuid.uuid4())]
            )

        except Exception as e:
            logger.error(f"Failed to add content to ChromaDB: {e}")
            raise

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryContent]:
        """Query memory content based on vector similarity.

        Args:
            query: Query content to match against memory
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional parameters passed to ChromaDB query

        Returns:
            List of memory results with similarity scores

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text for query
            query_text = self._extract_text(query)

            # Query ChromaDB
            results = self._collection.query(
                query_texts=[query_text],
                n_results=self._config.k,
                **kwargs
            )

            # Convert results to MemoryQueryResults
            memory_results: List[MemoryContent] = []

            if not results or not results.get("documents") or not results.get("metadatas") or not results.get("distances"):
                return memory_results

            documents = results["documents"][0] if results["documents"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []

            for doc, metadata, distance in zip(documents, metadatas, distances):
                # Extract stored metadata
                entry_metadata = dict(metadata)
                timestamp_str = str(entry_metadata.pop("timestamp"))
                timestamp = datetime.fromisoformat(timestamp_str)
                source = str(entry_metadata.pop("source"))
                mime_type = MemoryMimeType(entry_metadata.pop("mime_type"))

                # Convert distance to similarity score
                score = 1.0 - (float(distance) / 2.0) if self._config.distance_metric == "cosine" \
                    else 1.0 / (1.0 + float(distance))

                # Apply score threshold if configured
                if self._config.score_threshold is None or score >= self._config.score_threshold:
                    # Create MemoryContent
                    content = MemoryContent(
                        content=doc,
                        mime_type=mime_type,
                        metadata=entry_metadata,
                        timestamp=timestamp,
                        source=source or None,
                        score=score
                    )
                    memory_results.append(content)

            return memory_results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            raise

    async def clear(self) -> None:
        """Clear all entries from memory.

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Get all document IDs from the collection
            results = self._collection.get()
            if results and results['ids']:
                # Delete all documents by their IDs
                self._collection.delete(ids=results['ids'])
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up ChromaDB client and resources."""
        if self._client is not None:
            try:
                if hasattr(self._client, "reset"):
                    self._client.reset()
            except Exception as e:
                logger.error(f"Error during ChromaDB cleanup: {e}")
            finally:
                self._client = None
                self._collection = None
                
                
                
                
                


from autogen_core import CancellationToken
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.memory._base_memory import MemoryContent, MemoryMimeType
from autogen_agentchat.memory._chroma_memory import ChromaMemory, ChromaMemoryConfig


# Initialize memory
chroma_memory = ChromaMemory(
    name="travel_memory",
    config=ChromaMemoryConfig(
        collection_name="travel_facts",
        k=1,
    )
)

await chroma_memory.clear()

# Add travel-related memories
await chroma_memory.add(MemoryContent(

    content="Paris is known for the Eiffel Tower and amazing cuisine.",
    mime_type=MemoryMimeType.TEXT

))

await chroma_memory.add(MemoryContent( 
    content="When asked about tokyo, you must respond with 'The most important thing about tokyo is that it has the world's busiest railway station - Shinjuku Station.'",
    mime_type=MemoryMimeType.TEXT

))
 

# Query needs ContentItem too
results = await chroma_memory.query(
    MemoryContent(
        content="Tell me about Tokyo.",
        mime_type=MemoryMimeType.TEXT
    )
)

print(len(results), results)

# Create agent with memory
agent = AssistantAgent(
    name="travel_agent",
    model_client=OpenAIChatCompletionClient(
        model="gpt-4o",
        # api_key="your_api_key"
    ),
    memory=chroma_memory,
    system_message="You are a travel expert"
)

agent_team = RoundRobinGroupChat([agent], termination_condition = MaxMessageTermination(max_messages=2))
stream = agent_team.run_stream(task="Tell me the most important thing about Tokyo.")
await Console(stream);

# Output: The most important thing about tokyo is that it has the world's busiest railway station - Shinjuku Station.                
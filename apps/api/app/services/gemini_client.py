import json
import google.generativeai as genai
from typing import Optional

from app.config import get_settings


class GeminiClient:
    """Centralized wrapper around the Google Gemini API.

    Used by all AI services for text generation, JSON-structured output,
    and embedding generation. Swap this to use a different LLM provider.
    """

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.embedding_model = "models/gemini-embedding-001"

    async def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The user prompt.
            system_instruction: Optional system-level instruction.

        Returns:
            The generated text response.
        """
        if system_instruction:
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=system_instruction,
            )
        else:
            model = self.model

        response = model.generate_content(prompt)
        return response.text

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> dict | list:
        """Generate structured JSON output from a prompt.

        The prompt should ask the model to return valid JSON.
        Parses the response and returns the Python dict/list.

        Args:
            prompt: The prompt requesting JSON output.
            system_instruction: Optional system instruction.

        Returns:
            Parsed JSON as a dict or list.
        """
        text = await self.generate(prompt, system_instruction)

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Uses Gemini's embedding model with 768 dimensions
        (reduced from 3072 to fit pgvector HNSW index limits).

        Args:
            text: The text to embed.

        Returns:
            A list of 768 floats representing the embedding vector.
        """
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document",
            output_dimensionality=768,
        )
        return result["embedding"]

    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a search query.

        Uses retrieval_query task type for better search results.
        """
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_query",
            output_dimensionality=768,
        )
        return result["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single batch.

        Args:
            texts: List of texts to embed.

        Returns:
            List of 768-dimension embedding vectors.
        """
        result = genai.embed_content(
            model=self.embedding_model,
            content=texts,
            task_type="retrieval_document",
            output_dimensionality=768,
        )
        return result["embedding"]

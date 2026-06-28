from app.services.gemini_client import GeminiClient
from app.utils.supabase_client import get_supabase_client


class EmbeddingService:
    """Generates and stores vector embeddings for clauses using Gemini.

    Embeddings enable semantic search across an org's contract clauses
    via pgvector cosine similarity (HNSW index).

    Uses Gemini gemini-embedding-001 (3072 dimensions).
    To swap embedding provider, modify GeminiClient.embed methods.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()

    async def generate_and_store(self, clause_id: str, content: str, org_id: str) -> None:
        """Generate an embedding for a clause and store it in clause_embeddings.

        Args:
            clause_id: The clause UUID.
            content: The clause text to embed.
            org_id: Organization ID.
        """
        embedding = await self.gemini.embed(content)

        self.supabase.table("clause_embeddings").insert({
            "org_id": org_id,
            "clause_id": clause_id,
            "embedding": embedding,
            "model_name": "gemini-embedding-001",
        }).execute()

    async def batch_embed_contract(self, contract_id: str, org_id: str) -> int:
        """Generate embeddings for all clauses in a contract.

        Args:
            contract_id: The contract UUID.
            org_id: Organization ID.

        Returns:
            Number of clauses embedded.
        """
        clauses = (
            self.supabase.table("clauses")
            .select("id, content")
            .eq("contract_id", contract_id)
            .eq("org_id", org_id)
            .execute()
        ).data

        if not clauses:
            return 0

        texts = [c["content"] for c in clauses]
        embeddings = await self.gemini.embed_batch(texts)

        records = []
        for clause, embedding in zip(clauses, embeddings):
            records.append({
                "org_id": org_id,
                "clause_id": clause["id"],
                "embedding": embedding,
                "model_name": "gemini-embedding-001",
            })

        if records:
            self.supabase.table("clause_embeddings").insert(records).execute()

        return len(records)

    async def semantic_search(
        self, query: str, org_id: str, threshold: float = 0.7, limit: int = 10
    ) -> list[dict]:
        """Search for clauses semantically similar to a query.

        Uses the match_clauses RPC function with pgvector cosine similarity.

        Args:
            query: Natural language search query.
            org_id: Organization ID to scope results.
            threshold: Minimum similarity score (0-1).
            limit: Maximum results to return.

        Returns:
            List of matching clauses with similarity scores.
        """
        query_embedding = await self.gemini.embed_query(query)

        result = self.supabase.rpc(
            "match_clauses",
            {
                "query_embedding": query_embedding,
                "match_org_id": org_id,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()

        return result.data or []

    async def find_similar(self, clause_id: str, org_id: str, limit: int = 10) -> list[dict]:
        """Find clauses similar to a given clause.

        Args:
            clause_id: The reference clause UUID.
            org_id: Organization ID.
            limit: Maximum results.

        Returns:
            List of similar clauses.
        """
        # Get the clause's embedding
        embedding_result = (
            self.supabase.table("clause_embeddings")
            .select("embedding")
            .eq("clause_id", clause_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not embedding_result.data:
            return []

        result = self.supabase.rpc(
            "match_clauses",
            {
                "query_embedding": embedding_result.data["embedding"],
                "match_org_id": org_id,
                "match_threshold": 0.5,
                "match_count": limit + 1,  # +1 to exclude self
            },
        ).execute()

        # Filter out the source clause itself
        return [r for r in (result.data or []) if r["clause_id"] != clause_id][:limit]

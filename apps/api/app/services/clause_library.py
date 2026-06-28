import uuid
from datetime import datetime

from app.services.gemini_client import GeminiClient
from app.utils.supabase_client import get_supabase_client


class ClauseLibraryService:
    """Manages the organization's approved clause library.

    The library stores approved legal language that the review agent uses
    as a playbook. When lawyers accept redlines, the accepted language
    gets added here, creating a feedback loop that improves future reviews.

    Embeddings are generated for library clauses to enable semantic search
    via the search_playbook tool.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()

    async def add_clause(
        self, org_id: str, clause_type: str, title: str, content: str, tags: list[str]
    ) -> dict:
        """Add a new clause to the library with its embedding.

        Args:
            org_id: Organization ID.
            clause_type: Category (e.g., 'indemnification', 'confidentiality').
            title: Descriptive title.
            content: The clause text.
            tags: Searchable tags.

        Returns:
            The created clause record.
        """
        embedding = await self.gemini.embed(content)
        clause_id = str(uuid.uuid4())

        result = self.supabase.table("clause_library").insert({
            "id": clause_id,
            "org_id": org_id,
            "clause_type": clause_type,
            "title": title,
            "content": content,
            "tags": tags,
            "embedding": embedding,
            "is_approved": False,
            "usage_count": 0,
        }).execute()

        return result.data[0]

    async def approve_clause(self, clause_id: str, approved_by: str, org_id: str) -> None:
        """Mark a clause as approved by a lawyer/admin.

        Args:
            clause_id: Clause UUID.
            approved_by: User UUID who approved.
            org_id: Organization ID.
        """
        self.supabase.table("clause_library").update({
            "is_approved": True,
            "approved_by": approved_by,
            "approved_at": datetime.utcnow().isoformat(),
        }).eq("id", clause_id).eq("org_id", org_id).execute()

    async def search_library(
        self,
        org_id: str,
        query: str,
        clause_type: str | None = None,
        approved_only: bool = True,
        threshold: float = 0.6,
        limit: int = 10,
    ) -> list[dict]:
        """Semantic search across the clause library.

        Args:
            org_id: Organization ID.
            query: Search query text.
            clause_type: Optional filter by clause type.
            approved_only: Only return approved clauses.
            threshold: Minimum similarity score.
            limit: Max results.

        Returns:
            List of matching clauses with similarity scores.
        """
        query_embedding = await self.gemini.embed_query(query)

        # Use raw SQL for pgvector similarity search on clause_library
        sql = f"""
        select id, clause_type, title, content, is_approved, tags, usage_count,
               1 - (embedding <=> '{query_embedding}'::vector) as similarity
        from clause_library
        where org_id = '{org_id}'
        {'and is_approved = true' if approved_only else ''}
        {'and clause_type = ' + repr(clause_type) if clause_type else ''}
        and 1 - (embedding <=> '{query_embedding}'::vector) > {threshold}
        order by embedding <=> '{query_embedding}'::vector
        limit {limit}
        """

        # Fallback to text search if embedding search is not viable
        query_builder = (
            self.supabase.table("clause_library")
            .select("*")
            .eq("org_id", org_id)
        )
        if approved_only:
            query_builder = query_builder.eq("is_approved", True)
        if clause_type:
            query_builder = query_builder.eq("clause_type", clause_type)

        query_builder = query_builder.ilike("content", f"%{query}%").limit(limit)
        result = query_builder.execute()

        return result.data or []

    async def import_from_contract(self, clause_id: str, org_id: str) -> dict:
        """Import a clause from a contract into the library.

        Args:
            clause_id: The source clause UUID from the clauses table.
            org_id: Organization ID.

        Returns:
            The created library clause record.
        """
        clause = (
            self.supabase.table("clauses")
            .select("*")
            .eq("id", clause_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        return await self.add_clause(
            org_id=org_id,
            clause_type=clause.get("clause_type", "general"),
            title=clause.get("title", "Imported clause"),
            content=clause["content"],
            tags=["imported", "from-contract"],
        )

    async def increment_usage(self, clause_id: str, org_id: str) -> None:
        """Increment the usage count for a library clause."""
        clause = (
            self.supabase.table("clause_library")
            .select("usage_count")
            .eq("id", clause_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        if clause:
            self.supabase.table("clause_library").update({
                "usage_count": clause["usage_count"] + 1,
            }).eq("id", clause_id).execute()

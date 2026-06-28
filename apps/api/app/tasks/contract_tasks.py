import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def parse_contract_task(self, contract_id: str, org_id: str):
    """Async task: Parse a contract file into clauses.

    Extracts text, uses Gemini to identify clauses, stores results.
    Automatically triggers embedding generation on success.
    """
    from app.services.parser import ParserService

    try:
        parser = ParserService()
        loop = asyncio.new_event_loop()
        clauses = loop.run_until_complete(parser.parse_contract(contract_id, org_id))
        loop.close()

        # Trigger embedding generation
        embed_clauses_task.delay(contract_id, org_id)

        return {"status": "parsed", "clause_count": len(clauses)}
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def embed_clauses_task(self, contract_id: str, org_id: str):
    """Async task: Generate embeddings for all clauses in a contract.

    Uses Gemini embedding API and stores vectors in pgvector.
    """
    from app.services.embeddings import EmbeddingService

    try:
        service = EmbeddingService()
        loop = asyncio.new_event_loop()
        count = loop.run_until_complete(service.batch_embed_contract(contract_id, org_id))
        loop.close()

        return {"status": "embedded", "count": count}
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def review_contract_task(self, contract_id: str, org_id: str):
    """Async task: Run AI review on a contract.

    Uses LangChain agent to analyze each clause for risks.
    """
    from app.services.reviewer import ReviewerService

    try:
        reviewer = ReviewerService()
        loop = asyncio.new_event_loop()
        report = loop.run_until_complete(reviewer.review_contract(contract_id, org_id))
        loop.close()

        return {"status": "reviewed", "report_id": report["id"]}
    except Exception as exc:
        self.retry(exc=exc)

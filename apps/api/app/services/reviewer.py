import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field

from app.config import get_settings
from app.services.gemini_client import GeminiClient
from app.services.embeddings import EmbeddingService
from app.utils.supabase_client import get_supabase_client


REVIEW_SYSTEM_PROMPT = """You are a senior legal contract reviewer. Your job is to analyze each clause
in a contract and identify risks, issues, and areas for improvement.

For each clause, you should:
1. Search the organization's playbook for approved language on the topic
2. Assess the risk level (low, medium, high, critical)
3. Find precedent from past contracts
4. Suggest improvements

Be thorough but practical. Focus on material risks, not trivial formatting issues."""


class SearchPlaybookTool(BaseTool):
    """Searches the org's approved clause library for relevant approved language."""

    name: str = "search_playbook"
    description: str = "Search the organization's clause library for approved language on a topic. Input: the topic or clause type to search for."
    org_id: str = Field(default="")

    def _run(self, query: str) -> str:
        supabase = get_supabase_client()
        results = (
            supabase.table("clause_library")
            .select("clause_type, title, content")
            .eq("org_id", self.org_id)
            .eq("is_approved", True)
            .ilike("content", f"%{query}%")
            .limit(5)
            .execute()
        )
        if not results.data:
            return "No approved clauses found in the playbook for this topic."
        return json.dumps(results.data, indent=2)


class CheckClauseRiskTool(BaseTool):
    """Rates a clause's risk level using Gemini."""

    name: str = "check_clause_risk"
    description: str = "Analyze a contract clause for risk. Input: the full clause text. Returns risk level and explanation."

    def _run(self, clause_text: str) -> str:
        gemini = GeminiClient()
        import asyncio
        prompt = f"""Analyze this contract clause for legal risk. Rate it on a scale:
- low: Standard, well-balanced clause
- medium: Some concerns but manageable
- high: Significant risk, should be renegotiated
- critical: Unacceptable risk, must be changed

Return JSON: {{"risk_level": "...", "explanation": "...", "suggested_alternative": "..."}}

Clause:
{clause_text}"""

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(gemini.generate_json(prompt))
        return json.dumps(result)


class FindPrecedentTool(BaseTool):
    """Finds the most similar clause from the org's past contracts."""

    name: str = "find_precedent"
    description: str = "Find similar clauses from past contracts. Input: the clause text to find precedent for."
    org_id: str = Field(default="")

    def _run(self, clause_text: str) -> str:
        embedding_service = EmbeddingService()
        import asyncio
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            embedding_service.semantic_search(clause_text, self.org_id, threshold=0.6, limit=3)
        )
        if not results:
            return "No similar precedent found in past contracts."
        return json.dumps(results, indent=2)


class ReviewerService:
    """AI-powered contract review agent using LangChain + Gemini.

    Uses custom tools to search playbooks, assess risk, and find precedent.
    Produces a ReviewReport with per-clause findings.

    To swap LLM: change ChatGoogleGenerativeAI to a different LangChain chat model.
    To add tools: create a new BaseTool subclass and add to the tools list.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()

    def _create_agent(self, org_id: str) -> AgentExecutor:
        """Create the review agent with org-specific tools."""
        settings = get_settings()
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.google_api_key,
        )

        tools = [
            SearchPlaybookTool(org_id=org_id),
            CheckClauseRiskTool(),
            FindPrecedentTool(org_id=org_id),
        ]

        prompt = ChatPromptTemplate.from_messages([
            ("system", REVIEW_SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)

    async def review_contract(self, contract_id: str, org_id: str) -> dict:
        """Run a full AI review on all clauses in a contract.

        1. Loads all clauses for the contract
        2. For each clause, invokes the LangChain agent
        3. Compiles findings into a ReviewReport
        4. Stores the report in the database

        Args:
            contract_id: Contract UUID.
            org_id: Organization ID.

        Returns:
            The created review report dict.
        """
        # Update contract status
        self.supabase.table("contracts").update(
            {"status": "reviewing"}
        ).eq("id", contract_id).execute()

        # Get all clauses
        clauses = (
            self.supabase.table("clauses")
            .select("*")
            .eq("contract_id", contract_id)
            .eq("org_id", org_id)
            .order("position_start")
            .execute()
        ).data

        agent = self._create_agent(org_id)
        findings = []
        risk_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        max_risk = "low"

        for clause in clauses:
            try:
                result = agent.invoke({
                    "input": f"""Review this contract clause:

Type: {clause['clause_type']}
Title: {clause['title']}
Content: {clause['content']}

Use your tools to:
1. Search the playbook for approved language
2. Check the risk level
3. Find precedent from past contracts

Return your analysis as JSON with: risk_level, issue, suggestion, playbook_reference"""
                })

                output = result.get("output", "{}")
                try:
                    finding = json.loads(output) if isinstance(output, str) else output
                except json.JSONDecodeError:
                    finding = {"risk_level": "medium", "issue": output, "suggestion": ""}

                finding["clause_id"] = clause["id"]
                findings.append(finding)

                clause_risk = finding.get("risk_level", "low")
                if risk_scores.get(clause_risk, 0) > risk_scores.get(max_risk, 0):
                    max_risk = clause_risk

            except Exception as e:
                findings.append({
                    "clause_id": clause["id"],
                    "risk_level": "medium",
                    "issue": f"Review error: {str(e)}",
                    "suggestion": "Manual review recommended",
                })

        # Create review report
        import uuid
        report_id = str(uuid.uuid4())
        report = {
            "id": report_id,
            "org_id": org_id,
            "contract_id": contract_id,
            "summary": f"Reviewed {len(clauses)} clauses. Overall risk: {max_risk}.",
            "overall_risk": max_risk,
            "findings": findings,
        }

        self.supabase.table("review_reports").insert(report).execute()

        # Update contract status
        self.supabase.table("contracts").update(
            {"status": "reviewed"}
        ).eq("id", contract_id).execute()

        return report

    async def accept_findings(self, report_id: str, finding_ids: list[str], org_id: str) -> int:
        """Accept specific findings and add their suggestions to the clause library."""
        report = (
            self.supabase.table("review_reports")
            .select("findings")
            .eq("id", report_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        if not report:
            return 0

        count = 0
        for finding in report.get("findings", []):
            if finding.get("clause_id") in finding_ids and finding.get("suggestion"):
                import uuid
                self.supabase.table("clause_library").insert({
                    "id": str(uuid.uuid4()),
                    "org_id": org_id,
                    "clause_type": finding.get("clause_type", "general"),
                    "title": f"AI Suggested: {finding.get('clause_type', 'clause')}",
                    "content": finding["suggestion"],
                    "is_approved": False,
                    "tags": ["ai-generated", "from-review"],
                }).execute()
                count += 1

        return count

import uuid
from datetime import datetime

from app.services.gemini_client import GeminiClient
from app.utils.supabase_client import get_supabase_client


class GDPRModule:
    """Checks contracts against GDPR Article requirements.

    Required clauses:
    - Data processing purpose and lawful basis
    - Data retention periods
    - Data subject rights
    - Cross-border transfer safeguards
    - Data breach notification procedures
    - Data Processing Agreement (DPA)

    To extend: add new items to REQUIRED_CLAUSES.
    """

    REQUIRED_CLAUSES = [
        {"id": "gdpr_processing", "name": "Data Processing Purpose", "description": "Contract must specify the purpose and lawful basis for data processing"},
        {"id": "gdpr_retention", "name": "Data Retention", "description": "Must define data retention periods and deletion procedures"},
        {"id": "gdpr_subject_rights", "name": "Data Subject Rights", "description": "Must acknowledge data subject rights (access, rectification, erasure)"},
        {"id": "gdpr_transfer", "name": "Cross-Border Transfer", "description": "Must address international data transfers and safeguards (SCCs, adequacy)"},
        {"id": "gdpr_breach", "name": "Breach Notification", "description": "Must include 72-hour breach notification obligation"},
        {"id": "gdpr_dpa", "name": "Data Processing Agreement", "description": "Must include or reference a Data Processing Agreement"},
        {"id": "gdpr_sub_processors", "name": "Sub-Processors", "description": "Must address use of sub-processors and notification requirements"},
    ]

    async def check(self, clauses: list[dict], gemini: GeminiClient) -> list[dict]:
        """Run GDPR compliance check against contract clauses.

        Args:
            clauses: List of extracted clauses from the contract.
            gemini: GeminiClient instance for AI analysis.

        Returns:
            List of compliance findings.
        """
        clauses_text = "\n\n".join(
            f"[{c.get('clause_type', 'unknown')}] {c.get('content', '')}" for c in clauses
        )

        prompt = f"""Analyze these contract clauses for GDPR compliance.

For each of these required provisions, determine if the contract adequately addresses it:
{chr(10).join(f'- {r["name"]}: {r["description"]}' for r in self.REQUIRED_CLAUSES)}

Contract clauses:
{clauses_text}

Return a JSON array where each item has:
- rule_id: the provision identifier
- status: "pass", "fail", or "warning"
- detail: explanation of the finding
- recommendation: what to add or change if status is not "pass"
- clause_id: the relevant clause id if found, or null
"""

        findings = await gemini.generate_json(
            prompt,
            system_instruction="You are a GDPR compliance expert. Be thorough and specific.",
        )

        return findings if isinstance(findings, list) else [findings]


class SOC2Module:
    """Checks contracts against SOC2 Trust Service Criteria.

    Required controls:
    - Security obligations and access controls
    - Availability SLAs and uptime commitments
    - Confidentiality requirements
    - Audit rights
    - Incident response procedures

    To extend: add new items to REQUIRED_CONTROLS.
    """

    REQUIRED_CONTROLS = [
        {"id": "soc2_security", "name": "Security Obligations", "description": "Must define security requirements, access controls, and encryption standards"},
        {"id": "soc2_availability", "name": "Availability SLA", "description": "Must include uptime commitments and remediation for downtime"},
        {"id": "soc2_confidentiality", "name": "Confidentiality", "description": "Must address data confidentiality obligations and handling procedures"},
        {"id": "soc2_audit", "name": "Audit Rights", "description": "Must grant audit rights or provide SOC2 reports"},
        {"id": "soc2_incident", "name": "Incident Response", "description": "Must define incident response and notification procedures"},
        {"id": "soc2_data_integrity", "name": "Data Integrity", "description": "Must address data integrity controls and validation"},
    ]

    async def check(self, clauses: list[dict], gemini: GeminiClient) -> list[dict]:
        """Run SOC2 compliance check."""
        clauses_text = "\n\n".join(
            f"[{c.get('clause_type', 'unknown')}] {c.get('content', '')}" for c in clauses
        )

        prompt = f"""Analyze these contract clauses for SOC2 Trust Service Criteria compliance.

For each of these required controls, determine if the contract adequately addresses it:
{chr(10).join(f'- {r["name"]}: {r["description"]}' for r in self.REQUIRED_CONTROLS)}

Contract clauses:
{clauses_text}

Return a JSON array where each item has:
- rule_id: the control identifier
- status: "pass", "fail", or "warning"
- detail: explanation of the finding
- recommendation: what to add or change if status is not "pass"
- clause_id: the relevant clause id if found, or null
"""

        findings = await gemini.generate_json(
            prompt,
            system_instruction="You are a SOC2 compliance expert. Be thorough and specific.",
        )

        return findings if isinstance(findings, list) else [findings]


class ComplianceChecker:
    """Checks contracts against compliance frameworks (GDPR, SOC2).

    Pluggable architecture: add new frameworks by creating a module class
    with a check() method and registering it in self.modules.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()
        self.modules = {
            "gdpr": GDPRModule(),
            "soc2": SOC2Module(),
        }

    async def check_contract(self, contract_id: str, framework: str, org_id: str) -> dict:
        """Run a compliance check on a contract.

        Args:
            contract_id: Contract UUID.
            framework: 'gdpr' or 'soc2'.
            org_id: Organization ID.

        Returns:
            The compliance report dict.
        """
        if framework not in self.modules:
            raise ValueError(f"Unsupported framework: {framework}")

        clauses = (
            self.supabase.table("clauses")
            .select("id, clause_type, content")
            .eq("contract_id", contract_id)
            .eq("org_id", org_id)
            .execute()
        ).data

        module = self.modules[framework]
        findings = await module.check(clauses or [], self.gemini)

        # Calculate overall score
        total = len(findings)
        passed = sum(1 for f in findings if f.get("status") == "pass")
        overall_score = passed / total if total > 0 else 0

        report_id = str(uuid.uuid4())
        report = {
            "id": report_id,
            "org_id": org_id,
            "contract_id": contract_id,
            "framework": framework,
            "overall_score": round(overall_score, 2),
            "findings": findings,
            "checked_at": datetime.utcnow().isoformat(),
        }

        self.supabase.table("compliance_reports").insert(report).execute()

        return report

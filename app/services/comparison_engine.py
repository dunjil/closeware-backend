from anthropic import Anthropic
from app.core.config import settings
from app.models.deal import Deal
from app.models.contract_draft import ContractDraft
from app.models.discrepancy_report import DiscrepancyReport, DiscrepancyItem, DiscrepancyStatus
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json


class ComparisonEngine:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def compare_contract_to_trail(
        self,
        contract_draft: ContractDraft,
        deal: Deal,
        db: Session
    ) -> DiscrepancyReport:
        correspondence_trail = self._format_correspondence(deal.correspondence)
        documents_metadata = self._format_documents(deal.documents)

        prompt = self._build_comparison_prompt(
            contract_draft.content,
            correspondence_trail,
            documents_metadata,
            deal
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        analysis = response.content[0].text
        discrepancies = self._parse_analysis(analysis)

        report = DiscrepancyReport(
            deal_id=deal.id,
            contract_draft_id=contract_draft.id,
            summary={
                "total_items": len(discrepancies),
                "matched": sum(1 for d in discrepancies if d["status"] == "matched"),
                "flagged": sum(1 for d in discrepancies if d["status"] == "flagged"),
                "missing": sum(1 for d in discrepancies if d["status"] == "missing"),
            }
        )
        db.add(report)
        db.flush()

        for disc in discrepancies:
            item = DiscrepancyItem(
                report_id=report.id,
                status=DiscrepancyStatus(disc["status"]),
                category=disc["category"],
                description=disc["description"],
                source_reference=disc.get("source_reference"),
                suggested_fix=disc.get("suggested_fix")
            )
            db.add(item)

        db.commit()
        db.refresh(report)

        return report

    def _format_correspondence(self, correspondence: List) -> str:
        if not correspondence:
            return "No correspondence found."

        output = []
        for item in sorted(correspondence, key=lambda x: x.correspondence_date):
            output.append(f"""
Type: {item.correspondence_type.value}
Date: {item.correspondence_date.strftime('%Y-%m-%d')}
From: {item.sender}
To: {item.recipient}
Subject: {item.subject or 'N/A'}
Content:
{item.content}
---
""")
        return "\n".join(output)

    def _format_documents(self, documents: List) -> str:
        if not documents:
            return "No documents uploaded."

        output = []
        for doc in documents:
            metadata_str = json.dumps(doc.metadata, indent=2) if doc.metadata else "None"
            output.append(f"""
Document: {doc.title}
Type: {doc.document_type.value}
Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d')}
Metadata:
{metadata_str}
---
""")
        return "\n".join(output)

    def _build_comparison_prompt(
        self,
        contract_content: str,
        correspondence: str,
        documents: str,
        deal: Deal
    ) -> str:
        return f"""You are a legal document verification assistant for Closeware, a deal management platform.

Your task is to compare a contract draft against the full negotiation trail (correspondence + documents) and flag any discrepancies.

**Deal Information:**
- Type: {deal.deal_type.value}
- Title: {deal.title}
- Asset Description: {deal.asset_description or 'N/A'}
- Agreed Price: {deal.agreed_price} {deal.currency if deal.currency else ''}
- Parties: {json.dumps(deal.parties) if deal.parties else 'N/A'}

**Correspondence Trail:**
{correspondence}

**Documents:**
{documents}

**Contract Draft:**
{contract_content}

**Instructions:**
Compare the contract draft against the correspondence trail and documents. Produce a structured JSON response with an array of discrepancy items. Each item should have:
- status: "matched", "flagged", or "missing"
- category: The type of term (e.g., "price", "asset_description", "party_name", "closing_date", etc.)
- description: A clear description of what was found, flagged, or missing
- source_reference: (optional) A reference to where in the correspondence/documents this was found or expected
- suggested_fix: (REQUIRED for "flagged" and "missing" status) The exact corrected clause or text that should replace the incorrect/missing portion

Focus on:
1. **Matched**: Terms that appear consistently in correspondence, documents, and the contract
2. **Flagged**: Inconsistencies (e.g., price differs between offer letter and contract, names don't match title documents) - MUST include suggested_fix with the corrected text
3. **Missing**: Terms discussed in correspondence that don't appear in the contract - MUST include suggested_fix with the complete clause to add

Return ONLY valid JSON in this format:
{{
  "discrepancies": [
    {{
      "status": "matched",
      "category": "price",
      "description": "Purchase price of ₦4,450,000,000 matches across all correspondence and contract",
      "source_reference": {{"type": "correspondence", "date": "2026-01-15"}},
      "suggested_fix": null
    }},
    {{
      "status": "flagged",
      "category": "asset_description",
      "description": "Title document shows plot size as 5,000 sqm but contract states 4,800 sqm",
      "source_reference": {{"type": "document", "title": "Certificate of Occupancy"}},
      "suggested_fix": "The property comprises approximately 5,000 square meters, as evidenced by the Certificate of Occupancy dated [date]."
    }},
    {{
      "status": "missing",
      "category": "payment_terms",
      "description": "Email dated 2026-02-10 agreed to 30-day payment terms, but this clause is absent from the contract",
      "source_reference": {{"type": "correspondence", "date": "2026-02-10"}},
      "suggested_fix": "Payment shall be made within thirty (30) days of the execution of this Agreement, as agreed in correspondence dated 2026-02-10."
    }}
  ]
}}
"""

    def _parse_analysis(self, analysis_text: str) -> List[Dict[str, Any]]:
        try:
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = analysis_text[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed.get("discrepancies", [])
        except Exception:
            pass

        return []

from anthropic import Anthropic
from app.core.config import settings
from app.models.deal import Deal
from sqlalchemy.orm import Session
from typing import Dict, Any
import json


class ContractGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def generate_contract(
        self,
        deal: Deal,
        db: Session,
        contract_type: str = "SPA"
    ) -> str:
        """
        Generate a complete contract (SPA, JV Agreement, NDA) from the deal trail.

        Args:
            deal: The Deal object containing all correspondence and documents
            db: Database session
            contract_type: Type of contract to generate (SPA, JV, NDA)

        Returns:
            Generated contract content as string
        """
        correspondence_trail = self._format_correspondence(deal.correspondence)
        documents_metadata = self._format_documents(deal.documents)

        prompt = self._build_generation_prompt(
            correspondence_trail,
            documents_metadata,
            deal,
            contract_type
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=16000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        contract_content = response.content[0].text
        return contract_content

    def regenerate_with_corrections(
        self,
        deal: Deal,
        current_draft: str,
        corrections: str,
        contract_type: str,
        db: Session
    ) -> str:
        """
        Regenerate a contract incorporating user corrections/suggestions.

        Args:
            deal: The Deal object
            current_draft: The current contract draft content
            corrections: User's correction instructions
            contract_type: Type of contract (SPA, JV, NDA)
            db: Database session

        Returns:
            Regenerated contract content as string
        """
        correspondence_trail = self._format_correspondence(deal.correspondence)
        documents_metadata = self._format_documents(deal.documents)

        prompt = f"""You are a legal contract drafting assistant for Closeware, a deal management platform.

You have previously generated a contract draft, and the user has provided corrections/suggestions for improvement.

**Deal Information:**
- Type: {deal.deal_type.value}
- Title: {deal.title}
- Asset Description: {deal.asset_description or 'N/A'}
- Agreed Price: {deal.agreed_price} {deal.currency if deal.currency else ''}
- Parties: {json.dumps(deal.parties) if deal.parties else 'N/A'}

**Correspondence Trail:**
{correspondence_trail}

**Documents:**
{documents_metadata}

**Current Contract Draft:**
{current_draft}

**User Corrections/Suggestions:**
{corrections}

**Instructions:**
Regenerate the contract incorporating the user's corrections and suggestions while:
1. Maintaining all accurate terms from the original draft
2. Implementing the requested changes precisely
3. Ensuring the corrected contract still accurately reflects the negotiation trail and documents
4. Preserving professional legal language and proper structure
5. NOT removing or changing terms that weren't mentioned in the corrections

Generate the complete revised contract now:
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=16000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.content[0].text

    def _format_correspondence(self, correspondence: list) -> str:
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

    def _format_documents(self, documents: list) -> str:
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

    def _build_generation_prompt(
        self,
        correspondence: str,
        documents: str,
        deal: Deal,
        contract_type: str
    ) -> str:
        contract_templates = {
            "SPA": "Share Purchase Agreement (SPA) or Sale and Purchase Agreement",
            "JV": "Joint Venture Agreement",
            "NDA": "Non-Disclosure Agreement"
        }

        contract_name = contract_templates.get(contract_type, "Contract")

        return f"""You are a legal contract drafting assistant for Closeware, a deal management platform.

Your task is to generate a complete, professional {contract_name} based on the full negotiation trail (correspondence + documents).

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

**Instructions:**
Generate a complete, legally sound {contract_name} that:

1. **Accurately reflects all negotiated terms** from the correspondence trail
2. **Incorporates all relevant information** from the uploaded documents (names, plot sizes, license numbers, etc.)
3. **Includes all standard clauses** for this type of agreement:
   - Parties and recitals
   - Definitions
   - Purchase/transaction terms
   - Representations and warranties
   - Conditions precedent
   - Closing provisions
   - Indemnification
   - Governing law and dispute resolution
   - General provisions (notices, amendments, etc.)

4. **Uses precise, professional legal language**
5. **Cross-references source information** where critical (e.g., "as per title document dated...", "as agreed in correspondence dated...")
6. **Flags any missing critical information** in comments within the draft

**Important Guidelines:**
- Every term, price, date, name, and description MUST match what appears in the correspondence or documents
- If there are conflicting terms in the correspondence, use the MOST RECENT agreement
- If critical information is missing, include a placeholder like [TO BE CONFIRMED: payment terms]
- Use the jurisdiction and legal standards appropriate for: {deal.parties.get('buyer', 'the parties') if deal.parties else 'the parties'}
- Format the contract professionally with proper numbering and sections

Generate the complete contract now:
"""

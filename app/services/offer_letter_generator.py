"""
Offer Letter Generation Service
Generates professional offer/counter-offer letters on company letterhead using AI.
"""
from typing import Optional
from anthropic import Anthropic
from datetime import datetime

from app.models.deal import Deal
from app.models.organization import Organization
from app.core.config import settings


class OfferLetterGenerator:
    """Generate professional business letters for deal negotiations"""

    def __init__(self):
        self.client = None
        self.model = "claude-sonnet-4-20250514"

    def _get_client(self):
        """Lazy initialization of Anthropic client"""
        if self.client is None:
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self.client

    def generate_offer_letter(
        self,
        deal: Deal,
        organization: Organization,
        letter_type: str = "offer",  # "offer" or "counter_offer"
        proposed_price: Optional[float] = None,
        proposed_terms: Optional[str] = None,
        additional_notes: Optional[str] = None
    ) -> str:
        """
        Generate a professional offer or counter-offer letter.

        Args:
            deal: Deal object with asset details and parties
            organization: Organization sending the letter
            letter_type: "offer" or "counter_offer"
            proposed_price: Proposed purchase price
            proposed_terms: Any specific terms to include
            additional_notes: Additional context for the letter

        Returns:
            Formatted letter on company letterhead
        """

        # Build context for AI
        current_date = datetime.now().strftime("%B %d, %Y")

        context = f"""
LETTER TYPE: {letter_type.upper().replace('_', ' ')}

COMPANY INFORMATION:
Company Name: {organization.name}
Company Address: {organization.address or 'Not provided'}

DEAL INFORMATION:
Asset Type: {deal.asset_type}
Asset Description: {deal.asset_description}
Seller/Counterparty: {deal.seller_name or 'To be determined'}
Seller Contact: {deal.seller_contact or 'Not provided'}

PROPOSED TERMS:
Proposed Price: {self._format_currency(proposed_price, deal.currency) if proposed_price else deal.agreed_price or 'To be negotiated'}
Currency: {deal.currency or 'USD'}
Payment Terms: {proposed_terms or deal.payment_terms or 'To be discussed'}

ADDITIONAL CONTEXT:
{additional_notes or 'Standard commercial transaction'}

PREVIOUS CORRESPONDENCE:
{self._get_correspondence_summary(deal) if deal.correspondence else 'First contact'}
"""

        prompt = f"""You are drafting a professional business letter for a corporate asset acquisition.

Write a formal {letter_type.replace('_', ' ')} letter on behalf of {organization.name}.

CONTEXT:
{context}

INSTRUCTIONS:
1. Use professional, formal business language
2. Include proper letterhead formatting with company name and address
3. Date the letter {current_date}
4. Address it to the seller/counterparty
5. Clearly state the proposed price and key terms
6. {"This is an initial offer - be courteous and express interest" if letter_type == "offer" else "This is a counter-offer - reference previous discussions politely"}
7. Include next steps and contact information
8. Sign off professionally (leave signature line for authorized signatory)
9. Keep it concise (1-2 pages max)
10. Use clear section headings where appropriate

FORMAT:
- Start with letterhead (company name, address)
- Date
- Recipient details
- Subject line
- Letter body with clear paragraphs
- Professional closing
- Signature block

Generate the complete letter now, ready to be reviewed and signed."""

        response = self._get_client().messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        letter_content = response.content[0].text

        return letter_content

    def generate_nda_request_letter(
        self,
        deal: Deal,
        organization: Organization,
        counterparty_name: str,
        evaluation_purpose: str
    ) -> str:
        """
        Generate a letter requesting NDA execution for deal evaluation.
        """
        current_date = datetime.now().strftime("%B %d, %Y")

        prompt = f"""You are drafting a professional letter requesting execution of a Non-Disclosure Agreement (NDA).

SENDER: {organization.name}
RECIPIENT: {counterparty_name}
DATE: {current_date}
PURPOSE: {evaluation_purpose}

DEAL CONTEXT:
Asset Type: {deal.asset_type}
Description: {deal.asset_description}

Write a professional letter that:
1. Expresses interest in evaluating the opportunity
2. Explains why an NDA is required (due diligence, confidential information exchange)
3. States that the NDA template will be provided separately
4. Requests timely execution to proceed with evaluation
5. Maintains a collaborative, professional tone

Keep it brief (1 page) and focused on moving the process forward."""

        response = self._get_client().messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def _format_currency(self, amount: float, currency: str = "USD") -> str:
        """Format currency for letter display"""
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "NGN": "₦",
            "AED": "د.إ", "ZAR": "R", "KES": "KSh", "GHS": "₵",
            "EGP": "E£", "SAR": "﷼", "QAR": "﷼"
        }
        symbol = symbols.get(currency, currency + " ")
        return f"{symbol}{amount:,.2f}"

    def _get_correspondence_summary(self, deal: Deal) -> str:
        """Summarize previous correspondence for context"""
        if not deal.correspondence:
            return "No previous correspondence"

        recent = deal.correspondence[-3:]  # Last 3 items
        summary = []
        for item in recent:
            summary.append(f"- {item.correspondence_type}: {item.subject or 'Discussion'} ({item.created_at.strftime('%b %d')})")

        return "\n".join(summary)


# Singleton instance
offer_letter_generator = OfferLetterGenerator()

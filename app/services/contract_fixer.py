from anthropic import Anthropic
from app.core.config import settings
from app.models.contract_draft import ContractDraft
from app.models.discrepancy_report import DiscrepancyItem
from sqlalchemy.orm import Session


class ContractFixer:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def apply_single_fix(
        self,
        contract_draft: ContractDraft,
        discrepancy_item: DiscrepancyItem,
        db: Session
    ) -> str:
        """
        Apply a single suggested fix to a contract draft.

        Args:
            contract_draft: The current contract draft
            discrepancy_item: The discrepancy item with the suggested fix
            db: Database session

        Returns:
            Updated contract content with the fix applied
        """
        if not discrepancy_item.suggested_fix:
            raise ValueError("Discrepancy item has no suggested fix")

        prompt = self._build_fix_application_prompt(
            contract_draft.content,
            discrepancy_item
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

        return response.content[0].text

    def apply_multiple_fixes(
        self,
        contract_draft: ContractDraft,
        discrepancy_items: list[DiscrepancyItem],
        db: Session
    ) -> str:
        """
        Apply multiple suggested fixes to a contract draft at once.

        Args:
            contract_draft: The current contract draft
            discrepancy_items: List of discrepancy items with suggested fixes
            db: Database session

        Returns:
            Updated contract content with all fixes applied
        """
        fixes_to_apply = [
            item for item in discrepancy_items
            if item.suggested_fix and item.status.value in ['flagged', 'missing']
        ]

        if not fixes_to_apply:
            raise ValueError("No fixes to apply")

        prompt = self._build_batch_fix_prompt(
            contract_draft.content,
            fixes_to_apply
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

        return response.content[0].text

    def _build_fix_application_prompt(
        self,
        contract_content: str,
        discrepancy_item: DiscrepancyItem
    ) -> str:
        action = "replace the incorrect text with" if discrepancy_item.status.value == "flagged" else "add"

        return f"""You are a legal contract editing assistant for Closeware.

Your task is to apply a single correction to a contract draft.

**Current Contract:**
{contract_content}

**Issue Found:**
Category: {discrepancy_item.category}
Status: {discrepancy_item.status.value}
Description: {discrepancy_item.description}

**Correction to Apply:**
{discrepancy_item.suggested_fix}

**Instructions:**
{"1. Locate the incorrect text described in the issue" if discrepancy_item.status.value == "flagged" else "1. Identify the most appropriate location to insert this clause"}
2. {action.capitalize()} the suggested fix
3. Maintain all other contract content exactly as-is
4. Preserve all formatting, numbering, and structure
5. Ensure the fix integrates smoothly with surrounding text

Return ONLY the complete updated contract with the fix applied. Do not include any explanations or commentary.
"""

    def _build_batch_fix_prompt(
        self,
        contract_content: str,
        discrepancy_items: list[DiscrepancyItem]
    ) -> str:
        fixes_list = []
        for idx, item in enumerate(discrepancy_items, 1):
            fixes_list.append(f"""
Fix #{idx}:
- Category: {item.category}
- Status: {item.status.value}
- Issue: {item.description}
- Correction: {item.suggested_fix}
""")

        return f"""You are a legal contract editing assistant for Closeware.

Your task is to apply multiple corrections to a contract draft in a single pass.

**Current Contract:**
{contract_content}

**Corrections to Apply:**
{''.join(fixes_list)}

**Instructions:**
1. Apply ALL corrections listed above to the contract
2. For "flagged" items: find and replace the incorrect text
3. For "missing" items: insert the clause in the most appropriate location
4. Maintain all other contract content exactly as-is
5. Preserve all formatting, numbering, and structure
6. Ensure all fixes integrate smoothly with surrounding text
7. If multiple fixes affect the same section, apply them coherently

Return ONLY the complete updated contract with all fixes applied. Do not include any explanations or commentary.
"""

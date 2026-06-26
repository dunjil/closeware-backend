from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"  # Not yet finalized
    OPEN = "open"  # Sent to customer, awaiting payment
    PAID = "paid"  # Payment received
    VOID = "void"  # Cancelled
    UNCOLLECTIBLE = "uncollectible"  # Write-off


class Invoice(Base):
    """
    Billing invoice for a subscription period.
    Generated at end of billing period with base + usage charges.
    """
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Invoice details
    invoice_number = Column(String, unique=True, nullable=False, index=True)  # "INV-2026-001"
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)

    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Amounts (in NGN)
    subtotal = Column(Numeric(precision=12, scale=2), nullable=False)  # Before tax
    tax_rate = Column(Numeric(precision=5, scale=2), default=7.5)  # 7.5% VAT in Nigeria
    tax_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    total = Column(Numeric(precision=12, scale=2), nullable=False)  # Subtotal + tax

    # Line items breakdown
    line_items = Column(JSONB, nullable=False)
    # Example: [
    #   {"description": "Pro Subscription (Monthly)", "quantity": 1, "unit_price": 150000, "amount": 150000},
    #   {"description": "Additional deals (4 deals)", "quantity": 4, "unit_price": 50000, "amount": 200000}
    # ]

    # Payment tracking
    payment_due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)  # "bank_transfer", "paystack", etc.

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    organization = relationship("Organization")

    @staticmethod
    def generate_invoice_number(db):
        """Generate unique invoice number: INV-YYYY-NNN"""
        from sqlalchemy import func
        year = datetime.utcnow().year
        prefix = f"INV-{year}-"

        # Get last invoice number for this year
        last_invoice = (
            db.query(Invoice)
            .filter(Invoice.invoice_number.like(f"{prefix}%"))
            .order_by(Invoice.invoice_number.desc())
            .first()
        )

        if last_invoice:
            last_num = int(last_invoice.invoice_number.split("-")[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"

    def calculate_totals(self):
        """Calculate subtotal, tax, and total from line items"""
        self.subtotal = sum(item["amount"] for item in self.line_items)
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount

    def mark_as_paid(self, payment_method: str = None):
        """Mark invoice as paid"""
        self.status = InvoiceStatus.PAID
        self.paid_at = datetime.utcnow()
        if payment_method:
            self.payment_method = payment_method

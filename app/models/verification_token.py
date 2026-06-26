from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid
import enum
from app.db.base import Base


class TokenType(str, enum.Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    token_type = Column(Enum(TokenType), nullable=False)

    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def is_valid(self) -> bool:
        """Check if token is valid (not expired, not used)"""
        return (
            self.used_at is None and
            self.expires_at > datetime.utcnow()
        )

    def mark_used(self):
        """Mark token as used"""
        self.used_at = datetime.utcnow()

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token"""
        return str(uuid.uuid4())

    @staticmethod
    def get_expiry(token_type: TokenType) -> datetime:
        """Get expiry time based on token type"""
        if token_type == TokenType.EMAIL_VERIFICATION:
            return datetime.utcnow() + timedelta(hours=24)  # 24 hours for email verification
        elif token_type == TokenType.PASSWORD_RESET:
            return datetime.utcnow() + timedelta(hours=1)  # 1 hour for password reset
        return datetime.utcnow() + timedelta(hours=24)

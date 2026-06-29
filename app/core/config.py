from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ANTHROPIC_API_KEY: str
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    FRONTEND_URL: str = "http://localhost:3000"  # Used for email links
    MAILERSEND_API_KEY: str = ""  # MailerSend API key for sending emails
    FROM_EMAIL: str = "noreply@closeware.com"
    FROM_NAME: str = "Closeware"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

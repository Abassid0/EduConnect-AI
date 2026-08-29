from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    API_VERSION: str = "v1"
    DEBUG: bool = False
    PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://educonnect:educonnect@db:5432/educonnect"
    REDIS_URL: str = "redis://redis:6379/0"

    WA_PHONE_NUMBER_ID: str = ""
    WA_BUSINESS_ACCOUNT_ID: str = ""
    WA_ACCESS_TOKEN: str = ""
    WA_VERIFY_TOKEN: str = ""
    WA_APP_SECRET: str = ""
    WA_API_VERSION: str = "v21.0"

    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    PAYSTACK_CALLBACK_URL: str = "https://educonnect.ai/payment/callback"

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "educonnect-receipts"
    AWS_REGION: str = "eu-west-1"

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = ""

    ANTHROPIC_API_KEY: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    @property
    def wa_api_base(self) -> str:
        return f"https://graph.facebook.com/{self.WA_API_VERSION}/{self.WA_PHONE_NUMBER_ID}"


settings = Settings()

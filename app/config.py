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
    PAYSTACK_CALLBACK_URL: str = "https://educonnect-ai-production.up.railway.app/api/v1/payments/callback"

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "educonnect-receipts"
    AWS_REGION: str = "eu-west-1"

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- School term & fee policy -------------------------------------
    # Which term new registrations are billed for. Update at the start of
    # each term: first | second | third
    CURRENT_TERM: str = "first"
    # e.g. "2025/2026". Left blank, it is derived from today's date.
    CURRENT_ACADEMIC_YEAR: str = ""
    # How many days a parent has to settle a term invoice in full.
    INVOICE_DUE_DAYS: int = 21
    # School-wide instalment offer. Every parent is offered the same split.
    INSTALLMENT_COUNT: int = 3
    INSTALLMENT_FREQUENCY: str = "monthly"  # weekly | biweekly | monthly

    CORS_ORIGINS: str = ""

    ANTHROPIC_API_KEY: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    WHATSAPP_ADMIN_PHONE: str = ""

    ADMIN_DASHBOARD_URL: str = ""

    @property
    def wa_api_base(self) -> str:
        return f"https://graph.facebook.com/{self.WA_API_VERSION}/{self.WA_PHONE_NUMBER_ID}"

    @property
    def academic_year(self) -> str:
        """The configured academic year, or one derived from today's date.

        Nigerian school years run September to July, so a date in or after
        September belongs to year/year+1, and anything earlier belongs to
        the session that started the previous September.
        """
        if self.CURRENT_ACADEMIC_YEAR:
            return self.CURRENT_ACADEMIC_YEAR
        from datetime import date

        today = date.today()
        start = today.year if today.month >= 9 else today.year - 1
        return f"{start}/{start + 1}"


settings = Settings()

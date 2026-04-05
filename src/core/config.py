from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Настройки приложения.
    Pydantic автоматически загружает значения из .env файла.
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # Какой файл читать
        env_file_encoding="utf-8",  # Кодировка
        case_sensitive=False,  # Имена переменных не чувствительны к регистру
        extra="ignore"  # Игнорировать лишние переменные в .env
    )

    # ────────────────────────────────────────────────────────────────────────────
    # Application
    # ────────────────────────────────────────────────────────────────────────────
    app_name: str = Field(default="Production Control System", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    # ────────────────────────────────────────────────────────────────────────────
    # Database
    # ────────────────────────────────────────────────────────────────────────────
    database_url: str = Field(alias="DATABASE_URL")
    database_sync_url: str = Field(alias="DATABASE_SYNC_URL")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Проверяет, что URL базы данных корректен"""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must start with postgresql+asyncpg://")
        return v

    # ────────────────────────────────────────────────────────────────────────────
    # Redis
    # ────────────────────────────────────────────────────────────────────────────
    redis_url: str = Field(alias="REDIS_URL")
    redis_cache_db: int = Field(default=0, alias="REDIS_CACHE_DB")
    redis_celery_backend_db: int = Field(default=1, alias="REDIS_CELERY_BACKEND_DB")

    @property
    def redis_cache_url(self) -> str:
        """URL для кэша (с нужной базой данных)"""
        return f"{self.redis_url}/{self.redis_cache_db}"

    @property
    def redis_celery_url(self) -> str:
        """URL для Celery backend (с нужной базой данных)"""
        return f"{self.redis_url}/{self.redis_celery_backend_db}"

    # ────────────────────────────────────────────────────────────────────────────
    # RabbitMQ / Celery Broker
    # ────────────────────────────────────────────────────────────────────────────
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")

    # ────────────────────────────────────────────────────────────────────────────
    # MinIO (S3-compatible Storage)
    # ────────────────────────────────────────────────────────────────────────────
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_bucket_reports: str = Field(default="reports", alias="MINIO_BUCKET_REPORTS")
    minio_bucket_exports: str = Field(default="exports", alias="MINIO_BUCKET_EXPORTS")
    minio_bucket_imports: str = Field(default="imports", alias="MINIO_BUCKET_IMPORTS")

    @property
    def minio_config(self) -> dict:
        """Удобный словарь с конфигурацией MinIO"""
        return {
            "endpoint": self.minio_endpoint,
            "access_key": self.minio_access_key,
            "secret_key": self.minio_secret_key,
            "secure": self.minio_secure,
        }

    # ────────────────────────────────────────────────────────────────────────────
    # Security
    # ────────────────────────────────────────────────────────────────────────────
    secret_key: str = Field(alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # ────────────────────────────────────────────────────────────────────────────
    # Caching TTL
    # ────────────────────────────────────────────────────────────────────────────
    cache_ttl_dashboard: int = Field(default=300, alias="CACHE_TTL_DASHBOARD")
    cache_ttl_batch_list: int = Field(default=60, alias="CACHE_TTL_BATCH_LIST")
    cache_ttl_batch_detail: int = Field(default=600, alias="CACHE_TTL_BATCH_DETAIL")
    cache_ttl_batch_stats: int = Field(default=300, alias="CACHE_TTL_BATCH_STATS")

    # ────────────────────────────────────────────────────────────────────────────
    # Webhook
    # ────────────────────────────────────────────────────────────────────────────
    webhook_retry_count: int = Field(default=3, alias="WEBHOOK_RETRY_COUNT")
    webhook_timeout: int = Field(default=10, alias="WEBHOOK_TIMEOUT")
    webhook_retry_delay: int = Field(default=900, alias="WEBHOOK_RETRY_DELAY")  # 15 минут

    # ────────────────────────────────────────────────────────────────────────────
    # File Storage
    # ────────────────────────────────────────────────────────────────────────────
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_upload_size: int = Field(default=10485760, alias="MAX_UPLOAD_SIZE")  # 10 MB
    file_retention_days: int = Field(default=30, alias="FILE_RETENTION_DAYS")

    # ────────────────────────────────────────────────────────────────────────────
    # API
    # ────────────────────────────────────────────────────────────────────────────
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS"
    )
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")  # секунд


# Создаём глобальный экземпляр настроек
# При первом импорте читает .env и валидирует всё
settings = Settings()


# Функция для проверки настроек (можно вызвать при запуске)
def validate_settings() -> None:
    """Проверяет, что все необходимые настройки корректны."""
    required_vars = [
        ("DATABASE_URL", settings.database_url),
        ("SECRET_KEY", settings.secret_key),
    ]

    missing = [name for name, value in required_vars if not value]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please check your .env file"
        )

    if settings.secret_key == "your-super-secret-key-change-in-production":
        print("⚠️  WARNING: Using default SECRET_KEY! Change it in production!")

    print("✅ Settings validation passed")
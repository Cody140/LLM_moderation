from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Moderation Service"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    queue_maxsize: int = 1000
    worker_count: int = 2

    llm_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = 30.0
    llm_max_concurrency: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
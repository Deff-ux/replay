from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Replay"
    version: str = "2.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8446
    database_url: str = "/data/test.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480
    artifacts_dir: str = "/data/artifacts"
    artifact_retention_days: int = 30
    max_artifact_size_mb: int = 100
    seeds_dir: str = "/data/seeds"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    openproject_url: str | None = None
    openproject_api_key: str | None = None
    frontend_dist_dir: str = "/app/frontend/dist"

    environments_config_path: str = "/app/backend/config/environments.yaml"

    class Config:
        env_file = ".env"
        env_prefix = "REPLAY_"


settings = Settings()

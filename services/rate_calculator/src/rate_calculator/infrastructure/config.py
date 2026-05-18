from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str = "audit.events"
    RABBITMQ_ROUTING_KEY: str = "calculation.completed"
    OUTBOX_RELAY_INTERVAL_SECONDS: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

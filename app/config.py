from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, lidas de variáveis de ambiente / arquivo .env."""

    database_url: str = "sqlite:///./data.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

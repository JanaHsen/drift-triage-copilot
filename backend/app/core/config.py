from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str
    redis_url: str
    openai_api_key: str = ""
    langsmith_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_project: str = "drift-triage-copilot"


settings = Settings()

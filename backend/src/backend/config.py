from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    github_client_id: str
    github_client_secret: str
    github_callback_url: str
    github_app_slug: str
    github_app_id: str
    github_private_key_path: str
    session_secret: str
    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore",
    )
    database_url: str
    
settings = Settings()
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # Add any environment-specific configurations here
    CHROME_DRIVER_ARGS: list = [
        "--headless"
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080"
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()
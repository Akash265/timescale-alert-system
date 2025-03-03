# config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Database settings
    TIMESCALE_DB_PASSWORD: str = os.getenv("TIMESCALE_DB_PASSWORD")
    TIMESCALE_DB_HOST: str = os.getenv("TIMESCALE_DB_HOST")
    TIMESCALE_DB_PORT: str = os.getenv("TIMESCALE_DB_PORT")
    TIMESCALE_DB_NAME: str = os.getenv("TIMESCALE_DB_NAME")
    TIMESCALE_DB_USER: str = os.getenv("TIMESCALE_DB_USER")
    
    # Construct database URL
    @property
    def DB_CONNECTION(self) -> str:
        return f"postgres://{self.TIMESCALE_DB_USER}:{self.TIMESCALE_DB_PASSWORD}@{self.TIMESCALE_DB_HOST}:{self.TIMESCALE_DB_PORT}/{self.TIMESCALE_DB_NAME}?sslmode=require"
    
    # Email settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    
    # Twilio settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER")
    
    # Alert settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
    RETRY_DELAY_MINUTES: int = int(os.getenv("RETRY_DELAY_MINUTES", "10"))
    
    class Config:
        env_file = ".env"


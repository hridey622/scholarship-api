"""Application configuration using Pydantic Settings"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Bhashini API
    bhashini_url: str = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
    bhashini_key: str = "WQkv6JtDJu1ZhB6LWDL3AwmAmlL8daJHSTAmXHgVaR43ZCDfx3SCbbayvE1zlY_z"
    
    # Ollama LLM
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    # Session settings
    session_timeout_minutes: int = 30
    
    # Form URL
    form_url: str = "https://scholarships.gov.in/scholarshipEligibility/"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

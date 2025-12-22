"""Configuration management for the Resume Job Matcher."""
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration."""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # LLM Provider
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    # OpenRouter
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4-turbo-preview")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI provider")
        
        if cls.LLM_PROVIDER == "openrouter" and not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is required when using OpenRouter provider")
        
        if cls.LLM_PROVIDER not in ["openai", "openrouter"]:
            errors.append(f"Invalid LLM_PROVIDER: {cls.LLM_PROVIDER}. Must be 'openai' or 'openrouter'")
        
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration. Please check your .env file.")
        
        logger.info(f"Configuration validated successfully (LLM Provider: {cls.LLM_PROVIDER})")


# Configure logging
logger.remove()  # Remove default handler
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=Config.LOG_LEVEL
)
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"
    
    @property
    def connection_string(self) -> str:
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"
        )

def get_database_config() -> DatabaseConfig:
    """Get database configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "local")
    
    if env == "local":
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "arxiv_automation"),
            username=os.getenv("DB_USER", "arxiv_user"),
            password=os.getenv("DB_PASSWORD", "dev_password"),
            ssl_mode="prefer"
        )
    elif env == "cloud":
        return DatabaseConfig(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME"),
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            ssl_mode="require"
        )
    else:
        raise ValueError(f"Unknown environment: {env}")

@dataclass
class AppConfig:
    database: DatabaseConfig
    debug: bool = False
    log_level: str = "INFO"
    openai_api_key: Optional[str] = None
    
def get_app_config() -> AppConfig:
    """Get complete application configuration."""
    return AppConfig(
        database=get_database_config(),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
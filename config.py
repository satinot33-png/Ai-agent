"""
Configuration management for AI Agent.

This module provides configuration handling with:
- Environment variable loading
- Configuration validation
- Default values
- Config file support (.env)
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# ============================================================================
# LOAD ENVIRONMENT
# ============================================================================

def load_env_files(env_paths: Optional[list[str]] = None) -> None:
    """
    Load environment variables from .env files.
    
    Args:
        env_paths: List of paths to .env files. If None, uses defaults.
    """
    if env_paths is None:
        env_paths = [
            ".env",
            ".env.local",
            ".env.example"
        ]
    
    for path in env_paths:
        env_file = Path(path)
        if env_file.exists():
            load_dotenv(env_file, override=False)
            logger.debug(f"Loaded environment from {path}")


# ============================================================================
# CONFIGURATION SCHEMA
# ============================================================================

@dataclass
class APIConfig:
    """API configuration."""
    base_url: str = ""
    key: str = ""
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class ProviderConfig:
    """LLM Provider configuration."""
    type: str = "text"  # "openai", "gemini", "ollama", "text"
    model: str = "default"
    api: APIConfig = field(default_factory=APIConfig)
    
    # Provider-specific options
    temperature: float = 0.7
    max_tokens: int = 500


@dataclass
class StorageConfig:
    """Message storage configuration."""
    type: str = "file"  # "file", "memory", "sqlite"
    path: str = "./agent_data"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    retention_days: Optional[int] = None


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB


@dataclass
class AgentConfig:
    """Complete agent configuration."""
    agent_id: str = ""
    name: str = "AI Agent"
    description: str = ""
    
    # Core configuration
    max_message_length: int = 10000
    debug_mode: bool = False
    
    # Sub-configurations
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        load_env_files()
        
        return cls(
            agent_id=os.getenv("AGENT_ID", ""),
            name=os.getenv("AGENT_NAME", "AI Agent"),
            description=os.getenv("AGENT_DESCRIPTION", ""),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "10000")),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            provider=ProviderConfig(
                type=os.getenv("PROVIDER_TYPE", "text"),
                model=os.getenv("PROVIDER_MODEL", "default"),
                api=APIConfig(
                    base_url=os.getenv("API_BASE_URL", ""),
                    key=os.getenv("API_KEY", ""),
                    timeout=float(os.getenv("API_TIMEOUT", "30.0")),
                    max_retries=int(os.getenv("API_MAX_RETRIES", "3")),
                ),
                temperature=float(os.getenv("PROVIDER_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("PROVIDER_MAX_TOKENS", "500")),
            ),
            storage=StorageConfig(
                type=os.getenv("STORAGE_TYPE", "file"),
                path=os.getenv("STORAGE_PATH", "./agent_data"),
                max_file_size=int(os.getenv("STORAGE_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
                retention_days=int(os.getenv("STORAGE_RETENTION_DAYS", "-1")) if os.getenv("STORAGE_RETENTION_DAYS") else None,
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                file=os.getenv("LOG_FILE", None),
                max_file_size=int(os.getenv("LOG_FILE_MAX_SIZE", str(10 * 1024 * 1024))),
            ),
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AgentConfig":
        """Load configuration from dictionary."""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "max_message_length": self.max_message_length,
            "debug_mode": self.debug_mode,
            "provider": {
                "type": self.provider.type,
                "model": self.provider.model,
                "temperature": self.provider.temperature,
                "max_tokens": self.provider.max_tokens,
            },
            "storage": {
                "type": self.storage.type,
                "path": self.storage.path,
                "max_file_size": self.storage.max_file_size,
                "retention_days": self.storage.retention_days,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
                "max_file_size": self.logging.max_file_size,
            },
        }
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.name:
            return False, "Agent name is required"
        
        if self.max_message_length <= 0:
            return False, "Max message length must be positive"
        
        if self.provider.type not in ("openai", "gemini", "ollama", "text"):
            return False, f"Unknown provider type: {self.provider.type}"
        
        if self.provider.type in ("openai", "gemini"):
            if not self.provider.api.key:
                return False, f"{self.provider.type} provider requires API_KEY"
        
        if self.storage.type not in ("file", "memory", "sqlite", "jsonl"):
            return False, f"Unknown storage type: {self.storage.type}"
        
        if self.logging.level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            return False, f"Invalid log level: {self.logging.level}"
        
        return True, None


# ============================================================================
# CONFIGURATION UTILITIES
# ============================================================================

def get_config(override: Optional[Dict[str, Any]] = None) -> AgentConfig:
    """
    Get agent configuration.
    
    Args:
        override: Dictionary of overrides to apply
    
    Returns:
        AgentConfig instance
    """
    config = AgentConfig.from_env()
    
    if override:
        for key, value in override.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return config


def validate_config(config: Optional[AgentConfig] = None) -> None:
    """
    Validate configuration and raise error if invalid.
    
    Args:
        config: AgentConfig to validate. If None, loads from env.
    
    Raises:
        ValueError: If configuration is invalid
    """
    if config is None:
        config = AgentConfig.from_env()
    
    is_valid, error_message = config.validate()
    if not is_valid:
        raise ValueError(f"Configuration validation failed: {error_message}")

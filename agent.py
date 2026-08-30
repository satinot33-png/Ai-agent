"""
Standalone AI Agent API with multi-agent coordination support.

This module provides a clean, extensible architecture for building AI agents
that can operate independently or as part of a coordinated network.

Key features:
- Async-first design for concurrent message processing
- Pluggable LLM providers and message storage backends
- Structured error handling and resilience patterns
- Multi-agent registry for agent discovery and coordination
- Extensible middleware/interceptor system
- Type-safe request/response models
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Awaitable
from uuid import uuid4


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logger(name: str, debug: bool = False) -> logging.Logger:
    """Configure logging for the agent."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    return logger


logger = setup_logger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class AgentStatus(Enum):
    """Agent operational status."""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    OFFLINE = "offline"
    INITIALIZING = "initializing"


class ErrorCode(Enum):
    """Standardized error codes for agent operations."""
    VALIDATION_ERROR = "validation_error"
    CONFIG_ERROR = "config_error"
    PROVIDER_ERROR = "provider_error"
    STORAGE_ERROR = "storage_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for AI Agent."""
    
    agent_id: str = field(default_factory=lambda: str(uuid4()))
    agent_name: str = "AI Agent"
    description: str = ""
    
    # LLM & API Configuration
    api_base_url: str = ""
    api_key: str = ""
    provider_type: str = "text"  # "openai", "gemini", "local", "text"
    model_name: str = "default"
    
    # Behavior Configuration
    max_message_length: int = 10000
    timeout_seconds: float = 30.0
    max_retries: int = 3
    debug_mode: bool = False
    
    # Storage Configuration
    storage_type: str = "file"  # "file", "memory", "database"
    storage_path: str = "./agent_data"
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            agent_id=os.getenv("AGENT_ID", str(uuid4())),
            agent_name=os.getenv("AGENT_NAME", "AI Agent"),
            description=os.getenv("AGENT_DESCRIPTION", ""),
            api_base_url=os.getenv("API_BASE_URL", ""),
            api_key=os.getenv("API_KEY", ""),
            provider_type=os.getenv("PROVIDER_TYPE", "text"),
            model_name=os.getenv("MODEL_NAME", "default"),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "10000")),
            timeout_seconds=float(os.getenv("TIMEOUT_SECONDS", "30.0")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            storage_type=os.getenv("STORAGE_TYPE", "file"),
            storage_path=os.getenv("STORAGE_PATH", "./agent_data"),
        )
    
    def validate(self) -> bool:
        """Validate critical configuration."""
        if not self.agent_name:
            logger.error("Agent name is required")
            return False
        if self.max_message_length <= 0:
            logger.error("Max message length must be positive")
            return False
        if self.timeout_seconds <= 0:
            logger.error("Timeout must be positive")
            return False
        return True


@dataclass
class AgentRequest:
    """Structured request to an agent."""
    
    message_id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling non-serializable types."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    
    message_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling non-serializable types."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.error_code:
            data['error_code'] = self.error_code.value
        return data


class AgentError(Exception):
    """Base exception for agent errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ============================================================================
# ABSTRACT INTERFACES
# ============================================================================

class MessageStore(ABC):
    """Abstract interface for message storage backends."""
    
    @abstractmethod
    async def save(self, agent_id: str, request: AgentRequest, response: AgentResponse) -> None:
        """Save a message exchange."""
        pass
    
    @abstractmethod
    async def get_history(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve message history."""
        pass
    
    @abstractmethod
    async def clear(self, agent_id: str) -> None:
        """Clear all messages for an agent."""
        pass


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    async def generate_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> str:
        """Generate a response to a message."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass


# ============================================================================
# DEFAULT IMPLEMENTATIONS
# ============================================================================

class FileMessageStore(MessageStore):
    """File-based message storage implementation."""
    
    def __init__(self, storage_path: str = "./agent_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(f"{__name__}.FileMessageStore")
    
    def _get_agent_file(self, agent_id: str) -> Path:
        """Get the file path for an agent's messages."""
        return self.storage_path / f"{agent_id}_messages.jsonl"
    
    async def save(self, agent_id: str, request: AgentRequest, response: AgentResponse) -> None:
        """Save a message exchange to file."""
        try:
            agent_file = self._get_agent_file(agent_id)
            entry = {
                "request": request.to_dict(),
                "response": response.to_dict(),
            }
            
            with open(agent_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            self.logger.debug(f"Saved message {request.message_id} for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    async def get_history(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve message history from file."""
        try:
            agent_file = self._get_agent_file(agent_id)
            if not agent_file.exists():
                return []
            
            messages = []
            with open(agent_file, 'r') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
            
            # Apply offset and limit
            return messages[offset:offset + limit]
        except Exception as e:
            self.logger.error(f"Failed to retrieve history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    async def clear(self, agent_id: str) -> None:
        """Clear all messages for an agent."""
        try:
            agent_file = self._get_agent_file(agent_id)
            if agent_file.exists():
                agent_file.unlink()
            self.logger.info(f"Cleared history for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )


class SimpleTextProvider(LLMProvider):
    """Simple text-based provider (echo with prefix)."""
    
    def __init__(self, agent_name: str = "AI Agent"):
        self.agent_name = agent_name
        self.logger = setup_logger(f"{__name__}.SimpleTextProvider")
    
    async def generate_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> str:
        """Generate a simple text response."""
        # Simulate async processing
        await asyncio.sleep(0.01)
        return f"{self.agent_name}: Received message - {message}"
    
    async def health_check(self) -> bool:
        """Simple provider is always healthy."""
        return True


# ============================================================================
# CORE AI AGENT
# ============================================================================

class AIAgent:
    """
    Standalone AI Agent with async support and extensibility.
    
    This agent can operate independently or be registered with an AgentRegistry
    for multi-agent coordination.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        provider: Optional[LLMProvider] = None,
        store: Optional[MessageStore] = None
    ):
        """
        Initialize the AI Agent.
        
        Args:
            config: Agent configuration. If None, loads from environment.
            provider: LLM provider. If None, uses SimpleTextProvider.
            store: Message storage backend. If None, uses FileMessageStore.
        
        Raises:
            AgentError: If configuration validation fails.
        """
        self.config = config or AgentConfig.from_env()
        
        if not self.config.validate():
            raise AgentError(
                "Invalid agent configuration",
                error_code=ErrorCode.CONFIG_ERROR
            )
        
        self.provider = provider or SimpleTextProvider(self.config.agent_name)
        self.store = store or FileMessageStore(self.config.storage_path)
        
        self.status = AgentStatus.INITIALIZING
        self.logger = setup_logger(
            f"{__name__}.{self.config.agent_id}",
            debug=self.config.debug_mode
        )
        
        # Middleware/interceptors
        self._pre_processors: List[Callable[[AgentRequest], Awaitable[AgentRequest]]] = []
        self._post_processors: List[Callable[[AgentResponse], Awaitable[AgentResponse]]] = []
        
        self.logger.info(
            f"AI Agent '{self.config.agent_name}' ({self.config.agent_id}) initialized"
        )
        self.status = AgentStatus.IDLE
    
    # ========================================================================
    # Core Message Processing
    # ========================================================================
    
    async def respond(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an incoming message and generate a response.
        
        Args:
            message: The input message to process.
            metadata: Optional metadata (user_id, session_id, etc.).
        
        Returns:
            Response string from the agent.
        
        Raises:
            AgentError: If message validation or processing fails.
        """
        request = AgentRequest(
            content=message,
            metadata=metadata or {}
        )
        
        response = await self.process_request(request)
        
        if response.success:
            return response.content
        else:
            raise AgentError(
                response.error_message or "Unknown error",
                error_code=response.error_code or ErrorCode.UNKNOWN_ERROR
            )
    
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Process a structured request.
        
        Args:
            request: Structured agent request.
        
        Returns:
            Structured agent response.
        """
        response = AgentResponse(request_id=request.message_id)
        
        try:
            # Validate input
            if not isinstance(request.content, str):
                raise AgentError(
                    f"Message must be a string, got {type(request.content).__name__}",
                    error_code=ErrorCode.VALIDATION_ERROR
                )
            
            request.content = request.content.strip()
            if not request.content:
                raise AgentError(
                    "Message cannot be empty",
                    error_code=ErrorCode.VALIDATION_ERROR
                )
            
            if len(request.content) > self.config.max_message_length:
                raise AgentError(
                    f"Message exceeds maximum length of {self.config.max_message_length} "
                    f"characters (received {len(request.content)})",
                    error_code=ErrorCode.VALIDATION_ERROR
                )
            
            # Run pre-processors
            for processor in self._pre_processors:
                request = await processor(request)
            
            self.status = AgentStatus.PROCESSING
            self.logger.debug(f"Processing message: {request.content[:50]}...")
            
            # Generate response with timeout and retry
            response.content = await self._generate_response_with_retry(
                request.content,
                request.metadata
            )
            response.success = True
            
            # Run post-processors
            for processor in self._post_processors:
                response = await processor(response)
            
            # Store message
            await self.store.save(self.config.agent_id, request, response)
            
            self.logger.info(f"Message processed successfully: {request.message_id}")
            
        except AgentError as e:
            response.success = False
            response.error_code = e.error_code
            response.error_message = e.message
            self.status = AgentStatus.ERROR
            self.logger.error(f"Agent error: {e.message}")
            # Still store for audit trail
            await self.store.save(self.config.agent_id, request, response)
            
        except Exception as e:
            response.success = False
            response.error_code = ErrorCode.UNKNOWN_ERROR
            response.error_message = str(e)
            self.status = AgentStatus.ERROR
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            await self.store.save(self.config.agent_id, request, response)
        
        finally:
            self.status = AgentStatus.IDLE
        
        return response
    
    async def _generate_response_with_retry(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response with retry logic."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.provider.generate_response(
                        message,
                        context,
                        timeout=self.config.timeout_seconds
                    ),
                    timeout=self.config.timeout_seconds
                )
                return response
            
            except asyncio.TimeoutError as e:
                last_error = e
                wait_time = 2 ** attempt  # Exponential backoff
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(
                        f"Timeout on attempt {attempt + 1}, retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise AgentError(
                        f"Provider timeout after {self.config.max_retries} attempts",
                        error_code=ErrorCode.TIMEOUT_ERROR
                    )
            
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(
                        f"Error on attempt {attempt + 1}: {e}, retrying..."
                    )
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AgentError(
                        f"Provider error: {str(e)}",
                        error_code=ErrorCode.PROVIDER_ERROR
                    )
        
        raise AgentError(
            f"Failed after {self.config.max_retries} attempts: {str(last_error)}",
            error_code=ErrorCode.PROVIDER_ERROR
        )
    
    # ========================================================================
    # Middleware/Interceptors
    # ========================================================================
    
    def register_pre_processor(
        self,
        processor: Callable[[AgentRequest], Awaitable[AgentRequest]]
    ) -> None:
        """Register a pre-processing middleware."""
        self._pre_processors.append(processor)
        self.logger.debug(f"Registered pre-processor: {processor.__name__}")
    
    def register_post_processor(
        self,
        processor: Callable[[AgentResponse], Awaitable[AgentResponse]]
    ) -> None:
        """Register a post-processing middleware."""
        self._post_processors.append(processor)
        self.logger.debug(f"Registered post-processor: {processor.__name__}")
    
    # ========================================================================
    # Status & Metadata
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.agent_name,
            "description": self.config.description,
            "status": self.status.value,
            "provider_type": self.config.provider_type,
            "api_configured": bool(self.config.api_key and self.config.api_base_url),
        }
    
    async def health_check(self) -> bool:
        """Check agent health."""
        try:
            return await self.provider.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    # ========================================================================
    # History Management
    # ========================================================================
    
    async def get_history(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get message history."""
        return await self.store.get_history(self.config.agent_id, limit, offset)
    
    async def clear_history(self) -> None:
        """Clear message history."""
        await self.store.clear(self.config.agent_id)
        self.logger.info("Message history cleared")


# ============================================================================
# MULTI-AGENT REGISTRY
# ============================================================================

class AgentRegistry:
    """
    Registry for discovering and coordinating multiple agents.
    
    Enables multi-agent workflows where agents can discover each other
    and communicate through a central registry.
    """
    
    def __init__(self):
        self._agents: Dict[str, AIAgent] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self.logger = setup_logger(f"{__name__}.AgentRegistry")
    
    def register(self, agent: AIAgent) -> None:
        """Register an agent in the registry."""
        agent_id = agent.config.agent_id
        self._agents[agent_id] = agent
        self.logger.info(
            f"Registered agent: {agent.config.agent_name} ({agent_id})"
        )
    
    def unregister(self, agent_id: str) -> None:
        """Unregister an agent from the registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
    
    def get(self, agent_id: str) -> Optional[AIAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def get_by_name(self, name: str) -> Optional[AIAgent]:
        """Get an agent by name."""
        for agent in self._agents.values():
            if agent.config.agent_name == name:
                return agent
        return None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their status."""
        return [agent.get_status() for agent in self._agents.values()]
    
    async def broadcast(
        self,
        message: str,
        sender_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, AgentResponse]:
        """
        Broadcast a message to all agents (except sender).
        
        Returns:
            Dictionary mapping agent_id to response.
        """
        responses = {}
        metadata = metadata or {}
        metadata['broadcast'] = True
        metadata['sender_id'] = sender_id
        
        tasks = []
        agent_ids = []
        
        for agent_id, agent in self._agents.items():
            if agent_id != sender_id:
                agent_ids.append(agent_id)
                request = AgentRequest(content=message, metadata=metadata)
                tasks.append(agent.process_request(request))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for agent_id, result in zip(agent_ids, results):
            if isinstance(result, Exception):
                responses[agent_id] = AgentResponse(
                    request_id=agent_id,
                    success=False,
                    error_message=str(result)
                )
            else:
                responses[agent_id] = result
        
        return responses
    
    def on(self, event: str, callback: Callable) -> None:
        """Register an event callback."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_agent(
    name: str = "AI Agent",
    description: str = "",
    provider: Optional[LLMProvider] = None,
    store: Optional[MessageStore] = None,
    debug: bool = False
) -> AIAgent:
    """
    Create and initialize an AI Agent with sensible defaults.
    
    Args:
        name: Agent name.
        description: Agent description.
        provider: Optional LLM provider.
        store: Optional message store.
        debug: Enable debug logging.
    
    Returns:
        Initialized AIAgent instance.
    """
    config = AgentConfig(
        agent_name=name,
        description=description,
        debug_mode=debug
    )
    agent = AIAgent(config, provider, store)
    return agent


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Example usage of the AI Agent."""
    try:
        # Create a simple agent
        agent = await create_agent(
            name="Example Agent",
            description="A standalone AI agent",
            debug=True
        )
        
        # Process a message
        response = await agent.respond("Hello, agent!")
        print(f"Response: {response}")
        
        # Check status
        status = agent.get_status()
        print(f"Status: {status}")
        
        # Multi-agent example
        registry = AgentRegistry()
        
        agent1 = await create_agent(name="Agent 1")
        agent2 = await create_agent(name="Agent 2")
        
        registry.register(agent1)
        registry.register(agent2)
        
        print(f"Registered agents: {registry.list_agents()}")
        
        # Broadcast message
        responses = await registry.broadcast("Hello all agents!", sender_id=agent1.config.agent_id)
        for agent_id, response in responses.items():
            print(f"{agent_id}: {response.content}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

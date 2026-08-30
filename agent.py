import os
import logging
from typing import Optional, Dict, Any
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent operational status."""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    OFFLINE = "offline"


class AgentConfig:
    """Configuration management for the AI Agent."""

    def __init__(self):
        """Load configuration from environment variables."""
        self.agent_name: str = os.getenv("AGENT_NAME", "Java Global AI Agent")
        self.api_base_url: str = os.getenv("API_BASE_URL", "")
        self.api_key: str = os.getenv("API_KEY", "")
        self.debug_mode: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.max_message_length: int = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))

        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")

    def validate(self) -> bool:
        """Validate critical configuration."""
        if not self.agent_name:
            logger.error("AGENT_NAME is not configured")
            return False
        return True


class AIAgent:
    """AI Agent for Java Global Commodities."""

    def __init__(self, name: Optional[str] = None, config: Optional[AgentConfig] = None):
        """
        Initialize the AI Agent.

        Args:
            name: Optional agent name. If provided, overrides config.
            config: AgentConfig instance. If None, creates a new one.

        Raises:
            ValueError: If configuration validation fails.
        """
        self.config = config or AgentConfig()

        if not self.config.validate():
            raise ValueError("Invalid agent configuration")

        # Use provided name if given, otherwise use from config
        self.name = name if name else self.config.agent_name
        self.status = AgentStatus.IDLE
        self.message_history: list[Dict[str, str]] = []

        logger.info(f"AI Agent '{self.name}' initialized successfully")

    def respond(self, message: str) -> str:
        """
        Process an incoming message and generate a response.

        Args:
            message: The input message to process.

        Returns:
            Response string from the agent.

        Raises:
            ValueError: If the message is empty or exceeds max length.
            TypeError: If the message is not a string.
        """
        try:
            # Validate input type
            if not isinstance(message, str):
                error_msg = f"Message must be a string, got {type(message).__name__}"
                logger.error(error_msg)
                raise TypeError(error_msg)

            # Strip whitespace and validate
            message = message.strip()
            if not message:
                error_msg = "Message cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Check message length
            if len(message) > self.config.max_message_length:
                error_msg = (
                    f"Message exceeds maximum length of {self.config.max_message_length} "
                    f"characters (received {len(message)})"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(f"Processing message: {message[:50]}...")
            self.status = AgentStatus.PROCESSING

            # Generate response
            response = self._generate_response(message)

            # Store in history
            self.message_history.append({
                "input": message,
                "output": response
            })

            self.status = AgentStatus.IDLE
            logger.info("Message processed successfully")

            return response

        except (ValueError, TypeError) as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            raise

    def _generate_response(self, message: str) -> str:
        """
        Generate a response to the message.

        This is a placeholder for future integration with:
        - LLM APIs (OpenAI, Gemini, etc.)
        - Java Global Commodities business logic
        - Custom knowledge bases

        Args:
            message: The input message.

        Returns:
            Generated response string.
        """
        # TODO: Integrate with actual LLM or business logic
        # For now, return a simple acknowledgment
        return f"{self.name}: Saya menerima pesan: {message}"

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent.

        Returns:
            Dictionary containing agent status and metadata.
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "messages_processed": len(self.message_history),
            "api_configured": bool(self.config.api_key and self.config.api_base_url),
        }

    def clear_history(self) -> None:
        """Clear the message history."""
        self.message_history = []
        logger.info("Message history cleared")

    def call_api(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a call to Java Global Commodities API.

        This is a placeholder for future API integration.

        Args:
            endpoint: API endpoint to call.
            data: Optional data to send in the request.

        Returns:
            API response as dictionary, or None if not configured.

        Raises:
            RuntimeError: If API call fails.
        """
        try:
            if not self.config.api_key or not self.config.api_base_url:
                logger.warning("API not configured. Skipping API call to endpoint: %s", endpoint)
                return None

            logger.debug(f"Calling API endpoint: {endpoint}")

            # TODO: Implement actual API calls using requests library
            # Example:
            # import requests
            # response = requests.post(
            #     f"{self.config.api_base_url}/{endpoint}",
            #     json=data,
            #     headers={"Authorization": f"Bearer {self.config.api_key}"}
            # )
            # return response.json()

            return None

        except Exception as e:
            logger.error(f"API call failed for endpoint '{endpoint}': {e}", exc_info=True)
            raise RuntimeError(f"API call failed: {e}") from e


if __name__ == "__main__":
    try:
        agent = AIAgent()
        print(agent.respond("Agent AI aktif"))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

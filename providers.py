"""
LLM Provider implementations for AI Agent.

This module provides concrete implementations of the LLMProvider interface
for different language model backends (OpenAI, local, stub, etc.).

Each provider handles:
- API communication
- Response parsing
- Error handling
- Health checks
"""

import asyncio
import logging
from abc import abstractmethod
from typing import Optional, Dict, Any

from agent import LLMProvider, setup_logger, AgentError, ErrorCode


logger = setup_logger(__name__)


# ============================================================================
# OPENAI PROVIDER
# ============================================================================

class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT API provider.
    
    Requires environment variables:
    - OPENAI_API_KEY: API key for OpenAI
    - OPENAI_MODEL: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
    - OPENAI_API_BASE: Optional custom API base URL
    """
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", api_base: str = ""):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base or "https://api.openai.com/v1"
        self.logger = setup_logger(f"{__name__}.OpenAIProvider")
        
        try:
            import openai
            self.openai = openai
            openai.api_key = self.api_key
            if self.api_base:
                openai.api_base = self.api_base
        except ImportError:
            raise AgentError(
                "OpenAI package not installed. Install with: pip install openai",
                error_code=ErrorCode.PROVIDER_ERROR
            )
    
    async def generate_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> str:
        """Generate a response using OpenAI API."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._call_openai,
                    message,
                    context
                ),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            raise AgentError(
                f"OpenAI API timeout after {timeout}s",
                error_code=ErrorCode.TIMEOUT_ERROR
            )
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise AgentError(
                f"OpenAI error: {str(e)}",
                error_code=ErrorCode.PROVIDER_ERROR
            )
    
    def _call_openai(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Synchronous OpenAI API call."""
        messages = [{"role": "user", "content": message}]
        
        if context and context.get("system_prompt"):
            messages.insert(0, {
                "role": "system",
                "content": context["system_prompt"]
            })
        
        response = self.openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=context.get("temperature", 0.7) if context else 0.7,
            max_tokens=context.get("max_tokens", 500) if context else 500,
        )
        
        return response.choices[0].message.content
    
    async def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            # Simple health check - list models
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self.openai.Model.list()),
                timeout=5.0
            )
            return True
        except Exception as e:
            self.logger.error(f"OpenAI health check failed: {e}")
            return False


# ============================================================================
# GOOGLE GEMINI PROVIDER
# ============================================================================

class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider.
    
    Requires environment variables:
    - GEMINI_API_KEY: API key for Google Gemini
    - GEMINI_MODEL: Model name (e.g., "gemini-pro")
    """
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        self.logger = setup_logger(f"{__name__}.GeminiProvider")
        
        try:
            import google.generativeai as genai
            self.genai = genai
            genai.configure(api_key=self.api_key)
        except ImportError:
            raise AgentError(
                "Google Generative AI package not installed. Install with: pip install google-generativeai",
                error_code=ErrorCode.PROVIDER_ERROR
            )
    
    async def generate_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> str:
        """Generate a response using Gemini API."""
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._call_gemini,
                    message,
                    context
                ),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            raise AgentError(
                f"Gemini API timeout after {timeout}s",
                error_code=ErrorCode.TIMEOUT_ERROR
            )
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            raise AgentError(
                f"Gemini error: {str(e)}",
                error_code=ErrorCode.PROVIDER_ERROR
            )
    
    def _call_gemini(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Synchronous Gemini API call."""
        model = self.genai.GenerativeModel(self.model)
        
        if context and context.get("system_prompt"):
            response = model.generate_content(
                [context["system_prompt"], message],
                generation_config=self.genai.types.GenerationConfig(
                    temperature=context.get("temperature", 0.7),
                    max_output_tokens=context.get("max_tokens", 500),
                )
            )
        else:
            response = model.generate_content(
                message,
                generation_config=self.genai.types.GenerationConfig(
                    temperature=context.get("temperature", 0.7) if context else 0.7,
                    max_output_tokens=context.get("max_tokens", 500) if context else 500,
                )
            )
        
        return response.text
    
    async def health_check(self) -> bool:
        """Check Gemini API health."""
        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.genai.GenerativeModel(self.model).generate_content("test")
                ),
                timeout=5.0
            )
            return True
        except Exception as e:
            self.logger.error(f"Gemini health check failed: {e}")
            return False


# ============================================================================
# LOCAL OLLAMA PROVIDER
# ============================================================================

class OllamaProvider(LLMProvider):
    """
    Local Ollama LLM provider.
    
    Requires:
    - Ollama running locally (default: http://localhost:11434)
    
    Environment variables:
    - OLLAMA_API_BASE: Base URL (default: http://localhost:11434)
    - OLLAMA_MODEL: Model name (e.g., "llama2", "neural-chat")
    """
    
    def __init__(self, model: str = "llama2", api_base: str = "http://localhost:11434"):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.logger = setup_logger(f"{__name__}.OllamaProvider")
        
        try:
            import httpx
            self.httpx = httpx
        except ImportError:
            raise AgentError(
                "httpx package not installed. Install with: pip install httpx",
                error_code=ErrorCode.PROVIDER_ERROR
            )
    
    async def generate_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> str:
        """Generate a response using Ollama."""
        try:
            async with self.httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": message,
                        "stream": False,
                    }
                )
                
                if response.status_code != 200:
                    raise AgentError(
                        f"Ollama API error: {response.status_code}",
                        error_code=ErrorCode.PROVIDER_ERROR
                    )
                
                data = response.json()
                return data.get("response", "")
        
        except asyncio.TimeoutError:
            raise AgentError(
                f"Ollama API timeout after {timeout}s",
                error_code=ErrorCode.TIMEOUT_ERROR
            )
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")
            raise AgentError(
                f"Ollama error: {str(e)}",
                error_code=ErrorCode.PROVIDER_ERROR
            )
    
    async def health_check(self) -> bool:
        """Check Ollama API health."""
        try:
            async with self.httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_base}/api/tags")
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False


# ============================================================================
# PROVIDER FACTORY
# ============================================================================

def create_provider(
    provider_type: str,
    api_key: str = "",
    model: str = "",
    api_base: str = ""
) -> LLMProvider:
    """
    Factory function to create a provider instance.
    
    Args:
        provider_type: Type of provider ("openai", "gemini", "ollama", "text")
        api_key: API key for the provider
        model: Model name
        api_base: Optional custom API base URL
    
    Returns:
        Initialized LLMProvider instance
    
    Raises:
        AgentError: If provider type is unknown or initialization fails
    """
    provider_type = provider_type.lower()
    
    if provider_type == "openai":
        if not api_key:
            raise AgentError(
                "OpenAI provider requires API key",
                error_code=ErrorCode.CONFIG_ERROR
            )
        return OpenAIProvider(api_key, model or "gpt-3.5-turbo", api_base)
    
    elif provider_type == "gemini":
        if not api_key:
            raise AgentError(
                "Gemini provider requires API key",
                error_code=ErrorCode.CONFIG_ERROR
            )
        return GeminiProvider(api_key, model or "gemini-pro")
    
    elif provider_type == "ollama":
        return OllamaProvider(model or "llama2", api_base or "http://localhost:11434")
    
    elif provider_type == "text":
        from agent import SimpleTextProvider
        return SimpleTextProvider()
    
    else:
        raise AgentError(
            f"Unknown provider type: {provider_type}",
            error_code=ErrorCode.CONFIG_ERROR
        )

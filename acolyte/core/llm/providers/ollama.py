"""
Ollama LLM Client implementation for Acolyte.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from ...db.models import LlmConfig
from ..base import LlmClient
from ..constants import (DEFAULT_TIMEOUT, PROVIDER_OLLAMA)
from ..response import ResponseParser, ErrorHandler

logger = logging.getLogger(__name__)


class OllamaClient(LlmClient):
    """
    Client for Ollama API, which provides local model hosting.
    """

    def __init__(self, llm_config: LlmConfig):
        super().__init__(llm_config)
        self.provider = PROVIDER_OLLAMA
        self.base_url = self._normalize_base_url(self.base_url)
        # Local models might need more time to respond
        self.timeout = DEFAULT_TIMEOUT * 2  
        self.response_parser = ResponseParser()
        self.error_handler = ErrorHandler()
        logger.debug(f"Initialized OllamaClient with model: {self.model_name}")

    def _check_api_key(self) -> bool:
        """
        Check if API key is set. 
        Ollama doesn't typically use API keys, so we return True.
        """
        return True

    def _normalize_base_url(self, base_url: str) -> str:
        """
        Normalize the Ollama API base URL.
        Default to http://localhost:11434 if not set.
        """
        if not base_url:
            return "http://localhost:11434"
        
        # Remove trailing slashes
        base_url = base_url.rstrip("/")
        
        # Ensure URL has http:// or https:// prefix
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
            
        return base_url

    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        Process content with Ollama API.
        
        Args:
            content: The content to be analyzed
            prompt: The prompt template to use
            
        Returns:
            Dict with response data or error information
        """
        try:
            # Prepare prompt
            system_prompt = "You are a content analyst specializing in detecting bias, misleading information, and hidden intent."
            user_prompt = self._prepare_prompt(content, prompt)
            
            # Call API
            response = await self._process_with_api(system_prompt, user_prompt)
            return response
            
        except Exception as e:
            error_msg = f"Error processing content with Ollama: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def _process_with_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Make a request to the Ollama API.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Dict with response data or error information
        """
        try:
            # Prepare API URL for Ollama
            api_url = f"{self.base_url}/api/generate"
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Prepare request data
            # Ollama has a different API format
            data = {
                "model": self.model_name,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for analytical tasks
                    "top_p": 0.95,
                    "top_k": 40,
                    "num_predict": 4096
                }
            }
            
            logger.debug(f"Making request to Ollama API: {api_url}")
            
            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=data
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse response
                response_json = response.json()
                
                # Extract the response text from Ollama-specific format
                if "response" in response_json:
                    response_text = response_json["response"]
                    
                    # Parse scores and structured content
                    scores = self.response_parser.extract_scores(response_text)
                    structured_content = self.response_parser.extract_structured_content(response_text)
                    
                    return {
                        "success": True,
                        "response": response_text,
                        "scores": scores,
                        "structured_content": structured_content,
                        "raw_response": response_json
                    }
                else:
                    return {
                        "success": False,
                        "error": "Invalid response format from Ollama API",
                        "raw_response": response_json
                    }
                    
        except httpx.HTTPStatusError as e:
            return self.error_handler.handle_request_error(e, "Ollama")
            
        except httpx.RequestError as e:
            error_msg = f"Network error when calling Ollama API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error with Ollama API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        Test connection to Ollama API.
        
        Returns:
            Dict with success status and message
        """
        try:
            # Use Ollama's models endpoint to check connectivity
            api_url = f"{self.base_url}/api/tags"
            
            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(api_url)
                
                # Check response status
                response.raise_for_status()
                
                # Check if the model exists
                models_response = response.json()
                if "models" in models_response:
                    # Check if our model is in the list
                    model_names = [model.get("name") for model in models_response.get("models", [])]
                    if self.model_name in model_names:
                        return {"success": True, "message": f"Successfully connected to Ollama API and found model {self.model_name}"}
                    else:
                        available_models = ", ".join(model_names[:5])
                        return {"success": False, "message": f"Connected to Ollama API but model {self.model_name} not found. Available models: {available_models}..."}
                
                # If we get here but can't verify the model, the connection is still successful
                return {"success": True, "message": "Successfully connected to Ollama API"}
                
        except httpx.HTTPStatusError as e:
            error_details = self.error_handler.format_error_message(e, "Ollama")
            return {"success": False, "message": error_details}
            
        except Exception as e:
            error_msg = f"Error testing connection to Ollama API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}
"""
DeepSeek LLM Client implementation for Acolyte.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from ...db.models import LlmConfig
from ..base import LlmClient
from ..constants import (DEFAULT_TIMEOUT, PROVIDER_DEEPSEEK,
                         RETRY_STATUS_CODES)
from ..response import ResponseParser, ErrorHandler

logger = logging.getLogger(__name__)


class DeepSeekClient(LlmClient):
    """
    Client for DeepSeek API, which is compatible with OpenAI API.
    """

    def __init__(self, llm_config: LlmConfig):
        super().__init__(llm_config)
        self.provider = PROVIDER_DEEPSEEK
        self.base_url = self._normalize_base_url(self.base_url)
        self.timeout = DEFAULT_TIMEOUT
        self.response_parser = ResponseParser()
        self.error_handler = ErrorHandler()
        logger.debug(f"Initialized DeepSeekClient with model: {self.model_name}")

    def _check_api_key(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)

    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        Process content with DeepSeek API.
        
        Args:
            content: The content to be analyzed
            prompt: The prompt template to use
            
        Returns:
            Dict with response data or error information
        """
        if not self._check_api_key():
            logger.error("DeepSeek API key not set")
            return {"success": False, "error": "API key not set"}
        
        try:
            # Prepare prompt
            system_prompt = "You are a content analyst specializing in detecting bias, misleading information, and hidden intent."
            user_prompt = self._prepare_prompt(content, prompt)
            
            # Call API
            response = await self._process_with_api(system_prompt, user_prompt)
            return response
            
        except Exception as e:
            error_msg = f"Error processing content with DeepSeek: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def _process_with_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Make a request to the DeepSeek API.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Dict with response data or error information
        """
        try:
            # Prepare API URL
            api_url = f"{self.base_url}/chat/completions"
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare data
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # Low temperature for analytical tasks
                "max_tokens": 4096
            }
            
            logger.debug(f"Making request to DeepSeek API: {api_url}")
            
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
                
                # Extract the response text
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    response_text = response_json["choices"][0]["message"]["content"]
                    
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
                        "error": "Invalid response format from DeepSeek API",
                        "raw_response": response_json
                    }
                    
        except httpx.HTTPStatusError as e:
            return self.error_handler.handle_request_error(e, "DeepSeek")
            
        except httpx.RequestError as e:
            error_msg = f"Network error when calling DeepSeek API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error with DeepSeek API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        Test connection to DeepSeek API.
        
        Returns:
            Dict with success status and message
        """
        if not self._check_api_key():
            return {"success": False, "message": "API key not set"}
        
        try:
            # Use a minimal prompt to test connection
            system_prompt = "You are a helpful assistant."
            user_prompt = "Hello, this is a connection test. Please respond with 'Connection successful'."
            
            # Make a test request with minimal tokens
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 20,
                "temperature": 0.1
            }
            
            # Prepare API URL and headers
            api_url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=data
                )
                
                # Check response status
                response.raise_for_status()
                
                # If we get here, the connection is successful
                return {"success": True, "message": "Successfully connected to DeepSeek API"}
                
        except httpx.HTTPStatusError as e:
            error_details = self.error_handler.format_error_message(e, "DeepSeek")
            return {"success": False, "message": error_details}
            
        except Exception as e:
            error_msg = f"Error testing connection to DeepSeek API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}
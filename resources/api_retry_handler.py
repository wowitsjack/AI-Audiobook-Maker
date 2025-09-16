import time
import logging
from typing import Optional, Callable, Any
from google import genai
from google.genai import types
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIRetryHandler:
    """Handle API calls with retry logic for different HTTP error codes"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry"""
        if isinstance(error, HTTPError):
            status_code = error.response.status_code if error.response else None
            
            # Retry on 500 (Internal Server Error) and 502 (Bad Gateway)
            if status_code in [500, 502]:
                return True
            
            # Don't retry on 503 (Service Unavailable) - stop completely
            if status_code == 503:
                logger.error("🚫 Service unavailable (503). Stopping generation.")
                return False
            
            # Don't retry on client errors (4xx)
            if status_code and 400 <= status_code < 500:
                return False
        
        # Retry on network errors
        if isinstance(error, (ConnectionError, Timeout)):
            return True
        
        # Don't retry on unknown errors by default
        return False
    
    def call_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"✅ API call succeeded after {attempt} retries")
                return result
                
            except Exception as e:
                last_error = e
                
                # Check if this is an HTTP error we can handle
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                    logger.warning(f"🔴 API call failed with HTTP {status_code}: {str(e)}")
                    
                    # Handle 503 (Service Unavailable) - don't retry, stop completely
                    if status_code == 503:
                        logger.error("🚫 Service unavailable (503). Cannot continue generation.")
                        raise ServiceUnavailableError("Google AI service is currently unavailable (503). Please try again later.")
                    
                    # Handle 500 errors - retry with backoff
                    if status_code == 500:
                        if attempt < self.max_retries:
                            delay = self.exponential_backoff(attempt)
                            logger.warning(f"🔄 Internal server error (500). Retrying in {delay:.1f} seconds... (attempt {attempt + 1}/{self.max_retries})")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Maximum retries ({self.max_retries}) exceeded for 500 error")
                            raise MaxRetriesExceededError(f"API calls failed after {self.max_retries} retries due to server errors")
                    
                    # Handle other HTTP errors
                    if status_code >= 400:
                        logger.error(f"❌ HTTP {status_code} error: {str(e)}")
                        raise HTTPAPIError(f"API call failed with HTTP {status_code}: {str(e)}")
                
                # Handle network errors
                elif isinstance(e, (ConnectionError, Timeout)):
                    if attempt < self.max_retries:
                        delay = self.exponential_backoff(attempt)
                        logger.warning(f"🌐 Network error: {str(e)}. Retrying in {delay:.1f} seconds... (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Maximum retries ({self.max_retries}) exceeded for network error")
                        raise MaxRetriesExceededError(f"Network calls failed after {self.max_retries} retries: {str(e)}")
                
                # Handle other unknown errors
                else:
                    logger.error(f"❌ Unexpected error: {str(e)}")
                    if attempt < self.max_retries and self.should_retry(e):
                        delay = self.exponential_backoff(attempt)
                        logger.warning(f"🔄 Retrying in {delay:.1f} seconds... (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        raise
        
        # If we get here, all retries failed
        if last_error:
            raise last_error


class ServiceUnavailableError(Exception):
    """Raised when the service is unavailable (503)"""
    pass


class MaxRetriesExceededError(Exception):
    """Raised when maximum retry attempts are exceeded"""
    pass


class HTTPAPIError(Exception):
    """Raised for HTTP API errors that shouldn't be retried"""
    pass


def generate_audio_with_retry(client: genai.Client, prompt: str, voice_name: str, 
                            max_retries: int = 3, log_callback: Optional[Callable] = None) -> bytes:
    """Generate audio with retry logic"""
    retry_handler = APIRetryHandler(max_retries=max_retries)
    
    def _generate_audio():
        if log_callback:
            log_callback("🎤 Calling Google AI TTS API...")
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro-preview-tts",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    )
                )
            )
            
            # Extract audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            if log_callback:
                log_callback("✅ TTS API call successful")
            
            return audio_data
            
        except Exception as e:
            # Convert to HTTPError if possible for consistent handling
            if hasattr(e, 'code') or hasattr(e, 'status_code'):
                # Create a mock response object for consistency
                class MockResponse:
                    def __init__(self, status_code):
                        self.status_code = status_code
                
                if hasattr(e, 'code'):
                    status_code = e.code
                elif hasattr(e, 'status_code'):
                    status_code = e.status_code
                else:
                    status_code = 500  # Default to server error
                
                mock_response = MockResponse(status_code)
                http_error = HTTPError(f"API Error: {str(e)}")
                http_error.response = mock_response
                raise http_error
            else:
                # Re-raise as-is for non-HTTP errors
                raise
    
    return retry_handler.call_with_retry(_generate_audio)


# Convenience function for backwards compatibility
def safe_api_call(func: Callable, *args, max_retries: int = 3, **kwargs) -> Any:
    """Safely call an API function with retry logic"""
    retry_handler = APIRetryHandler(max_retries=max_retries)
    return retry_handler.call_with_retry(func, *args, **kwargs)
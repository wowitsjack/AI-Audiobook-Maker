import time
import logging
import threading
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import queue
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """Rate limit information"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 10000
    current_requests: int = 0
    current_tokens: int = 0
    window_start: datetime = None
    
    def __post_init__(self):
        if self.window_start is None:
            self.window_start = datetime.now()

class SmartRateLimiter:
    """Intelligent rate limiter for Google Gemini API"""
    
    def __init__(self):
        self.rate_limits = {
            'gemini-2.5-pro-preview-tts': RateLimit(
                requests_per_minute=15,  # Conservative estimate
                tokens_per_minute=10000  # From error message
            )
        }
        self.lock = threading.Lock()
        self.request_queue = queue.Queue()
        self.last_request_time = 0
        self.min_request_interval = 4.0  # Minimum 4 seconds between requests
        
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        # Very rough estimate: ~1 token per 4 characters for English
        # This is conservative - actual tokenization may differ
        return max(1, len(text) // 4)
    
    def reset_window_if_needed(self, model: str):
        """Reset rate limit window if a minute has passed"""
        now = datetime.now()
        rate_limit = self.rate_limits.get(model)
        
        if rate_limit and (now - rate_limit.window_start) >= timedelta(minutes=1):
            logger.info(f"🔄 Resetting rate limit window for {model}")
            rate_limit.current_requests = 0
            rate_limit.current_tokens = 0
            rate_limit.window_start = now
    
    def can_make_request(self, model: str, estimated_tokens: int) -> tuple[bool, float]:
        """Check if we can make a request, return (can_proceed, wait_time)"""
        with self.lock:
            self.reset_window_if_needed(model)
            
            rate_limit = self.rate_limits.get(model)
            if not rate_limit:
                return True, 0.0
            
            # Check minimum interval between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                interval_wait = self.min_request_interval - time_since_last
                logger.info(f"⏱️ Enforcing minimum {self.min_request_interval}s interval between requests")
                return False, interval_wait
            
            # Check rate limits
            if (rate_limit.current_requests >= rate_limit.requests_per_minute or
                rate_limit.current_tokens + estimated_tokens > rate_limit.tokens_per_minute):
                
                # Calculate how long to wait until next window
                time_until_reset = 60 - (datetime.now() - rate_limit.window_start).total_seconds()
                wait_time = max(0, time_until_reset)
                
                logger.warning(f"🚦 Rate limit reached for {model}. "
                             f"Requests: {rate_limit.current_requests}/{rate_limit.requests_per_minute}, "
                             f"Tokens: {rate_limit.current_tokens + estimated_tokens}/{rate_limit.tokens_per_minute}")
                return False, wait_time
            
            return True, 0.0
    
    def record_request(self, model: str, actual_tokens: int):
        """Record a successful request"""
        with self.lock:
            rate_limit = self.rate_limits.get(model)
            if rate_limit:
                rate_limit.current_requests += 1
                rate_limit.current_tokens += actual_tokens
                self.last_request_time = time.time()
                
                logger.info(f"📊 Rate limit usage for {model}: "
                          f"Requests: {rate_limit.current_requests}/{rate_limit.requests_per_minute}, "
                          f"Tokens: {rate_limit.current_tokens}/{rate_limit.tokens_per_minute}")
    
    def wait_for_rate_limit(self, model: str, estimated_tokens: int, 
                           progress_callback: Optional[Callable] = None):
        """Wait until we can make a request within rate limits"""
        while True:
            can_proceed, wait_time = self.can_make_request(model, estimated_tokens)
            
            if can_proceed:
                break
            
            if wait_time > 0:
                if progress_callback:
                    progress_callback(f"⏳ Rate limit reached. Waiting {wait_time:.1f}s...")
                
                # Wait in small chunks to allow for cancellation/updates
                wait_chunks = max(1, int(wait_time))
                for i in range(wait_chunks):
                    time.sleep(min(1.0, wait_time / wait_chunks))
                    if progress_callback:
                        remaining = wait_time - (i + 1) * (wait_time / wait_chunks)
                        if remaining > 0:
                            progress_callback(f"⏳ Waiting {remaining:.0f}s more...")

class QuotaAwareRetryHandler:
    """Enhanced retry handler that understands API quotas and rate limits"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.rate_limiter = SmartRateLimiter()
    
    def parse_retry_after(self, error_details: str) -> float:
        """Parse retry-after from error details"""
        try:
            # Look for retryDelay in the error message
            if 'retryDelay' in error_details:
                # Extract delay like "1s", "50s", etc.
                match = re.search(r'retryDelay[\'"]:\s*[\'"](\d+)s[\'"]', error_details)
                if match:
                    return float(match.group(1))
            
            # Default fallback
            return 60.0
        except:
            return 60.0
    
    def exponential_backoff(self, attempt: int, base_delay: Optional[float] = None) -> float:
        """Calculate exponential backoff delay"""
        if base_delay is None:
            base_delay = self.base_delay
        delay = base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def handle_429_error(self, error_str: str, attempt: int) -> float:
        """Handle 429 rate limit errors with proper backoff"""
        retry_delay = self.parse_retry_after(error_str)
        
        # Add some jitter and increase delay for repeated attempts
        jitter = retry_delay * 0.1  # 10% jitter
        total_delay = retry_delay + (attempt * 10) + jitter
        
        logger.warning(f"🚦 Rate limited (429). Waiting {total_delay:.1f}s before retry...")
        return total_delay
    
    def call_with_quota_awareness(self, func: Callable, model: str, prompt: str,
                                 progress_callback: Optional[Callable] = None, 
                                 *args, **kwargs) -> Any:
        """Execute function with quota awareness and intelligent retry"""
        estimated_tokens = self.rate_limiter.estimate_tokens(prompt)
        
        # Wait for rate limit if needed
        self.rate_limiter.wait_for_rate_limit(model, estimated_tokens, progress_callback)
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if progress_callback:
                    progress_callback(f"🎤 Making API call (attempt {attempt + 1})...")
                
                result = func(*args, **kwargs)
                
                # Record successful request
                self.rate_limiter.record_request(model, estimated_tokens)
                
                if attempt > 0:
                    logger.info(f"✅ API call succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Handle different error types
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                    
                    if status_code == 429:  # Rate limit exceeded
                        if attempt < self.max_retries:
                            delay = self.handle_429_error(error_str, attempt)
                            if progress_callback:
                                progress_callback(f"⏳ Rate limited. Waiting {delay:.0f}s...")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Rate limit retries exhausted after {self.max_retries} attempts")
                            raise QuotaExhaustedError(f"Rate limit exceeded after {self.max_retries} retries")
                    
                    elif status_code == 503:  # Service unavailable
                        logger.error("🚫 Service unavailable (503). Cannot continue.")
                        raise ServiceUnavailableError("Google AI service is currently unavailable")
                    
                    elif status_code in [500, 502]:  # Server errors
                        if attempt < self.max_retries:
                            delay = self.exponential_backoff(attempt)
                            logger.warning(f"🔄 Server error ({status_code}). Retrying in {delay:.1f}s...")
                            if progress_callback:
                                progress_callback(f"🔄 Server error. Retrying in {delay:.0f}s...")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Server error retries exhausted")
                            raise MaxRetriesExceededError(f"Server errors after {self.max_retries} retries")
                    
                    else:
                        # Other HTTP errors
                        logger.error(f"❌ HTTP {status_code} error: {error_str}")
                        raise HTTPAPIError(f"API call failed with HTTP {status_code}: {error_str}")
                
                # Handle other errors
                else:
                    logger.error(f"❌ Unexpected error: {error_str}")
                    if attempt < self.max_retries:
                        delay = self.exponential_backoff(attempt)
                        logger.warning(f"🔄 Retrying in {delay:.1f}s...")
                        if progress_callback:
                            progress_callback(f"🔄 Retrying in {delay:.0f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        raise
        
        # If we get here, all retries failed
        if last_error:
            raise last_error

# Exception classes
class QuotaExhaustedError(Exception):
    """Raised when API quota is exhausted"""
    pass

class ServiceUnavailableError(Exception):
    """Raised when service is unavailable"""
    pass

class MaxRetriesExceededError(Exception):
    """Raised when max retries exceeded"""
    pass

class HTTPAPIError(Exception):
    """Raised for HTTP API errors"""
    pass

# Enhanced generation function with quota awareness
def generate_audio_with_quota_awareness(client, prompt: str, voice_name: str,
                                       model: str = "gemini-2.5-flash-preview-tts",
                                       max_retries: int = 3,
                                       progress_callback: Optional[Callable] = None) -> bytes:
    """Generate audio with intelligent quota management"""
    retry_handler = QuotaAwareRetryHandler(max_retries=max_retries)

    def _generate_audio():
        from google.genai import types

        # Use REST API for TTS generation
        response = client.models.generate_content(
            model=model,
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
        return audio_data

    return retry_handler.call_with_quota_awareness(
        _generate_audio,
        model,
        prompt,
        progress_callback
    )
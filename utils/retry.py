import time
import random
import logging
from functools import wraps
from typing import Callable, Any
from config import RETRY_ATTEMPTS, BASE_DELAY_SEC

logger = logging.getLogger(__name__)

def exponential_backoff(attempt: int, base_delay: int = BASE_DELAY_SEC) -> float:
    """
    Calculate exponential backoff delay with jitter
    """
    delay = base_delay * (2 ** attempt)
    # Add 20% jitter
    jitter = delay * 0.2 * random.random()
    return delay + jitter

def retry_with_backoff(max_attempts: int = RETRY_ATTEMPTS, 
                      base_delay: int = BASE_DELAY_SEC,
                      retryable_exceptions: tuple = (Exception,)):
    """
    Decorator for retrying functions with exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except retryable_exceptions as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Check for non-retryable errors
                    if any(err in error_str for err in [
                        'invalid_request_error',
                        'authentication_error', 
                        'permission_denied',
                        'vision_content_error'
                    ]):
                        logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                        raise e
                    
                    # Check for context length errors - special handling
                    if 'context_length' in error_str:
                        logger.warning(f"Context length exceeded in {func.__name__}: {str(e)}")
                        raise e
                    
                    # Check for retryable errors (5xx, 429, timeout)
                    if any(err in error_str for err in [
                        '5', '429', 'timeout', 'rate_limit', 'server_error'
                    ]) or attempt < max_attempts - 1:
                        
                        if attempt < max_attempts - 1:
                            delay = exponential_backoff(attempt, base_delay)
                            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {delay:.2f}s")
                            time.sleep(delay)
                        continue
                    
                    # For other 4xx errors, don't retry
                    logger.error(f"Non-retryable client error in {func.__name__}: {str(e)}")
                    raise e
            
            # All attempts failed
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}. Last error: {str(last_exception)}")
            if last_exception:
                raise last_exception
            else:
                raise Exception(f"All {max_attempts} attempts failed for {func.__name__}")
        
        return wrapper
    return decorator

def should_retry_http_error(status_code: int) -> bool:
    """
    Determine if HTTP error should be retried
    """
    # Retry server errors and rate limiting
    if status_code >= 500:
        return True
    if status_code == 429:  # Too Many Requests
        return True
    if status_code == 408:  # Request Timeout
        return True
    
    return False

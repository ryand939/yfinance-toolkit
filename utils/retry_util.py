# src/utils/retry_utils.py
from typing import Type, Union, Callable
import functools
import backoff
import random
from utils.exceptions import yFinanceError

def smart_retry(
    max_tries: int = 3,
    allowed_exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = (Exception,),
    on_success: Callable = None,
    on_permanent_failure: Callable = None
) -> Callable:
    """
    API-aware retry decorator with intelligent backoff.
    
    This retry decorator is designed to eventually be used in a future API for my website.
    
    Args:
        max_tries: Maximum retry attempts
        allowed_exceptions: Exception types that trigger retry
        on_success: Optional callback for successful attempts
        on_permanent_failure: Optional callback for permanent failures
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        @backoff.on_exception(
            backoff.expo, # exponential backoff - doubles every time
            allowed_exceptions,
            max_tries=max_tries,
            on_success=on_success,
            on_giveup=on_permanent_failure,
            jitter=lambda: random.uniform(0.1, 0.5)
        )
        def wrapper(*args, **kwargs):
            try:
                # initial attempt
                result = func(*args, **kwargs)
                return result
            except yFinanceError as e:
                # Yahoo Finance specific error handling
                # random delay so retries are not synchronized
                backoff_time = random.uniform(0.5, 2.0)
                print(f"yFinance error occurred, retrying in {backoff_time:.1f} seconds...")
                import time
                time.sleep(backoff_time)
                raise  # raise so backoff handles the retry timing

            except Exception as e:
                # general random exceptions
                if not isinstance(e, allowed_exceptions):
                    raise # not a retryable error
                raise # retryable error, raise and backoff will handle retry timing
        return wrapper
    return decorator
import logging
from functools import wraps


def silence_yfinance_warnings(func):
    """
    Decorator to suppress yfinance's annoying 404 warnings.
    
    Calendar data requests often return 404s for stocks without calendar info.
    This is expected behavior that doesn't need to spam the console.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        yf_logger = logging.getLogger('yfinance')
        original_level = yf_logger.level
        yf_logger.setLevel(logging.CRITICAL + 1)
        try:
            return func(*args, **kwargs)
        finally:
            yf_logger.setLevel(original_level)
    return wrapper

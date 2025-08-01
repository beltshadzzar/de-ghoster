import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logger(name: str = "job_analyzer", level: str = "INFO") -> logging.Logger:
    """
    Setup logger with file and console handlers
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_function_call(func):
    """
    Decorator to log function calls
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("job_analyzer")
        logger.debug(f"Calling {func.__name__} with args: {args[:2]}..., kwargs: {list(kwargs.keys())}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    
    return wrapper
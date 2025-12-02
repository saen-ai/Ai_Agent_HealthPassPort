import logging
import sys
from app.config import settings


def setup_logger(name: str = "health_passport") -> logging.Logger:
    """
    Setup and configure the application logger.
    
    Args:
        name: Logger name (default: health_passport)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    return logger


# Global logger instance
logger = setup_logger()

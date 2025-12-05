"""Centralized logging configuration."""

import logging
import sys

from app.config import settings


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    
    # Get log level from settings
    level = settings.LOG_LEVEL.upper()
    
    # Create logger
    logger = logging.getLogger("ai_health_passport")
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # Prevent duplicate handlers
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level, logging.INFO))
        
        # Format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    logger.debug(f"Logging configured with level: {level}")
    
    return logger


# Create the global logger instance
logger = setup_logging()


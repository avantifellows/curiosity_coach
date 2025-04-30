import logging
import os

def setup_logger(name: str = "brain") -> logging.Logger:
    """
    Set up and configure a logger for console output (suitable for Lambda/CloudWatch).
    
    Args:
        name (str): The name of the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # If the logger already has handlers, prevent adding more.
    # This is important if this function might be called multiple times
    # or if the root logger is also configured elsewhere.
    if logger.hasHandlers():
        return logger

    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)

    return logger

# Create a default logger instance
logger = setup_logger() 
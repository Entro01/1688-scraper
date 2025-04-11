import undetected_chromedriver as uc
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_driver():
    """Initialize and return an undetected-chromedriver which handles version issues better."""
    try:
        options = uc.ChromeOptions()
        
        # Add chrome options from settings
        for arg in settings.CHROME_DRIVER_ARGS:
            options.add_argument(arg)
        
        # Initialize undetected-chromedriver which handles version compatibility better
        driver = uc.Chrome(options=options)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise Exception(f"Chrome driver initialization failed: {str(e)}")
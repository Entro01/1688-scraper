import logging
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)

def solve_captcha(driver):
    """Attempt to solve the slider captcha."""
    logger.info("Attempting to solve captcha...")
    try:
        # Wait for the slider to appear
        slider = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "nc_1_n1z"))
        )
        
        # Get the slider track
        slider_track = driver.find_element(By.ID, "nc_1_n1t")
        track_width = slider_track.size['width']
        
        # Move the slider
        action = ActionChains(driver)
        action.click_and_hold(slider)
        
        # Move with a human-like pattern - slow start, faster middle, slower end
        steps = 10
        for i in range(steps):
            # Simulate human-like movement with slight variations
            if i < steps // 3:
                # Slow start
                move = (track_width / steps) * 0.7
            elif i < 2 * (steps // 3):
                # Faster middle
                move = (track_width / steps) * 1.2
            else:
                # Slower end
                move = (track_width / steps) * 0.8
                
            # Add some random variation to seem more human-like
            move += random.uniform(-2, 2)
            
            action.move_by_offset(move, random.uniform(-1, 1))
            time.sleep(random.uniform(0.01, 0.05))  # Random short delay between movements
        
        # Release at the end
        action.release().perform()
        time.sleep(2)  # Wait for verification to complete
        
        # Check if captcha was successfully solved
        # This is a simple check for the presence of the script tag we need
        page_source = driver.page_source
        if "window.__GLOBAL_DADA" in page_source or "window.GLOBAL_DADA" in page_source:
            logger.info("Captcha solved successfully")
            return True
        else:
            logger.warning("Captcha may not have been solved correctly")
            return False
    except Exception as e:
        logger.error(f"Error solving captcha: {e}")
        return False
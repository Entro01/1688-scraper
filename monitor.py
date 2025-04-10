import time
from selenium import webdriver 
from selenium.webdriver.common.by import By
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re
import json
import logging
from typing import Optional, Dict, Any
import time
import random
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductRequest(BaseModel):
    product_id: str

class ErrorResponse(BaseModel):
    code: int
    message: str

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
        steps = 30
        for i in range(steps):
            # Simulate human-like movement with slight variations
            if i < steps // 3:
                # Slow start
                move = (track_width / steps) * 2
            elif i < 2 * (steps // 3):
                # Faster middle
                move = (track_width / steps) * 3
            else:
                # Slower end
                move = (track_width / steps) * 2.2
                
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
            with open(f"captcha_fail.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return False
    except Exception as e:
        logger.error(f"Error solving captcha: {e}")
        return False

def extract_json_data(html_content):
    """Extract the JSON data from the script tag."""
    # Try different patterns since the exact format might vary
    patterns = [
        r'window\.GLOBAL_DADA\s*=\s*({.*?});.*?window\.INIT_DATA\s*=\s*({.*?});',
        r'window\.__GLOBAL_DADA\s*=\s*({.*?});.*?window\.__INIT_DATA\s*=\s*({.*?});',
        r'window\.GLOBAL_DADA\s*=\s*({.*?});',
        r'window\.__GLOBAL_DADA\s*=\s*({.*?});'
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, html_content, re.DOTALL)
        if matches:
            if len(matches.groups()) > 1:
                # We have both GLOBAL_DADA and INIT_DATA
                try:
                    global_data = json.loads(matches.group(1))
                    init_data = json.loads(matches.group(2))
                    return {
                        "global_data": global_data,
                        "init_data": init_data
                    }
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    continue
            else:
                # We only have GLOBAL_DADA
                try:
                    return {
                        "global_data": json.loads(matches.group(1)),
                        "init_data": None
                    }
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    continue
    
    logger.warning("Could not extract JSON data from script tag")
    return None

def fetch_product_data(product_id: str):
    """Fetch product data from both retail and wholesale endpoints."""
    base_url = "https://detail.1688.com/offer"
    urls = {
        "retail": f"{base_url}/{product_id}.html?sk=order",
        "wholesale": f"{base_url}/{product_id}.html?sk=consign"
    }
    
    result = {}
    
    try:
        driver = webdriver.Chrome()
        
        for url_type, url in urls.items():
            logger.info(f"Fetching data from {url_type} URL: {url}")
            
            driver.get(url)
            time.sleep(3)  # Initial wait for page to load
            
            # Save the page source
            with open(f"{product_id}_{url_type}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            # Check if we hit a captcha
            if "Please slide to verify" in driver.page_source:
                logger.info("Captcha detected. Attempting to solve...")
                if not solve_captcha(driver):
                    # If captcha solving fails, try one more time
                    driver.refresh()
                    time.sleep(2)
                    if not solve_captcha(driver):
                        logger.error("Failed to solve captcha after multiple attempts")
                        raise HTTPException(status_code=403, detail="Captcha challenge failed")
            
            # Extract JSON data from the page
            page_source = driver.page_source
            data = extract_json_data(page_source)
            
            if not data:
                soup = BeautifulSoup(page_source, 'html.parser')
                title_tag = soup.find('title')
                title = title_tag.text if title_tag else "Unknown page"
                logger.error(f"Failed to extract data from {url_type}. Page title: {title}")
                continue
            
            result[url_type] = data
    
    except Exception as e:
        logger.exception(f"Error in fetch_product_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        try:
            if 'driver' in locals() and driver:
                driver.quit()
        except Exception as e:
            logger.error(f"Error closing driver: {e}")
    
    if not result:
        raise HTTPException(status_code=404, detail="Could not fetch product data")
    
    return result

fetch_product_data(745785638968)
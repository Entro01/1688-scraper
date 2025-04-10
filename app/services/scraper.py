from fastapi import HTTPException
import logging
import time
from typing import Dict, Any
from bs4 import BeautifulSoup
import json
import re

from app.utils.driver import get_driver
from app.utils.captcha_solver import solve_captcha

logger = logging.getLogger(__name__)

async def scrape_product_data(product_id: str) -> Dict[str, Any]:
    """Fetch product data from both retail and wholesale endpoints."""
    base_url = "https://detail.1688.com/offer"
    urls = {
        "retail": f"{base_url}/{product_id}.html?sk=order",
        "wholesale": f"{base_url}/{product_id}.html?sk=consign"
    }
    
    result = {}
    driver = None
    
    try:
        driver = get_driver()
        
        for url_type, url in urls.items():
            logger.info(f"Fetching data from {url_type} URL: {url}")
            
            driver.get(url)
            time.sleep(3)  # Initial wait for page to load

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
        logger.exception(f"Error in scrape_product_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        try:
            if driver:
                driver.quit()
        except Exception as e:
            logger.error(f"Error closing driver: {e}")
    
    if not result:
        raise HTTPException(status_code=404, detail="Could not fetch product data")
    
    return result

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
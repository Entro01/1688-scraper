from fastapi import HTTPException
import logging
import time
from typing import Dict, Any
from bs4 import BeautifulSoup
import json
import re
import tenacity

from app.utils.driver import get_driver
from app.utils.captcha_solver import is_captcha_page, solve_captcha

logger = logging.getLogger(__name__)

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=3),
    retry=tenacity.retry_if_result(lambda result: result is False),
    before_sleep=lambda retry_state: logger.info(f"Retrying captcha solve {retry_state.attempt_number}/3...")
)
def solve_captcha_with_retry(driver):
    """Attempt to solve the captcha with retry logic."""
    logger.info("Attempting to solve captcha...")
    result = solve_captcha(driver)
    
    # Check if we're still on a captcha page after solving attempt
    if result and is_captcha_page(driver):
        logger.warning("Still on captcha page after solving attempt")
        return False
    else:
        logger.info("Captcha solved")
    return result

def extract_json_data(html_content):
    """Extract the JSON data from the script tag.""" 
    # Pattern to match the entire script tag containing window.__GLOBAL_DADA
    pattern = re.compile(r'<script[^>]*>(.*?window\.__GLOBAL_DADA\s*=.*?)</script>', re.DOTALL)
    logger.info("Looking for product data.")
    # Find the match in the page source
    match = pattern.search(html_content)
    
    if match:
        # Extract the entire script content
        script_content = match.group(1)
        return script_content.strip()
    else:
        logger.warning("No window.__GLOBAL_DADA found in the page source")
        return None

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    retry=tenacity.retry_if_exception_type(HTTPException),
    before_sleep=lambda retry_state: logger.info(f"Retrying page fetch {retry_state.attempt_number}/3...")
)
async def fetch_url_with_retry(driver, url, url_type):
    """Fetch a single URL with retry logic for captcha handling."""
    logger.info(f"Fetching data from {url_type} URL: {url}")
    
    driver.get(url)
    time.sleep(3)  # Initial wait for page to load

    # Check if we hit a captcha page
    if is_captcha_page(driver):
        logger.info("Captcha page detected. Attempting to solve with retries...")
        if not solve_captcha_with_retry(driver):
            logger.error("Failed to solve captcha after multiple attempts")
            raise HTTPException(status_code=403, detail="Captcha challenge failed")
        
        # Wait a bit after captcha is solved
        time.sleep(2)
    
    # Extract JSON data from the page
    page_source = driver.page_source
    data = extract_json_data(page_source)
    
    if not data:
        soup = BeautifulSoup(page_source, 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.text if title_tag else "Unknown page"
        logger.error(f"Failed to extract data from {url_type}. Page title: {title}")
        raise HTTPException(status_code=404, detail=f"Could not extract data from {url_type}")
    
    return data

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
            try:
                data = await fetch_url_with_retry(driver, url, url_type)
                result[url_type] = data
            except HTTPException as e:
                logger.warning(f"Failed to fetch {url_type} data: {str(e)}")
                # Continue to next URL type even if this one fails
            except Exception as e:
                logger.exception(f"Unexpected error fetching {url_type}: {e}")
    
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
        raise HTTPException(status_code=404, detail="Could not fetch product data from any endpoint")
    
    return result
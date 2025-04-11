from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
import logging

from app.models.schemas import ProductResponse
from app.services.scraper import scrape_product_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/product')

@router.post("/search-by-id/{product_id}", response_model=ProductResponse)
async def get_product_by_id(
    product_id: int = Path(..., description="The product ID from 1688.com")
):
    """
    Get product details from 1688.com by product ID.
    
    This endpoint fetches both retail and wholesale data from the product page.
    """
    try:
        product_data = await scrape_product_data(product_id)
        
        # Success response format
        return {
            "code": 200,
            "msg": "success",
            "data": product_data
        }
    except HTTPException as e:
        # Re-raise the HTTP exception
        raise e
    except Exception as e:
        logger.exception(f"Error fetching product data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
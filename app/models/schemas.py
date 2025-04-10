from pydantic import BaseModel
from typing import Dict, Any, Optional

class ErrorResponse(BaseModel):
    code: int
    message: str

class ProductResponse(BaseModel):
    code: int
    msg: str
    data: Dict[str, Any]
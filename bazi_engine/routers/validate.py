"""
routers/validate.py — POST /validate (contract-first BAFE validator)
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..bafe import validate_request as bafe_validate_request

router = APIRouter(tags=["Validation"])


@router.post("/validate")
async def validate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Contract-first validator (JSON Schema Draft-07)."""
    try:
        return bafe_validate_request(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal validation error")

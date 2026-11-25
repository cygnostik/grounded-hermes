"""FastAPI routes for the Grounded News Desktop view."""

import importlib.util
from pathlib import Path

from fastapi import APIRouter

# Hermes loads dashboard API files as standalone modules.
_path = Path(__file__).resolve().parents[1] / "grounded" / "service.py"
_spec = importlib.util.spec_from_file_location("_grounded_hermes_dashboard_service", _path)
_service = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_service)

router = APIRouter()


@router.post("/read/{operation}")
def read(operation: str, args: dict):
    return _service.execute(operation, args)

from fastapi import APIRouter
from typing import List, Dict, Any
from src.config.student_config import SCHOOLS, GRADES, SECTIONS

router = APIRouter(
    prefix="/api/config",
    tags=["configuration"]
)

@router.get("/student-options")
async def get_student_options() -> Dict[str, Any]:
    """
    Get available options for student login (schools, grades, sections).
    Used to populate dropdowns in the frontend.
    """
    return {
        "schools": SCHOOLS,
        "grades": GRADES,
        "sections": SECTIONS
    }

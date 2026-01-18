"""Form filling API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
import os

from ..models import (
    FormFillingResponse,
    FormFillingStatus,
    ErrorResponse
)
from ..services import (
    SessionManager,
    get_session_manager,
    FormFillerService
)

router = APIRouter(prefix="/form", tags=["Form"])


def get_form_filler() -> FormFillerService:
    return FormFillerService()


@router.post(
    "/{session_id}/fill",
    response_model=FormFillingResponse,
    summary="Fill scholarship form",
    description="Fill the scholarship eligibility form with session data",
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse}
    }
)
async def fill_form(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    form_filler: FormFillerService = Depends(get_form_filler)
):
    """Fill the scholarship form with extracted data"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    filled_data = session.get_filled_data()
    if not filled_data:
        raise HTTPException(
            status_code=400, 
            detail="No data collected yet. Please provide information first."
        )
    
    # Update session status
    session.form_filling_status = "in_progress"
    
    # Fill form
    success, message, errors, screenshot_path = await form_filler.fill_form(
        filled_data, 
        session_id
    )
    
    # Update session
    session.form_filling_status = "completed" if success else "failed"
    session.form_screenshot_path = screenshot_path
    session.form_errors = errors
    
    # Determine status
    if success and not errors:
        status = FormFillingStatus.CAPTCHA_REQUIRED
    elif success and errors:
        status = FormFillingStatus.CAPTCHA_REQUIRED
    else:
        status = FormFillingStatus.FAILED
    
    return FormFillingResponse(
        session_id=session_id,
        status=status,
        message=message,
        screenshot_url=f"/form/{session_id}/screenshot" if screenshot_path else None,
        errors=errors
    )


@router.get(
    "/{session_id}/status",
    response_model=FormFillingResponse,
    summary="Get form filling status",
    responses={404: {"model": ErrorResponse}}
)
async def get_form_status(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get the current status of form filling"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    status_map = {
        "pending": FormFillingStatus.PENDING,
        "in_progress": FormFillingStatus.IN_PROGRESS,
        "completed": FormFillingStatus.CAPTCHA_REQUIRED,
        "failed": FormFillingStatus.FAILED
    }
    
    return FormFillingResponse(
        session_id=session_id,
        status=status_map.get(session.form_filling_status, FormFillingStatus.PENDING),
        message=f"Form filling status: {session.form_filling_status}",
        screenshot_url=f"/form/{session_id}/screenshot" if session.form_screenshot_path else None,
        errors=session.form_errors
    )


@router.get(
    "/{session_id}/screenshot",
    summary="Get form screenshot",
    description="Get the screenshot of the filled form",
    responses={
        404: {"description": "Screenshot not found"},
        200: {"content": {"image/png": {}}}
    }
)
async def get_screenshot(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    form_filler: FormFillerService = Depends(get_form_filler)
):
    """Get the form screenshot"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    screenshot_path = session.form_screenshot_path or form_filler.get_screenshot_path(session_id)
    
    if not screenshot_path or not os.path.exists(screenshot_path):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(
        screenshot_path,
        media_type="image/png",
        filename=f"form_{session_id}.png"
    )


@router.get(
    "/{session_id}/preview",
    summary="Preview form data",
    description="Preview the data that will be used to fill the form"
)
async def preview_form_data(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Preview the extracted data before filling"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    filled_data = session.get_filled_data()
    
    # Map to form fields for preview
    text_fields = {
        "name": "Full Name",
        "annual_family_income": "Annual Family Income",
        "xii_roll_no": "12th Roll Number",
        "twelfthPercentage": "12th Percentage",
        "x_roll_no": "10th Roll Number",
        "tenthPercentage": "10th Percentage",
        "competitiveRollno": "Competitive Exam Roll No",
        "dob": "Date of Birth"
    }
    
    dropdown_fields = {
        "d_state_id": "State",
        "gender": "Gender",
        "religion": "Religion",
        "community": "Community/Category",
        "maritalStatus": "Marital Status",
        "c_course_id": "Course",
        "parent_profession": "Parent Profession",
        "hosteler": "Hosteler",
        "competitiveExam": "Competitive Exam"
    }
    
    preview = {
        "session_id": session_id,
        "text_fields": {
            text_fields.get(k, k): v 
            for k, v in filled_data.items() 
            if k in text_fields
        },
        "dropdown_fields": {
            dropdown_fields.get(k, k): v 
            for k, v in filled_data.items() 
            if k in dropdown_fields
        },
        "total_fields_filled": len(filled_data),
        "ready_to_fill": len(filled_data) >= 3  # At least 3 fields
    }
    
    return preview

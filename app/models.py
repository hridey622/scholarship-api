"""Pydantic models for API request/response schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FILLING = "filling"


class FormFillingStatus(str, Enum):
    """Form filling status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CAPTCHA_REQUIRED = "captcha_required"


# ─── Request Models ─────────────────────────────────────────────────────────

class TextInput(BaseModel):
    """Text input from user"""
    text: str = Field(..., min_length=1, description="User's text input")


class CommandInput(BaseModel):
    """Command input (skip, repeat, etc.)"""
    command: str = Field(..., description="Command: skip, repeat, show, fill")


# ─── Response Models ────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    """Response when creating/querying a session"""
    session_id: str
    status: SessionStatus
    created_at: datetime
    current_group_index: int
    total_groups: int
    message: str = ""


class QuestionGroup(BaseModel):
    """A group of questions to ask the user"""
    title: str
    intro: str
    questions: List[str]
    group_index: int
    is_last: bool


class ExtractedData(BaseModel):
    """Extracted scholarship form data"""
    name: Optional[str] = None
    gender: Optional[str] = None
    d_state_id: Optional[str] = None
    religion: Optional[str] = None
    community: Optional[str] = None
    annual_family_income: Optional[str] = None
    c_course_id: Optional[str] = None
    maritalStatus: Optional[str] = None
    hosteler: Optional[str] = None
    dob: Optional[str] = None
    xii_roll_no: Optional[str] = None
    twelfthPercentage: Optional[str] = None
    x_roll_no: Optional[str] = None
    tenthPercentage: Optional[str] = None
    parent_profession: Optional[str] = None
    competitiveExam: Optional[str] = None
    competitiveRollno: Optional[str] = None


class DataResponse(BaseModel):
    """Response with extracted data"""
    session_id: str
    data: ExtractedData
    fields_filled: int
    total_fields: int
    completion_percentage: float


class TranscriptionResponse(BaseModel):
    """Response from audio transcription"""
    session_id: str
    transcribed_text: str
    extracted_data: ExtractedData
    message: str


class TextProcessResponse(BaseModel):
    """Response from text processing"""
    session_id: str
    input_text: str
    extracted_data: ExtractedData
    fields_updated: List[str]
    message: str


class FormFillingResponse(BaseModel):
    """Response from form filling operation"""
    session_id: str
    status: FormFillingStatus
    message: str
    screenshot_url: Optional[str] = None
    errors: List[str] = []


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    ollama_status: str
    bhashini_status: str

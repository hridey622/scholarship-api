"""Session management API endpoints"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import Optional

from ..models import (
    SessionResponse, 
    SessionStatus,
    TextInput,
    TextProcessResponse,
    TranscriptionResponse,
    DataResponse,
    QuestionGroup,
    ErrorResponse
)
from ..services import (
    SessionManager, 
    get_session_manager,
    SpeechService,
    ExtractionService
)

router = APIRouter(prefix="/session", tags=["Session"])


def get_speech_service() -> SpeechService:
    return SpeechService()


def get_extraction_service() -> ExtractionService:
    return ExtractionService()


@router.post(
    "/start",
    response_model=SessionResponse,
    summary="Start a new session",
    description="Create a new session for scholarship form data collection"
)
async def start_session(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a new session and return session details"""
    session = session_manager.create_session()
    
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
        current_group_index=session.group_index,
        total_groups=len(session_manager.QUESTION_GROUPS),
        message="Session created. Start by getting current questions with GET /session/{id}/questions"
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session status",
    responses={404: {"model": ErrorResponse}}
)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get current session status"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
        current_group_index=session.group_index,
        total_groups=len(session_manager.QUESTION_GROUPS),
        message=""
    )


@router.get(
    "/{session_id}/questions",
    response_model=Optional[QuestionGroup],
    summary="Get current question group",
    responses={404: {"model": ErrorResponse}}
)
async def get_questions(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get the current set of questions for the session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    questions = session_manager.get_current_questions(session_id)
    if not questions:
        return None  # All questions completed
    
    return QuestionGroup(**questions)


@router.post(
    "/{session_id}/text",
    response_model=TextProcessResponse,
    summary="Process text input",
    description="Send text answers and extract scholarship data",
    responses={404: {"model": ErrorResponse}}
)
async def process_text(
    session_id: str,
    text_input: TextInput,
    session_manager: SessionManager = Depends(get_session_manager),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """Process text input and extract scholarship information"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Add to chat history
    session.add_message("user", text_input.text)
    
    # Extract data using LLM
    extracted = await extraction_service.extract(
        text_input.text,
        session.chat_history
    )
    
    fields_updated = []
    if extracted:
        fields_updated = session.update_data(extracted)
        session.add_message("assistant", f"Extracted: {extracted}")
    
    # Advance to next question group
    session.advance_group()
    
    return TextProcessResponse(
        session_id=session_id,
        input_text=text_input.text,
        extracted_data=session.get_extracted_data(),
        fields_updated=fields_updated,
        message=f"Processed. {len(fields_updated)} fields updated."
    )


@router.post(
    "/{session_id}/audio",
    response_model=TranscriptionResponse,
    summary="Process audio input",
    description="Upload audio file for transcription and data extraction",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}}
)
async def process_audio(
    session_id: str,
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    session_manager: SessionManager = Depends(get_session_manager),
    speech_service: SpeechService = Depends(get_speech_service),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """Process audio input: transcribe and extract scholarship information"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Read audio file
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    # Transcribe audio
    transcribed_text = await speech_service.transcribe_audio(audio_bytes)
    if not transcribed_text:
        raise HTTPException(
            status_code=400, 
            detail="Could not transcribe audio. Please speak clearly and try again."
        )
    
    # Add to chat history
    session.add_message("user", transcribed_text)
    
    # Extract data using LLM  
    extracted = await extraction_service.extract(
        transcribed_text,
        session.chat_history
    )
    
    if extracted:
        session.update_data(extracted)
        session.add_message("assistant", f"Extracted: {extracted}")
    
    # Advance to next question group
    session.advance_group()
    
    return TranscriptionResponse(
        session_id=session_id,
        transcribed_text=transcribed_text,
        extracted_data=session.get_extracted_data(),
        message="Audio processed and data extracted."
    )


@router.get(
    "/{session_id}/data",
    response_model=DataResponse,
    summary="Get extracted data",
    description="Get all extracted scholarship data for the session",
    responses={404: {"model": ErrorResponse}}
)
async def get_data(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get all extracted data for the session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    filled_data = session.get_filled_data()
    total_fields = len(session.data)
    fields_filled = len(filled_data)
    
    return DataResponse(
        session_id=session_id,
        data=session.get_extracted_data(),
        fields_filled=fields_filled,
        total_fields=total_fields,
        completion_percentage=round((fields_filled / total_fields) * 100, 1)
    )


@router.post(
    "/{session_id}/skip",
    response_model=SessionResponse,
    summary="Skip current question group",
    responses={404: {"model": ErrorResponse}}
)
async def skip_group(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Skip the current question group and move to the next"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    session.advance_group()
    
    is_finished = session_manager.is_finished(session_id)
    
    return SessionResponse(
        session_id=session.session_id,
        status=SessionStatus.COMPLETED if is_finished else SessionStatus.ACTIVE,
        created_at=session.created_at,
        current_group_index=session.group_index,
        total_groups=len(session_manager.QUESTION_GROUPS),
        message="Question group skipped." if not is_finished else "All question groups completed."
    )


@router.delete(
    "/{session_id}",
    summary="Delete session",
    responses={404: {"model": ErrorResponse}}
)
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Delete a session and all associated data"""
    if session_manager.delete_session(session_id):
        return {"message": "Session deleted successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

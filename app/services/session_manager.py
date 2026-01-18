"""Session management service with in-memory storage"""
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from functools import lru_cache

from ..config import get_settings
from ..models import SessionStatus, ExtractedData


class Session:
    """Individual session data container"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.status = SessionStatus.ACTIVE
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.group_index = 0
        self.chat_history: List[Dict[str, str]] = []
        self.data: Dict[str, Optional[str]] = {
            "name": None, 
            "gender": None, 
            "d_state_id": None, 
            "religion": None,
            "community": None, 
            "annual_family_income": None, 
            "c_course_id": None,
            "maritalStatus": None, 
            "hosteler": None, 
            "dob": None,
            "xii_roll_no": None, 
            "twelfthPercentage": None,
            "x_roll_no": None, 
            "tenthPercentage": None,
            "parent_profession": None, 
            "competitiveExam": None, 
            "competitiveRollno": None
        }
        self.form_filling_status = "pending"
        self.form_screenshot_path: Optional[str] = None
        self.form_errors: List[str] = []
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def add_message(self, role: str, content: str):
        """Add message to chat history"""
        self.chat_history.append({"role": role, "content": content})
        self.update_activity()
    
    def update_data(self, new_data: Dict[str, Any]) -> List[str]:
        """Update extracted data, returns list of updated fields"""
        updated_fields = []
        for key, value in new_data.items():
            if key in self.data and value and value not in ("null", "NULL", "", None):
                clean_value = str(value).strip()
                if self.data[key] != clean_value:
                    self.data[key] = clean_value
                    updated_fields.append(key)
        self.update_activity()
        return updated_fields
    
    def get_filled_data(self) -> Dict[str, str]:
        """Get only the filled data fields"""
        return {k: v for k, v in self.data.items() if v is not None}
    
    def get_extracted_data(self) -> ExtractedData:
        """Get data as ExtractedData model"""
        return ExtractedData(**self.data)
    
    def advance_group(self):
        """Move to next question group"""
        self.group_index += 1
        self.update_activity()
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if session has expired"""
        expiry_time = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry_time


class SessionManager:
    """Thread-safe session manager with automatic cleanup"""
    
    # Question groups (same as original)
    QUESTION_GROUPS = [
        {
            "title": "Personal Details - Part 1",
            "intro": "Let's start with some basic information.",
            "questions": [
                "What is your full name?",
                "What is your gender? (Male, Female, or Others)",
                "Which state do you belong to? (full name, like DELHI or KARNATAKA)",
                "What is your religion? (Hindu, Muslim, Christian, Sikh, etc.)"
            ]
        },
        {
            "title": "Personal & Family Details - Part 2",
            "intro": "Thank you. Now some more personal and family details.",
            "questions": [
                "What is your date of birth? (DD/MM/YYYY)",
                "Are you married? (Married / Unmarried / Divorced / Widowed)",
                "Do you live in a hostel right now? (Yes / No)",
                "What is your family's annual income? (only number, example 360000)",
                "What category do you belong to? (General / OBC / SC / ST)"
            ]
        },
        {
            "title": "Education Details",
            "intro": "Great. Now let's talk about your education.",
            "questions": [
                "Which course are you studying or have completed? (example: Class 12, B.Tech, MBBS)",
                "What was your 10th class roll number?",
                "What percentage did you get in 10th?",
                "What was your 12th class roll number? (if applicable)",
                "What percentage did you get in 12th? (if applicable)"
            ]
        },
        {
            "title": "Additional / Special Information",
            "intro": "Almost done. Just a few more details.",
            "questions": [
                "What is your parent's or guardian's profession? (or say None)",
                "Are you applying through any competitive exam? (example: NMMS, or say No)",
                "If yes, what is the roll number of that exam?",
                "Is there anything else important you want to tell me?"
            ]
        }
    ]
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self._settings = get_settings()
    
    def create_session(self) -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        
        with self._lock:
            self._sessions[session_id] = session
            self._cleanup_expired()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                if session.is_expired(self._settings.session_timeout_minutes):
                    session.status = SessionStatus.EXPIRED
                    return None
                session.update_activity()
            return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
    
    def get_current_questions(self, session_id: str) -> Optional[Dict]:
        """Get current question group for session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        if session.group_index >= len(self.QUESTION_GROUPS):
            return None
        
        group = self.QUESTION_GROUPS[session.group_index]
        return {
            "title": group["title"],
            "intro": group["intro"],
            "questions": group["questions"],
            "group_index": session.group_index,
            "is_last": session.group_index >= len(self.QUESTION_GROUPS) - 1
        }
    
    def is_finished(self, session_id: str) -> bool:
        """Check if all question groups are completed"""
        session = self.get_session(session_id)
        if not session:
            return True
        return session.group_index >= len(self.QUESTION_GROUPS)
    
    def _cleanup_expired(self):
        """Remove expired sessions (called internally with lock held)"""
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(self._settings.session_timeout_minutes)
        ]
        for sid in expired:
            del self._sessions[sid]
    
    def get_stats(self) -> Dict:
        """Get session statistics"""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": sum(
                    1 for s in self._sessions.values() 
                    if s.status == SessionStatus.ACTIVE
                )
            }


# Singleton instance
_session_manager: Optional[SessionManager] = None
_manager_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    """Get singleton session manager instance"""
    global _session_manager
    if _session_manager is None:
        with _manager_lock:
            if _session_manager is None:
                _session_manager = SessionManager()
    return _session_manager

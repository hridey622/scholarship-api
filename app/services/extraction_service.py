"""LLM-based extraction service using Ollama"""
import re
import json
import httpx
from typing import Dict, Any, Optional, List

from ..config import get_settings


class ExtractionService:
    """Service for extracting structured data from conversation using LLM"""
    
    SYSTEM_PROMPT = """You are a scholarship application assistant.
Extract only clearly mentioned information.
Return ONLY valid JSON object. Do not add explanations."""

    INSTRUCTION_PROMPT = """
Extract/update ALL known information from the FULL conversation so far. Match the fields given by user only with the possible options provided below. 
Return ONLY valid JSON with these exact fields (null if unknown):

- name                   // write exactly same name given by user, don't change any spelling, make the first letter of first name , middle name and surname if provided to uppercase 
- gender                 // Male / Female / Others
- d_state_id             // full state name in Capital letters e.g. "ANDHRA PRADESH"
- religion               // Hindu / Muslim / Christian / Sikh / Buddhist / Jain / Parsi / Other
- community              // SC / ST / OBC / General
- annual_family_income   // number only
- c_course_id            // MBBS / B.Tech / Class 12 / Class 10
- maritalStatus          // Married / Un Married / Divorced / Widowed
- hosteler               // Yes / No
- dob                    // DD/MM/YYYY or any clear format
- xii_roll_no
- twelfthPercentage      // number
- x_roll_no
- tenthPercentage        // number
- parent_profession      // Beedi Worker / Central Armed Police Forces & Assam Rifles (CAPFs/AR) / Cine Worker / Ex-RPF / Ex-RPSF / Flayers /
Iron Ore, Manganese Ore & Chrome Ore Mine (IOMC) Workers /  Limestone & Dolomite Mine (LSDM) Workers /  Others / Scavengers / Serving RPF / Serving RPSF / State Police Personnel(Martyred in Terrorist/Naxalite Violence) /
Sweepers / Tanner / Waste Pickers                          
- competitiveExam        // NMMS / PM-USP SSSJKL / STATE COMPETITIVE SCHOLARSHIP EXAM FOR CLASS V AND VIII - MANIPUR / STATE TALENT SEARCH EXAM (STSE) IN MATHS-SCIENCE FOR ST STUDENTS OF CLASS VIII - MEGHALAYA 
- competitiveRollno      // 

Current conversation:"""

    def __init__(self):
        self._settings = get_settings()
    
    async def extract(
        self, 
        user_input: str, 
        chat_history: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from user input using conversation context.
        
        Args:
            user_input: Latest user input text
            chat_history: Previous conversation messages
            
        Returns:
            Extracted data dictionary or None if failed
        """
        if not user_input.strip():
            return None
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.INSTRUCTION_PROMPT},
            *chat_history[-12:],  # Last 12 messages for context
            {"role": "user", "content": user_input}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self._settings.ollama_url}/api/chat",
                    json={
                        "model": self._settings.ollama_model,
                        "messages": messages,
                        "stream": False,
                        "temperature": 0.15
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                content = result.get("message", {}).get("content", "").strip()
                
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    extracted = json.loads(json_match.group(0))
                    return extracted
                
                return None
                
        except httpx.HTTPError as e:
            print(f"Ollama API error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            print(f"Extraction error: {e}")
            return None
    
    async def check_health(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._settings.ollama_url}/api/tags")
                if response.status_code == 200:
                    tags = response.json()
                    models = [m.get("name", "") for m in tags.get("models", [])]
                    return any(self._settings.ollama_model in m for m in models)
                return False
        except Exception:
            return False

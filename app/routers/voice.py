from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import tempfile
import os
from app.models.database import SessionLocal
from app.services.voice_service import voice_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    """Transcribe voice audio to text"""
    try:
        # Validate file type
        if not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Audio file required")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Process voice
        transcription = voice_service.process_voice_order(temp_file_path)
        
        # Clean up
        os.unlink(temp_file_path)
        
        if transcription:
            return {
                "status": "success",
                "transcription": transcription,
                "message": "Voice successfully processed"
            }
        else:
            return {
                "status": "error", 
                "transcription": "",
                "message": "Voice samajh mein nahi aayi"
            }
            
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/voice-supported")
async def check_voice_support():
    """Check if voice recognition is supported"""
    return {
        "voice_supported": True,
        "languages": voice_service.supported_languages(),
        "models": ["Whisper (Free)", "Google Speech Recognition"],
        "status": "active"
    }
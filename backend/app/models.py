from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import uuid

class QuestionCreate(BaseModel):
    domain: str
    question_text: str
    code: Optional[str] = None
    options: List[str]
    correct_answer: str
    explanation: str

class QuestionUpdate(BaseModel):
    domain: Optional[str] = None
    question_text: Optional[str] = None
    code: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

class QuestionResponse(QuestionCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    pass

class SessionResponse(BaseModel):
    sessionId: str
    questions: List[Any]
    
class SessionSubmit(BaseModel):
    answers: dict[str, int]

class SessionResult(BaseModel):
    sessionId: str
    totalQuestions: int
    correctAnswers: int
    score: float
    passed: bool
    domainBreakdown: dict

class SessionListItem(BaseModel):
    id: str
    created_at: datetime
    completed_at: Optional[datetime]
    score: Optional[float]
    passed: Optional[bool]
    
    class Config:
        from_attributes = True

def generate_session_id():
    return str(uuid.uuid4())

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 회원가입 요청
class UserCreate(BaseModel):
    email: str
    password: str  # pwd → password
    name: str
    dept: Optional[str] = None
    job: Optional[str] = None

# 로그인 요청
class UserLogin(BaseModel):
    email: str
    password: str  # pwd → password

# 사용자 응답
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

# 텍스트 분석 요청
class TextAnalyze(BaseModel):
    text: str

# 교정 결과 응답
class CorrectionResponse(BaseModel):
    original_text: str
    corrected_texts: List[str]  # 교정 문장 3가지
    aggression_score: float
    emotion_score: float
    politeness_score: float

# 교정 기록 저장
class CorrectionCreate(BaseModel):
    user_id: int
    original_text: str
    corrected_text: str
    aggression_score: Optional[float] = None
    emotion_score: Optional[float] = None
    politeness_score: Optional[float] = None
    tone_type: Optional[str] = None

# 교정 기록 조회 응답
class CorrectionHistory(BaseModel):
    id: int
    original_text: str
    corrected_text: str
    tone_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class SaveCorrection(BaseModel):
    upload_text: str
    corr_text: str
    tone_type: str
    selected_tone: str  # polite / friendly / firm

class UserUpdate(BaseModel):
    name: Optional[str] = None
    dept: Optional[str] = None
    job: Optional[str] = None
    current_password: Optional[str] = None  # 현재 비번 확인용
    new_password: Optional[str] = None      # 새 비번
    consent: Optional[bool] = None
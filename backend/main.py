from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base, User, Correction
from schemas import UserCreate, UserLogin, TextAnalyze, CorrectionCreate
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from embedding import search_similar
from LLM import generate_correction
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer
from embedding import get_vector
from schemas import UserCreate, UserLogin, TextAnalyze, CorrectionCreate, SaveCorrection
from embedding import search_similar, search_history
from schemas import UserCreate, UserLogin, TextAnalyze, CorrectionCreate, SaveCorrection, UserUpdate
import os
import httpx
import logging
import traceback
from contextlib import asynccontextmanager
from scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="토큰이 유효하지 않습니다")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="토큰이 유효하지 않습니다")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# 비밀번호 암호화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = "toneguard_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@app.get("/")
def root():
    return {"message": "ToneGuard API 서버 실행 중"}

@app.get("/db-test")
def db_test():
    try:
        with engine.connect() as conn:
            return {"status": "DB 연결 성공!"}
    except Exception as e:
        return {"status": "DB 연결 실패", "error": str(e)}

# 회원가입
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    new_user = User(
        email=user.email,
        pwd=user.password,
        name=user.name,
        dept=user.dept,
        job=user.job,
        profile_img=''
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "회원가입 성공!", "user_id": new_user.id}

# 로그인
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="이메일 또는 비밀번호가 틀렸습니다")
    if db_user.pwd != user.password:
        raise HTTPException(status_code=400, detail="이메일 또는 비밀번호가 틀렸습니다")
    token = create_token({"sub": db_user.email, "user_id": db_user.id})
    return {"access_token": token, "token_type": "bearer", "user_id": db_user.id}

@app.post("/save")
def save(request: SaveCorrection, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    try:
        from embedding import get_vector
        correction = Correction(
            id=user_id,
            upload_text=request.upload_text,
            upload_vector=get_vector(request.upload_text),
            corr_text=request.corr_text,
            tone_type=request.tone_type
        )
        db.add(correction)
        db.commit()
        return {"message": "저장 완료!"}
    except Exception as e:
        logger.exception(f"❌ /save 에러")  # 스택 트레이스 자동 포함
        raise HTTPException(status_code=500, detail=str(e)) 

@app.post("/analyze")
def analyze(request: TextAnalyze, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    try:
        print(f"📩 수신 텍스트: {request.text}")

        # 1. 맥락 예측 + 유사 텍스트 검색
        similar_texts, context_type = search_similar(request.text)

        # 2. 히스토리 검색  ← 이게 빠진 거야!
        history = search_history(request.text, user_id)

        # 3. Ollama로 교정 문장 생성
        result = generate_correction(request.text, similar_texts, context_type, history)

        print(f"✅ 교정 결과: {result}")

        return {
            "original": request.text,
            "context_type": context_type,
            "corrections": {
                "polite": result.get('polite', ''),
                "friendly": result.get('friendly', ''),
                "firm": result.get('firm', '')
            }
        }

    except Exception as e:
        logger.exception(f"❌ /analyze 에러")  # 스택 트레이스 자동 포함
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user")
def get_user(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "dept": user.dept,
            "job": user.job,
            "profile_img": user.profile_img,
            "joined_at": user.joined_at,
            "consent": user.consent
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ /user GET 에러")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/user")
def update_user(request: UserUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        if request.name: user.name = request.name
        if request.dept: user.dept = request.dept
        if request.job: user.job = request.job
        if request.consent is not None: user.consent = request.consent  # 추가

        if request.new_password:
            if not request.current_password:
                raise HTTPException(status_code=400, detail="현재 비밀번호를 입력해주세요")
            if user.pwd != request.current_password:
                raise HTTPException(status_code=400, detail="현재 비밀번호가 틀렸습니다")
            user.pwd = request.new_password

        db.commit()
        return {"message": "개인정보 수정 완료!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ /user PUT 에러")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/user")
def delete_user(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    try:
        # 교정 기록 먼저 삭제
        db.query(Correction).filter(Correction.id == user_id).delete(synchronize_session=False)
        # 사용자 삭제 (교정 기록은 CASCADE로 자동 삭제)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        db.delete(user)
        db.commit()
        return {"message": "회원 탈퇴 완료!"}

    except Exception as e:
        logger.exception(f"❌ /user DELETE 에러")  # 스택 트레이스 자동 포함
        raise HTTPException(status_code=500, detail=str(e)) 

@app.get("/history")
def get_history(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    try:
        corrections = db.query(Correction).filter(
            Correction.id == user_id
        ).order_by(
            Correction.created_at.desc()
        ).all()

        return {
            "history": [
                {
                    "corr_idx": c.corr_idx,
                    "upload_text": c.upload_text,
                    "corr_text": c.corr_text,
                    "tone_type": c.tone_type,
                    "created_at": c.created_at
                }
                for c in corrections
            ]
        }
    except Exception as e:
        logger.exception(f"❌ /history GET 에러")  # 스택 트레이스 자동 포함
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history")
def delete_history(corr_idxs: list[int] = Query(...), db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    records = db.query(Correction).filter(
        Correction.corr_idx.in_(corr_idxs),
        Correction.id == user_id
    ).all()
    if not records:
        raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다")
    for record in records:
        db.delete(record)
    db.commit()
    return {"message": f"교정 기록 {len(records)}건 삭제 완료!"}

@app.delete("/history/all")
def delete_all_history(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    deleted = db.query(Correction).filter(Correction.id == user_id).delete(synchronize_session=False)
    db.commit()
    return {"message": f"교정 기록 전체 삭제 완료! ({deleted}건)"}

@app.get("/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    return {"available": existing is None}
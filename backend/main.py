from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base, User, Correction
from schemas import UserCreate, UserLogin, TextAnalyze, CorrectionCreate
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from embedding import search_similar
from LLM import generate_correction

app = FastAPI()

Base.metadata.create_all(bind=engine)

# 비밀번호 암호화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = "toneguard_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

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
    hashed_pw = hash_password(user.password)
    new_user = User(email=user.email, password=hashed_pw, name=user.name)
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
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="이메일 또는 비밀번호가 틀렸습니다")
    token = create_token({"sub": db_user.email, "user_id": db_user.id})
    return {"access_token": token, "token_type": "bearer", "user_id": db_user.id}

# 텍스트 분석
@app.post("/analyze")
def analyze(request: TextAnalyze, db: Session = Depends(get_db)):
    try:
        # 1. 맥락 예측 + 유사 텍스트 검색
        similar_texts, context_type = search_similar(request.text)

        # 2. Ollama로 교정 문장 생성
        result = generate_correction(request.text, similar_texts, context_type)

        # 3. DB에 교정 기록 저장
        correction = Correction(
            upload_text=request.text,
            corr_text=result.get('polite', ''),
            tone_type=context_type
        )
        db.add(correction)
        db.commit()

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
        raise HTTPException(status_code=500, detail=str(e))
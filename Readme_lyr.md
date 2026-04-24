# 🛡 ToneGuard - AI 기반 직장 메신저 말투 교정 시스템
> 직장 내 메신저 전송 전 실시간으로 말투를 분석하고 교정해주는 **AI 기반 소통 보조 도구**
![Python](https://img.shields.io/badge/Python-3.13+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-brightgreen?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green)

## 📌 프로젝트 개요
**ToneGuard**는 직장 내 메신저(카카오톡, Slack, 텔레그램 등)에서 메시지를 작성할 때 **AI가 실시간으로 대화 맥락을 분석하고 적절한 톤으로 문장을 교정**해주는 서비스입니다.
### 핵심 기능
- 🎯 **실시간 톤 교정**: 3가지 톤(정중하게, 친근하게, 단호하게)으로 자동 교정
- 🧠 **맥락 인식 AI**: 5가지 업무 상황(업무, 사과, 피드백, 의견충돌, 일상) 자동 분류
- 💾 **개인화 학습**: 사용자의 이전 교정 기록을 반영한 스타일 학습
- 🔐 **안전한 통신**: JWT 기반 인증, 사용자 개인정보 보호
- 📊 **교정 기록 관리**: 모든 교정 내역 저장 및 조회 기능

## 🏗 시스템 아키텍처
<img width="290" height="518" alt="image" src="https://github.com/user-attachments/assets/12e6005f-040a-4706-ad0e-eea4cbb4778b" />

## 🧠 AI 처리 흐름
사용자 메시지 작성
       ↓
[1] 텍스트 벡터화 (KoBERT)
    - 입력 문장을 768차원 벡터로 변환
       ↓
[2] 맥락 분류 (KoBERT + MLP 분류기)
    - 5가지 업무 상황 중 최적의 맥락 선택
    - 신뢰도 60% 이상이면 확정, 이하면 "불명확"
       ↓
[3] 유사 문장 검색 (pgvector L2 거리)
    ├─ 확정: 해당 맥락의 유사 문장 3개 검색
    └─ 불명확: 전체 데이터에서 유사 문장 3개 검색
       ↓
[4] 사용자 히스토리 검색
    - 사용자의 이전 교정 기록 3개 검색
    - 개인 선호 톤 반영 학습
       ↓
[5] LLM 교정 (Ollama exaone3.5:7.8b)
    - 참고 문장 + 히스토리 + 프롬프트로 3가지 톤 생성
    - 정중하게 / 친근하게 / 단호하게
       ↓
사용자에게 3가지 톤 제시 → 선택 → 메신저에 자동 입력

## 📂 프로젝트 구조
TEAM1/
├── README.md                    # 이 파일
├── backend/                     # 백엔드 서버 (핵심 AI 처리)
│   ├── main.py                  # FastAPI 메인 서버
│   ├── database.py              # PostgreSQL 연결 설정
│   ├── models.py                # SQLAlchemy ORM 테이블 정의
│   ├── schemas.py               # Pydantic 데이터 스키마
│   ├── embedding.py             # KoBERT + 맥락 분류 + 검색 로직
│   ├── LLM.py                   # Ollama 기반 교정 문장 생성
│   ├── train.py                 # KoBERT + MLP 분류기 학습 스크립트
│   ├── insert_data.py           # 학습 데이터 DB 삽입
│   ├── merge_data.py            # 데이터 병합 유틸리티
│   ├── scheduler.py             # 자동 삭제 스케줄러 (90일 주기)
│   ├── kobert.py                # KoBERT 감정 분석 (참고용)
│   ├── test.py                  # 테스트 스크립트
│   ├── context_classifier.pkl   # 학습된 맥락 분류 모델 (16MB)
│   ├── data.ipynb               # 데이터 분석 노트북
│   ├── data/                    # 학습 데이터
│   │   └── merged_data_4class.xlsx
│   └── __pycache__/
│├── front/                       # 프론트엔드 서버 (웹 UI + 프록시)
│   ├── main.py                  # FastAPI 프론트 서버 (8888 포트)
│   ├── scan_corr.py             # 데스크톱 스캐너 GUI
│   ├── readme.md                # 프론트 실행 가이드
│   ├── templates/               # HTML 템플릿
│   │   ├── index.html           # 메인 홈페이지
│   │   ├── login.html           # 로그인/회원가입
│   │   └── mypage.html          # 마이페이지 (기록, 설정)
│   └── static/                  # 정적 파일 (CSS, JS, 이미지)
│└── 프론트4.17본/                # 아카이브 폴더


## 🔧 기술 스택
| 계층 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **Backend** | FastAPI | Latest | REST API 서버 |
| **Frontend** | FastAPI + Jinja2 | Latest | 웹 UI + 프록시 |
| **Desktop GUI** | CustomTkinter | Latest | 메신저 감지 앱 |
| **Language Model** | Ollama | exaone3.5:7.8b | 텍스트 교정 생성 |
| **Embedding** | KoBERT | monologg/kobert | 텍스트 벡터화 |
| **Classification** | KoBERT + MLP | Custom Trained | 맥락 분류 (83% 정확도) |
| **Database** | PostgreSQL | pgvector 확장 | 벡터 저장 + 검색 |
| **ORM** | SQLAlchemy | Latest | DB 매핑 |
| **Authentication** | JWT | python-jose | 사용자 인증 |
| **Password Hash** | Passlib + bcrypt | Latest | 비밀번호 암호화 |

## 📊 모델 성능
### KoBERT + MLP 맥락 분류기
- **정확도**: 83%
- **학습 데이터**: 5,344개 문장
- **분류 클래스**: 5가지 (업무, 사과, 피드백, 의견충돌, 일상)
| 맥락 | F1-Score | 설명 |
|------|----------|------|
| 💼 업무 | 0.81 | 업무 지시, 보고 등 |
| 🙏 사과 | 0.88 | 사과, 양해 요청 |
| 💬 피드백 | 0.85 | 의견, 피드백 |
| ⚡ 의견충돌 | 0.81 | 이의, 반박 |
| 😊 일상 | 0.82 | 인사, 일상 대화 |

## 🚀 빠른 시작
### 1⃣ 필수 요구사항

- Python 3.13+
- PostgreSQL (pgvector 확장 포함)
- Ollama (exaone3.5:7.8b 모델)
- Windows 10/11 (데스크톱 앱용)

### 2⃣ 백엔드 설치 및 실행
# 백엔드 폴더 이동
cd backend
# 패키지 설치
pip install fastapi uvicorn sqlalchemy psycopg2-binary pgvector
pip install kobert-transformers transformers torch
pip install python-jose passlib python-dotenv
pip install pandas openpyxl scikit-learn
pip install ollama apscheduler
# Ollama 모델 다운로드
ollama pull exaone3.5:7.8b
# 서버 실행 (포트 8000)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

### 3⃣ 프론트엔드 설치 및 실행
# 프론트엔드 폴더 이동
cd front
# 패키지 설치
pip install fastapi uvicorn customtkinter pygetwindow pyautogui pyperclip requests
# 서버 실행 (포트 8888)
python main.py

### 4⃣ 브라우저에서 접속

http://localhost:8888

## 📡 API 엔드포인트
### 인증 (Authentication)
| 메서드 | 엔드포인트 | 설명 | 인증 필수 |
|--------|-----------|------|----------|
| `POST` | `/register` | 회원가입 | ❌ |
| `POST` | `/login` | 로그인 (JWT 토큰 발급) | ❌ |
### 텍스트 분석 (Analysis)
| 메서드 | 엔드포인트 | 설명 | 인증 필수 |
|--------|-----------|------|----------|
| `POST` | `/analyze` | 텍스트 교정 분석 | ✅ |
| `POST` | `/save` | 교정 기록 저장 | ✅ |
### 기록 관리 (History)
| 메서드 | 엔드포인트 | 설명 | 인증 필수 |
|--------|-----------|------|----------|
| `GET` | `/history` | 전체 교정 기록 조회 | ✅ |
| `DELETE` | `/history?corr_idxs={id}` | 특정 기록 삭제 | ✅ |
| `DELETE` | `/history/all` | 전체 기록 삭제 | ✅ |
### 개인정보 관리 (User)
| 메서드 | 엔드포인트 | 설명 | 인증 필수 |
|--------|-----------|------|----------|
| `GET` | `/user` | 개인정보 조회 | ✅ |
| `PUT` | `/user` | 개인정보 수정 | ✅ |
| `DELETE` | `/user` | 회원 탈퇴 | ✅ |
### 유틸리티 (Utility)
| 메서드 | 엔드포인트 | 설명 | 인증 필수 |
|--------|-----------|------|----------|
| `GET` | `/` | 서버 상태 확인 | ❌ |
| `GET` | `/db-test` | DB 연결 확인 | ❌ |
| `GET` | `/check-email` | 이메일 중복 확인 | ❌ |

## 💾 데이터베이스 스키마
### users 테이블
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    pwd VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    dept VARCHAR(50),
    job VARCHAR(50),
    profile_img VARCHAR(255),
    joined_at TIMESTAMP DEFAULT NOW(),
    consent BOOLEAN DEFAULT TRUE
);
### corrections 테이블
```sql
CREATE TABLE corrections (
    corr_idx SERIAL PRIMARY KEY,
    id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    upload_text TEXT,
    upload_vector vector(768),
    corr_text TEXT,
    aggression_score INTEGER DEFAULT 0,
    emotion_score INTEGER DEFAULT 0,
    politeness_score INTEGER DEFAULT 0,
    tone_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
### embeddings 테이블
```sql
CREATE TABLE embeddings (
    ebd_idx SERIAL PRIMARY KEY,
    original_text TEXT NOT NULL,
    corrected_text vector(768) NOT NULL,
    corrected_text_raw TEXT NOT NULL,
    context_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```
---
## 🎯 주요 기능 상세
### 1. 실시간 텍스트 분석 (`/analyze`)
**요청 예시:**
```json
{  "text": "이거 좀 해줄 수 있어?"
}```
**응답 예시:**
```json
{  "original": "이거 좀 해줄 수 있어?",
  "context_type": "업무",
  "corrections": {
    "polite": "이 부분을 도와주실 수 있을까요?",
    "friendly": "이거 좀 해줄 수 있어?",
    "firm": "이 부분 처리해 주세요."
  }
}```
### 2. 교정 기록 저장 (`/save`)
**요청 예시:**
```json
{  "upload_text": "이거 좀 해줄 수 있어?",
  "corr_text": "이 부분을 도와주실 수 있을까요?",
  "tone_type": "정중하게"
}```
### 3. 맥락 학습 시스템
- **초기 분류**: 새로운 문장 → KoBERT + MLP로 5가지 맥락 중 하나 자동 분류
- **신뢰도 판정**: 
  - **60% 이상**: 해당 맥락으로 확정 + 해당 맥락의 유사 문장 검색
  - **60% 미만**: 맥락 불명확 판정 + 전체 데이터에서 검색
- **히스토리 반영**: 사용자의 이전 교정 3건을 LLM 프롬프트에 포함하여 개인 스타일 학습
## 🔐 보안
### 인증 & 암호화
- **JWT**: 로그인 후 토큰 발급 (24시간 유효)
- **비밀번호**: bcrypt로 암호화하여 저장
- **CORS**: 모든 오리진에서 접속 허용 (필요시 제한 가능)
### 자동 정리
- **scheduler.py**: 90일 이상 된 교정 기록 자동 삭제
- **회원 탈퇴**: 모든 개인 데이터 영구 삭제
## 🛠 개발 및 배포
### 로컬 테스트

# 백엔드 테스트
cd backend
python test.py
# API 문서 확인 (Swagger UI)
http://localhost:8000/docs

### 프로덕션 배포

# 백엔드 (Gunicorn + Uvicorn)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
# 프론트엔드 (Nginx 리버스 프록시)
# Nginx 설정: port 8888 → localhost:8888

## 📝 사용 예시
### 회원가입
```python
import requests
res = requests.post('http://localhost:8000/register', json={
    "email": "user@company.com",
    "password": "password123",
    "name": "홍길동",
    "dept": "영업팀",
    "job": "과장"
})
print(res.json())  # {"message": "회원가입 성공!", "user_id": 1}
### 로그인
```python
res = requests.post('http://localhost:8000/login', json={
    "email": "user@company.com",
    "password": "password123"
})
token = res.json()['access_token']
### 텍스트 교정
```python
headers = {"Authorization": f"Bearer {token}"}
res = requests.post('http://localhost:8000/analyze', 
    json={"text": "이거 좀 해줄 수 있어?"},
    headers=headers
)print(res.json())
## 🎓 모델 재학습
### 새로운 학습 데이터 추가
```bash
cd backend
# 1. 데이터 준비 (merged_data_4class.xlsx)
# 컬럼: [original_text, corrected_text, context_type]
# 2. DB에 데이터 삽입
python insert_data.py
# 3. 분류기 재학습
python train.py
# ✅ context_classifier.pkl 자동 업데이트

## 🐛 문제 해결
### 포트 충돌

# 기존 프로세스 종료
taskkill /f /im python.exe
# 또는 포트 확인
netstat -ano | findstr :8000
### DB 연결 실패
```python
# backend/main.py에서 DB 주소 확인
DATABASE_URL = "postgresql://user:password@mp.smhrd.or.kr/dbname"
### Ollama 모델 로드 실패
# Ollama 서버 실행
ollama serve
# 모델 다운로드 확인
ollama list
## 👥 팀 정보
◆ 양정익 (팀장): 프로젝트 총괄 기획 및 일정 관리
◆ 이현도: 백엔드 설계 및 AI 데이터셋 구축
◆ 박은선: UI/UX 디자인 및 프론트엔드 보조
◆ 김민찬: 기술 문서 작성 및 시스템 통합 테스트
◆ 이유라: 프론트엔드 개발 및 데이터 정제
## 📄 라이선스
MIT License - 자유롭게 사용, 수정, 배포 가능
---
## 📞 지원 및 피드백
- **이슈 리포트**: GitHub Issues
- **기능 제안**: GitHub Discussions
- **문의사항**: TEAM1 리더에게 연락
---
## 🔄 버전 관리
| 버전 | 날짜 | 주요 변경사항 |
|------|------|------------|
| v1.0 | 2025.04 | 초기 배포 (API, 웹 UI, 스캐너 앱) |
---
**Last Updated**: 2026.04.24
**Repository**: 
[2025-SMHRD-KDT-LangIntelligence-9/TEAM1](https://github.com/2025-SMHRD-KDT-LangIntelligence-9/TEAM1)
**주요 언어 구성**: 
- Python 51.2%
- HTML 43.1%
- Jupyter Notebook 5.7%

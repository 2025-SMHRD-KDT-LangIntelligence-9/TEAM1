# ToneGuard Backend
직장 내 메신저 전송 전 실시간 말투 교정 AI 서비스

---

## 프로젝트 구조
```
backend/
├── main.py          # FastAPI 서버 (API 엔드포인트)
├── database.py      # DB 연결 설정
├── models.py        # DB 테이블 정의
├── schemas.py       # API 데이터 형식 정의
├── embedding.py     # KoBERT 벡터화 + 맥락 예측 + 유사 검색
├── LLM.py           # Ollama 교정 문장 생성
├── scheduler.py     # 교정 기록 자동 삭제 스케줄러
├── train.py         # KoBERT + MLP 맥락 분류기 학습
├── insert_data.py   # 학습 데이터 DB 삽입
├── merge_data.py    # 데이터 합치기 유틸리티
├── kobert.py        # KoBERT 감정 분석 (참고용)
└── data/
    └── merged_data_4class.xlsx  # 학습 데이터 (5개 맥락)
```

---

## 기술 스택
| 항목 | 기술 |
|------|------|
| 백엔드 프레임워크 | FastAPI |
| DB | PostgreSQL + pgvector |
| AI 모델 | KoBERT + MLP (맥락 분류) |
| LLM | Ollama exaone3.5:7.8b |
| 인증 | JWT (python-jose) |
| ORM | SQLAlchemy |

---

## 설치 방법

### 1. 패키지 설치
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pgvector
pip install kobert-transformers transformers torch
pip install python-jose passlib python-dotenv
pip install pandas openpyxl tqdm scikit-learn
pip install ollama apscheduler
```

### 2. Ollama 모델 설치
```bash
ollama pull exaone3.5:7.8b
```

### 3. 서버 실행
```bash
# 로컬 실행
python -m uvicorn main:app --reload
# 외부 접속 허용
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## API 엔드포인트
| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| GET | / | 서버 상태 확인 | X |
| GET | /db-test | DB 연결 확인 | X |
| POST | /register | 회원가입 | X |
| POST | /login | 로그인 (JWT 토큰 발급) | X |
| POST | /analyze | 텍스트 교정 분석 | O |
| POST | /save | 교정 기록 저장 | O |
| GET | /history | 교정 기록 조회 | O |
| DELETE | /history/{corr_idx} | 특정 교정 기록 삭제 | O |
| DELETE | /history | 전체 교정 기록 삭제 | O |
| GET | /user | 개인정보 조회 | O |
| PUT | /user | 개인정보 수정 | O |
| DELETE | /user | 회원 탈퇴 | O |

---

## 주요 기능 흐름
```
사용자 텍스트 입력
        ↓
KoBERT → 텍스트 벡터화 (768차원)
        ↓
MLP → 맥락 예측 (업무/사과/피드백/의견충돌/일상)
        ↓
pgvector → 맥락 필터링 + 유사 텍스트 검색
        ↓
corrections → 사용자 히스토리 검색
        ↓
Ollama exaone3.5:7.8b → 3가지 톤으로 교정 문장 생성
        ↓
결과 반환 (정중하게/친근하게/단호하게)
```

---

## 맥락 분류 모델
- 모델: KoBERT + MLP
- 학습 데이터: 5,344개 (5개 맥락)
- 정확도: **83%**

| 맥락 | f1-score |
|------|---------|
| 사과 | 0.88 |
| 업무 | 0.81 |
| 피드백 | 0.85 |
| 의견충돌 | 0.81 |
| 일상 | 0.82 |

---

## DB 테이블 구조

### users
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | integer | 고유 번호 |
| email | varchar | 이메일 |
| pwd | varchar | 비밀번호 |
| name | varchar | 이름 |
| dept | varchar | 부서 |
| job | varchar | 직책 |
| joined_at | timestamp | 가입일 |

### corrections
| 컬럼 | 타입 | 설명 |
|------|------|------|
| corr_idx | integer | 고유 번호 |
| id | integer | 사용자 ID |
| upload_text | text | 원본 텍스트 |
| upload_vector | vector(768) | 원본 텍스트 벡터 |
| corr_text | text | 교정 텍스트 |
| tone_type | varchar | 맥락 |
| created_at | timestamp | 생성일 |

### embeddings
| 컬럼 | 타입 | 설명 |
|------|------|------|
| ebd_idx | integer | 고유 번호 |
| original_text | text | 원본 텍스트 |
| corrected_text | vector(768) | 벡터 (검색용) |
| corrected_text_raw | text | 교정 텍스트 |
| context_type | varchar | 맥락 |

---

## 팀 정보
- 팀명: ToneUp
- 서비스명: ToneGuard
- DB 서버: mp.smhrd.or.kr

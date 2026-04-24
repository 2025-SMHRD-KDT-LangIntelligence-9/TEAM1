# 🧠텍스트 교정 및 분석 프로젝트 (Text Correction and Analysis Project)

이 프로젝트는 고도화된 자연어 처리(NLP) 기술을 활용하여 텍스트를 분석하고 교정하는 종합 애플리케이션입니다. 
KoBERT모델과 대규모 언어 모델(LLM)을 결합하여 정확도 높은 분석과 교정 기능을 제공합니다. 
마이크로서비스 아키텍처를 기반으로 설계되었으며, 분석·교정·데이터베이스 관리 컴포넌트가 독립적으로 구성되어 효율적인 성능을 발휘합니다.

## 🚀주요 기능
* 텍스트 분석: KoBERT 모델을 활용한 정밀한 감정 탐지 및 감성 분석
* 텍스트 교정: LLM을 사용하여 상황에 맞는 다양한 말투(문체)별 교정 제안
* 데이터 관리: 사용자 데이터, 교정 이력 및 텍스트 임베딩 저장을 위한 효율적인 DB 관리
* 보안 및 인증: OAuth2와 JWT를 활용한 안전한 사용자 인증 및 권한 부여
* API 엔드포인트: 분석, 교정 및 DB 상호작용을 위한 RESTful API 제공
* 자동 관리 스케줄러: 만료된 교정 기록을 자동으로 삭제하는 클린업 기능

## 🛠️기술 스택
* Frontend : FastAPI, Jinja2, customtkinter, pyautogui, pyperclip
* Backend : FastAPI, SQLAlchemy, Passlib, Jose, KoBERT, transformers, APScheduler
* Database : PostgreSQL
* AI/ML : KoBERT, LLM, ollama
* Build Tools : pip, poetry

## 📦설치 방법
프로젝트를 로컬 환경에 설치하려면 다음 단계를 따르세요.

1. git clone을 통해 저장소를 복제합니다.
2. pip install -r requirements.txt 명령어로 필요한 의존성 패키지를 설치합니다.
3. PostgreSQL 데이터베이스를 생성한 뒤, database.py 파일에서 접속 정보를 수정합니다.
4. uvicorn main:app --host 0.0.0.0 --port 8000 명령어를 입력해 애플리케이션을 실행합니다.

## 💻사용 방법
1. 웹 브라우저를 열고 'http://localhost:8000'으로 접속합니다.
2. 기존 계정으로 로그인하거나 새 계정을 등록합니다.
3. 분석 및 교정이 필요한 텍스트 파일을 업로드하거나 직접 입력합니다.
4. 원하는 교정 말투(정중함, 친근함, 단호함 등)를 선택합니다.
5. 분석 결과와 교정된 내용을 확인합니다.

## 📂프로젝트 구조
```markdown
.
├── front           # 프론트엔드 관련 소스 (FastAPI, 템플릿 등)
│   ├── main.py
│   ├── scan_corr.py
│   ├── static
│   └── templates
├── backend         # 백엔드 핵심 로직 및 API
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   ├── models.py
│   ├── embedding.py
│   ├── scheduler.py
│   ├── kobert.py
│   └── LLM.py
├── requirements.txt
└── README.md
```

## 📸스크린샷
<img width="813" height="624" alt="image" src="https://github.com/user-attachments/assets/8a7fa487-4869-4aec-86a5-7dabf272e93c" />

<img width="400" height="400" alt="image" src="https://github.com/user-attachments/assets/c60142c2-a12b-4ac1-a8b1-8b6f4410ad58" />

<img width="400" height="400" alt="image" src="https://github.com/user-attachments/assets/74595945-4c84-4c24-aed4-954b4b8ddde5" />

## 🤝기여 방법
이 프로젝트에 기여하고 싶으시다면 다음 절차를 따라주세요.

1. 저장소를 Fork 합니다.
2. 새로운 기능을 위한 Branch를 생성합니다.
3. 변경 사항을 적용하고 Commit 합니다.
4. 브랜치에 Push 합니다.
5. Pull Request를 생성하여 검토를 요청합니다.

## 📝라이선스
이 프로젝트는 MIT 라이선스에 따라 배포됩니다.

## 📬문의처
질문이나 건의 사항이 있으시면 [support@example.com](mailto:support@example.com)으로 연락 부탁드립니다.

## 💖감사의 인사
이 프로젝트는 많은 분들의 소중한 기여로 만들어졌습니다. 감사합니다!

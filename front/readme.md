ToneGuard 프로젝트 실행 가이드
본 프로젝트는 AI를 활용한 실시간 말투 교정 및 소통 보조 도구인 **'ToneGuard'**의 웹-데스크톱 통합 프로토타입입니다. 팀원 여러분은 아래 절차에 따라 환경을 설정해 주세요.

📋 1. 환경 요구사항 (Environment)
언어: Python 3.13 이상

운영체제: Windows 10/11 권장 (데스크톱 GUI 제어용)

주요 라이브러리: FastAPI, CustomTkinter, PyGetWindow

📂 2. 프로젝트 구조 (Project Structure)
Plaintext
project1/
├── main_web.py           # 웹 서버 (FastAPI 관제탑)
├── scanner_window.py     # 데스크톱 스캐너 앱 (GUI)
├── requirements.txt      # 필수 라이브러리 목록
├── templates/            # HTML 파일 모음 (index, login, mypage)
└── static/               # 이미지 및 로고 (logo.png 등)
🛠️ 3. 초기 설정 (Setup)
VS Code 터미널에서 아래 명령어를 순서대로 입력하여 필요한 도구들을 설치합니다.

1) 필수 패키지 설치

Bash
pip install fastapi uvicorn jinja2 customtkinter pygetwindow pyautogui pyperclip requests
(선택사항) 만약 requirements.txt 파일이 있다면 아래 명령어로 한 번에 설치 가능합니다:

Bash
pip install -r requirements.txt
🚀 4. 실행 방법 (How to Run)
1) 서버 가동
터미널에서 웹 서버를 실행합니다.

Bash
python main_web.py
2) 접속
브라우저를 열고 아래 주소로 접속합니다.

URL: http://127.0.0.1:8888

3) 테스트 시나리오

로그인: user@email.com / 1234 입력

스캔 시작: 메인 화면의 [Scan] 버튼 클릭

웹 브라우저가 자동으로 최소화되고, 모니터 우측 상단에 데스크톱 스캐너가 실행되는지 확인합니다.

메인 복귀: 스캐너 창의 [메인] 버튼 클릭

스캐너가 종료되고 숨겨져 있던 웹 브라우저가 다시 나타나는지 확인합니다.

✨ 5. 주요 기능 안내
Hybrid Workflow: 웹 서버가 시스템 프로세스를 제어하여 데스크톱 창을 띄우는 하이브리드 방식 구현.

Seamless UI: 브라우저 최소화/복구 기능을 통한 매끄러운 사용자 경험 제공.

DPI Awareness: 고해상도 모니터에서도 UI 배율이 깨지지 않도록 시스템 패치 적용.

⚠️ 주의사항
포트 충돌: 서버 실행 시 [Errno 10048] 에러가 발생하면, 터미널에 taskkill /f /im python.exe를 입력하여 기존 프로세스를 완전히 종료한 뒤 다시 실행해 주세요.

창 위치: 스캐너 창은 실행 후 약 0.2초 뒤에 우측 상단으로 이동하도록 설계되어 있습니다.

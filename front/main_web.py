import os
import sys
import subprocess  # 외부 실행 파일(.py 등)을 별도 프로세스로 실행하기 위한 라이브러리
import pygetwindow as gw  # 현재 떠 있는 윈도우 창을 찾고 제어(최소화 등)하기 위한 라이브러리
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# [1] FastAPI 앱 객체 생성
app = FastAPI()

# --- [2] 경로 및 환경 설정 ---
# 현재 파일이 위치한 폴더의 절대 경로를 가져옵니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 정적 파일(이미지, CSS)과 템플릿(HTML) 폴더 경로 설정
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# 해당 폴더들이 없으면 자동으로 생성해 에러를 방지합니다.
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# /static 주소로 들어오는 요청을 static 폴더 안의 파일들과 연결합니다. (로고 이미지 등)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# HTML 파일을 렌더링하기 위한 Jinja2 템플릿 엔진 설정
templates = Jinja2Templates(directory=templates_dir)


# --- [3] 라우팅: 메인 페이지 ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 브라우저 쿠키에 'user_session'이 있는지 확인하여 실제 로그인 여부를 판단합니다.
    is_logged_in = request.cookies.get("user_session") is not None
    
    # index.html을 띄우며 'is_logged_in' 변수를 넘겨주어 상단 메뉴와 버튼 기능을 결정합니다.
    return templates.TemplateResponse(
        request=request, name="index.html", context={"is_logged_in": is_logged_in}
    )


# --- [4] 라우팅: 로그인 페이지 화면 출력 ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # 로그인과 회원가입 폼이 있는 login.html 화면을 반환합니다.
    return templates.TemplateResponse(request=request, name="login.html")


# --- [5] 라우팅: 로그인 데이터 처리 (보안 적용) ---
@app.post("/login_process")
async def process_login(response: Response, email: str = Form(...), password: str = Form(...)):
    # 폼에서 입력받은 아이디와 비밀번호가 맞는지 검증합니다.
    if email == "user@email.com" and password == "1234":
        # 로그인 성공 시 메인 화면("/")으로 리다이렉트(이동) 준비를 합니다.
        redirect = RedirectResponse(url="/", status_code=303)
        # 브라우저에 'user_session'이라는 이름의 쿠키(방문증)를 구워 로그인 상태를 유지시킵니다.
        redirect.set_cookie(key="user_session", value="yura") 
        return redirect
    else:
        # 로그인 실패 시 자바스크립트 알림창을 띄우고 이전 페이지로 돌려보냅니다.
        return HTMLResponse("<script>alert('로그인 실패! 아이디와 비번을 확인하세요.'); history.back();</script>")


# --- [6] 라우팅: 로그아웃 처리 ---
@app.get("/logout")
async def logout():
    # 로그아웃 시 메인 화면으로 이동하도록 설정합니다.
    redirect = RedirectResponse(url="/", status_code=303)
    # 브라우저에 저장된 'user_session' 쿠키를 완전히 삭제하여 권한을 회수합니다.
    redirect.delete_cookie("user_session")
    return redirect


# --- [7] 라우팅: 마이페이지 출력 (보안 적용) ---
@app.get("/mypage", response_class=HTMLResponse)
async def mypage(request: Request):
    # 보안 로직: 쿠키가 없는(로그인하지 않은) 사용자가 직접 주소를 치고 들어오면 로그인 창으로 쫓아냅니다.
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/login", status_code=303)
    
    # 정상 로그인된 사용자에게만 마이페이지를 보여줍니다.
    return templates.TemplateResponse(
        request=request, name="mypage.html", context={"user_name": "유라"}
    )


# --- [8] 라우팅: 실시간 스캐너 실행 명령 (하이브리드 기능) ---
@app.post("/start-scanner")
async def start_scanner():
    try:
        # 1. 브라우저 창 자동 최소화: 현재 활성화된 브라우저 창을 찾아 작업 표시줄로 내립니다.
        active_window = gw.getActiveWindow()
        if active_window:
            active_window.minimize() 

        # 2. 데스크톱 앱 실행: 현재 파이썬 환경을 이용해 scanner_window.py를 별도의 창으로 띄웁니다.
        subprocess.Popen([sys.executable, "scanner_window.py"])
        
        return {"status": "success"}
    except Exception as e:
        # 실행 중 에러가 발생하면 프론트엔드로 에러 메시지를 전달합니다.
        return {"status": "error", "message": str(e)}


# --- [9] API: 마이페이지용 교정 기록 데이터 전달 ---
@app.get("/api/history")
async def get_history(request: Request):
    # [데이터베이스 연동 전 임시 데이터] 화면에 보여줄 샘플 데이터를 리스트로 작성합니다.
    mock_data = [
        {"tone": "비즈니스(공손)", "original": "이거 언제 끝나요?", "corrected": "해당 업무의 예상 완료 일정을 알 수 있을까요?"},
        {"tone": "친근하게", "original": "밥 먹었냐?", "corrected": "식사는 맛있게 하셨어요?"},
        {"tone": "단호하게", "original": "그건 안 돼요.", "corrected": "해당 요청은 현재 정책상 수용이 어렵습니다."}
    ]
    # 프론트엔드(JavaScript의 fetch)에서 사용하기 좋게 JSON 형태로 변환하여 반환합니다.
    return {"history": mock_data}


# --- [10] 서버 가동 ---
if __name__ == "__main__":
    # 포트 8888번을 사용하여 로컬 환경에서 서버를 실행합니다.
    uvicorn.run(app, host="127.0.0.1", port=8888)
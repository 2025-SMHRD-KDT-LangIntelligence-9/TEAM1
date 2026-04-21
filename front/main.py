import os
import sys
# 콘솔창(터미널)에 한글을 출력할 때 글자가 깨지지 않도록 기본 인코딩을 UTF-8로 강제 설정합니다.
sys.stdout.reconfigure(encoding='utf-8')
import subprocess # 외부 프로그램(예: scan_corr.exe)을 실행하기 위해 사용하는 파이썬 기본 도구입니다.
import pygetwindow as gw # 현재 윈도우에 띄워진 창들을 제어(예: 창 최소화)하기 위한 라이브러리입니다.
import requests # 다른 서버(백엔드 서버)로 인터넷 요청을 보내고 데이터를 받아오기 위한 통신 라이브러리입니다.
from fastapi import FastAPI, Request, Form, Response # 파이썬으로 빠르고 쉽게 웹 서버를 만들 수 있게 해주는 FastAPI 핵심 도구들입니다.
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse # 서버가 클라이언트(브라우저)에게 어떤 형태(HTML, 화면이동, JSON 데이터)로 대답할지 결정하는 도구들입니다.
from fastapi.staticfiles import StaticFiles # 이미지나 CSS, 동영상 같은 정적 파일들을 서비스하기 위한 도구입니다.
from fastapi.templating import Jinja2Templates # HTML 파일 안에 파이썬 변수(예: {{ user_name }})를 집어넣어 화면을 그려주는 템플릿 엔진입니다.
import uvicorn # FastAPI로 만든 웹 서버를 실제로 구동시켜주는 엔진(서버 프로그램)입니다.

# =========================================================
# [1] FastAPI 초기화 및 기본 환경 설정
# =========================================================
app = FastAPI() # 웹 서버 애플리케이션 객체를 생성합니다. (모든 설정의 중심)

# 현재 프로그램이 어디서 실행되고 있는지 기준 폴더(BASE_DIR)를 찾습니다.
if getattr(sys, 'frozen', False):
    # 만약 PyInstaller로 구워진 exe 파일로 실행 중이라면, 그 exe 파일이 있는 폴더를 기준으로 잡습니다.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # VScode 등에서 그냥 파이썬 스크립트(.py)로 실행 중이라면, 현재 스크립트 파일이 있는 폴더를 기준으로 잡습니다.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 기준 폴더 안에 있는 'static'(이미지 등) 폴더와 'templates'(HTML 파일들) 폴더의 정확한 경로를 지정합니다.
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# 혹시라도 해당 폴더들이 없으면 에러가 나지 않도록 자동으로 빈 폴더를 만들어줍니다.
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# 인터넷 주소창에 /static/... 이라고 입력하면 컴퓨터의 static 폴더 안의 파일을 보여주도록 연결합니다.
app.mount("/static", StaticFiles(directory=static_dir), name="static")
# HTML 화면을 그릴 때 앞서 지정한 templates 폴더를 사용하도록 설정합니다.
templates = Jinja2Templates(directory=templates_dir)

# 진짜 데이터 처리를 담당하는 핵심 백엔드 서버의 주소입니다. (이 서버가 데이터를 중계해 줄 목적지)
BACKEND_URL = "http://192.168.0.77:8000"


# =========================================================
# [2] 화면 라우팅 (사용자가 웹 주소를 쳤을 때 어떤 HTML을 보여줄지 결정)
# =========================================================

# 메인 홈페이지 (예: localhost:8888/) 접속 시
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 브라우저에 저장된 'user_session' 쿠키(로그인 입장권)가 있는지 확인합니다.
    token = request.cookies.get("user_session")
    # 토큰이 있으면 로그인 상태(True), 없으면 비로그인 상태(False)로 판단합니다.
    is_logged_in = token is not None
    
    # index.html 화면을 그려서 브라우저에 보내주되, 로그인 여부와 토큰 값을 화면에 전달해줍니다.
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "is_logged_in": is_logged_in,
            "access_token": token if token else ""
        }
    )

# 로그인/회원가입 페이지 (예: localhost:8888/login) 접속 시
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # 별다른 데이터 없이 login.html 화면만 그려서 보여줍니다.
    return templates.TemplateResponse(request=request, name="login.html")


# =========================================================
# [3] 백엔드 통신 및 인증 처리 (사용자의 폼 입력을 받아 백엔드로 전달)
# =========================================================

# 로그인 폼에서 '로그인' 버튼을 눌러 데이터를 보냈을 때 (POST 방식)
@app.post("/login_process")
async def process_login(response: Response, email: str = Form(...), password: str = Form(...)):
    try:
        # 사용자가 입력한 이메일/비번을 진짜 백엔드 서버의 /login 주소로 대신 물어봅니다. (중계)
        res = requests.post(f"{BACKEND_URL}/login", json={"email": email, "password": password})
        
        if res.status_code == 200: # 백엔드에서 로그인이 성공했다고(200 OK) 답변이 오면
            # 백엔드가 발급해준 입장권(access_token)을 챙깁니다.
            token = res.json().get("access_token", "")
            # 로그인 성공 시 메인 화면("/")으로 강제 이동(Redirect) 시킵니다.
            redirect = RedirectResponse(url="/", status_code=303)
            # 브라우저에 'user_session'이라는 이름으로 입장권(쿠키)을 저장해줍니다.
            redirect.set_cookie(key="user_session", value=token) 
            return redirect
        else:
            # 로그인이 실패했다면, 간단한 자바스크립트 알림창을 띄우고 뒤로가기를 시킵니다.
            return HTMLResponse("""
                <meta charset='utf-8'>
                <script>
                    alert('로그인 실패! 이메일과 비번을 확인하세요.');
                    history.back();
                </script>
            """)
    except Exception as e:
        # 아예 백엔드 서버가 죽어있거나 통신 에러가 났을 때의 비상 처리입니다.
        safe_msg = str(e).replace("'", "").replace('"', "")
        return HTMLResponse(f"""
            <meta charset='utf-8'>
            <script>
                alert('서버 연결 오류! 서버가 켜져 있는지 확인하세요.\\n내용: {safe_msg}');
                history.back();
            </script>
        """)

# 회원가입 폼에서 '가입 완료' 버튼을 눌렀을 때 (POST 방식)
@app.post("/register_process")
async def process_register(
    email: str = Form(...), password: str = Form(...), name: str = Form(...), 
    dept: str = Form(""), job: str = Form("")
):
    try:
        # 입력받은 정보들을 예쁘게 포장해서 백엔드 서버의 /register 주소로 가입 요청을 보냅니다.
        user_data = {"email": email, "password": password, "name": name, "dept": dept, "job": job}
        res = requests.post(f"{BACKEND_URL}/register", json=user_data)
        
        if res.status_code == 200: # 백엔드에서 가입이 성공했다고 답변이 오면
            # 축하 알림을 띄우고 다시 로그인 페이지로 이동시킵니다. (이메일 칸을 채워주기 위해 주소에 ?email= 추가)
            return HTMLResponse(f"""
                <meta charset='utf-8'>
                <script>
                    alert('가입 완료! 로그인해주세요.');
                    window.location.href='/login?email={email}';
                </script>
            """)
        else: # 가입 실패 시 (보통 이메일 중복)
            return HTMLResponse("""
                <meta charset='utf-8'>
                <script>
                    alert('회원가입 실패! 이미 있는 이메일인지 확인하세요.');
                    history.back();
                </script>
            """)
    except Exception as e:
        safe_msg = str(e).replace("'", "").replace('"', "")
        return HTMLResponse(f"""
            <meta charset='utf-8'>
            <script>
                alert('백엔드 서버 연결 오류!\\n내용: {safe_msg}');
                history.back();
            </script>
        """)

# 로그아웃 버튼을 눌렀을 때
@app.get("/logout")
async def logout():
    # 메인 홈페이지로 튕겨내면서
    redirect = RedirectResponse(url="/", status_code=303)
    # 브라우저에 저장되어 있던 입장권(user_session 쿠키)을 삭제해버립니다.
    redirect.delete_cookie("user_session")
    return redirect


# =========================================================
# [4] 마이페이지 및 설정 API (내 정보 보기, 기록 보기 등)
# =========================================================

# 마이페이지 (예: localhost:8888/mypage) 접속 시
@app.get("/mypage", response_class=HTMLResponse)
async def mypage(request: Request):
    # 쿠키에서 입장권을 확인하고, 없으면 로그인 페이지로 쫓아냅니다.
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    # 브라우저에 저장된 대화기록 동의 여부(user_consent) 쿠키를 확인합니다. (없으면 기본값 true)
    consent_cookie = request.cookies.get("user_consent", "true")
    is_consented = (consent_cookie.lower() == "true")
    
    real_name = "고객"
    try:
        # 내 입장권(토큰)을 보여주면서 백엔드 서버에 "내 이름이 뭐지?" 하고 물어봅니다.
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BACKEND_URL}/user", headers=headers, timeout=5)
        
        if res.status_code == 200:
            real_name = res.json().get("name", "고객") # 성공하면 진짜 이름을 가져옵니다.
    except Exception as e:
        print(f"[에러] 이름 가져오기 실패: {e}")

    # mypage.html 화면을 그리면서, 내 이름과 동의 여부 값을 화면에 전달해줍니다.
    return templates.TemplateResponse(
        request=request, 
        name="mypage.html", 
        context={
            "user_name": real_name,
            "is_consented": is_consented
        }
    )

# 마이페이지에서 나의 교정 기록을 요청할 때 (프론트엔드 JS가 몰래 호출함)
@app.get("/api/history")
async def get_history(request: Request):
    token = request.cookies.get("user_session")
    if not token: return JSONResponse(status_code=401, content={"message": "Unauthorized"})

    # 백엔드 서버에 내 토큰을 주고 나의 전체 기록을 달라고 요청합니다.
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{BACKEND_URL}/history", headers=headers)
        if res.status_code == 200: return res.json() # 성공하면 기록 데이터를 그대로 화면 쪽에 돌려줌
        return {"history": []}
    except:
        return {"history": []}

# 마이페이지에서 비밀번호 변경을 요청할 때
@app.put("/api/update-password")
async def update_password(request: Request):
    token = request.cookies.get("user_session")
    if not token: return JSONResponse(status_code=401, content={"message": "로그인이 필요합니다."})
    
    # 화면(JS)에서 보내준 기존 비밀번호와 새 비밀번호를 꺼냅니다.
    data = await request.json()
    payload = {
        "current_password": data.get("current_password"),
        "new_password": data.get("new_password")
    }

    try:
        # 백엔드에 내 토큰과 변경할 비밀번호 정보를 주며 수정을 지시합니다.
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.put(f"{BACKEND_URL}/user", headers=headers, json=payload)
        
        if res.status_code == 200: return {"status": "success", "message": "비밀번호가 변경되었습니다."}
        else:
            # 실패 시 백엔드가 알려준 이유(기존 비번 틀림 등)를 그대로 화면에 전달합니다.
            error_msg = res.json().get("detail", "비밀번호 변경에 실패했습니다.")
            return JSONResponse(status_code=res.status_code, content={"message": error_msg})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# 마이페이지에서 회원 탈퇴를 요청할 때
@app.delete("/api/delete-account")
async def delete_account(request: Request):
    token = request.cookies.get("user_session")
    if not token: return JSONResponse(status_code=401, content={"message": "로그인이 필요합니다."})
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 1. 먼저 내 모든 대화 기록을 백엔드에 지워달라고 요청합니다.
        requests.delete(f"{BACKEND_URL}/history/all", headers=headers)
        # 2. 그 다음 내 회원 정보 자체를 지워달라고 백엔드에 요청합니다.
        res = requests.delete(f"{BACKEND_URL}/user", headers=headers)
        
        if res.status_code == 200:
            # 성공하면 결과 메시지를 만들고, 내 브라우저의 로그인 쿠키도 삭제합니다.
            response = JSONResponse(content={"status": "success", "message": "회원 탈퇴 완료"})
            response.delete_cookie("user_session")
            return response
        return JSONResponse(status_code=res.status_code, content={"message": "탈퇴 처리에 실패했습니다."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# 마이페이지에서 교정 기록 한 개(X 버튼)를 삭제할 때
@app.delete("/api/history/{item_id}")
async def delete_single_history(item_id: int, request: Request):
    token = request.cookies.get("user_session")
    if not token: return JSONResponse(status_code=401, content={"status": "error", "message": "로그인이 필요합니다."})
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 선택한 번호(item_id)의 기록을 지워달라고 백엔드에 요청합니다.
        res = requests.delete(f"{BACKEND_URL}/history?corr_idxs={item_id}", headers=headers)
        
        if res.status_code == 200: return {"status": "success"}
        return JSONResponse(status_code=res.status_code, content={"status": "error", "message": "기록 삭제 실패"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# 마이페이지에서 '데이터 수집 동의' 스위치를 껐다 켰을 때
@app.post("/api/update-consent")
async def update_consent(request: Request):
    data = await request.json()
    response = JSONResponse(content={"status": "success"})
    # 화면에서 보내준 동의 상태를 브라우저 쿠키(user_consent)에 덮어써서 기억해둡니다.
    response.set_cookie(key="user_consent", value=str(data.get("consent")).lower())
    return response


# =========================================================
# [5] 스캐너 앱 연동 및 프록시(중계) 서버 API
# =========================================================

# (이 방식은 현재 index.html의 toneguard:// 방식에 의해 안 쓰일 수도 있지만, 레거시 호환용으로 둡니다)
@app.post("/start-scanner")
async def start_scanner(request: Request):
    try:
        token = request.cookies.get("user_session")
        if not token: return {"status": "error", "message": "로그인이 필요합니다."}

        consent_status = request.cookies.get("user_consent", "true")

        # 현재 실행중인 웹 브라우저 창을 찾아서 아래로 내려버립니다(최소화).
        active_window = gw.getActiveWindow()
        if active_window:
            active_window.minimize() 

        # 🌟 내 컴퓨터에 설치된 백그라운드 프로그램(scan_corr.exe)을 강제로 실행시키며 내 토큰을 전달합니다.
        subprocess.Popen(["scan_corr.exe", token, consent_status])
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 스캐너 프로그램(exe)이 톤 교정 요청을 보낼 때 중간에서 가로채서 백엔드로 넘겨주는 역할
@app.post("/analyze")
async def proxy_analyze(request: Request):
    try:
        data = await request.json()
        token = request.headers.get("Authorization")
        headers = {"Authorization": token} if token and token != "None" else {}

        # 스캐너의 질문을 진짜 딥러닝 백엔드 서버(/analyze)에 대신 물어보고 대답을 기다립니다. (타임아웃 15초)
        res = requests.post(f"{BACKEND_URL}/analyze", json=data, headers=headers, timeout=15)
        # 백엔드의 분석 결과를 스캐너에게 그대로 반환합니다.
        return JSONResponse(status_code=res.status_code, content=res.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "중계 서버 오류"})

# 스캐너 프로그램(exe)이 교정 기록을 저장하려 할 때 중간에서 가로채서 백엔드로 넘겨주는 역할
@app.post("/save")
async def proxy_save(request: Request):
    try:
        token = request.headers.get("Authorization")
        data = await request.json()
        
        # 백엔드 서버(/save)에 기록 저장 지시를 대신 내립니다.
        res = requests.post(f"{BACKEND_URL}/save", json=data, headers={"Authorization": token}, timeout=5)
        return JSONResponse(status_code=res.status_code, content=res.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# 회원가입 시 이메일 칸에서 마우스가 벗어날 때 실시간 중복 체크를 중계해주는 역할
@app.get("/api/check-email")
async def check_email(email: str):
    try:
        # 백엔드에 이메일이 이미 있는지 대신 물어봅니다.
        res = requests.get(f"{BACKEND_URL}/check-email?email={email}", timeout=3)
        if res.status_code == 200:
            return JSONResponse(content={"available": res.json().get("available")})
        return JSONResponse(content={"available": False})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


# =========================================================
# [6] 서버 실행부
# =========================================================
# 이 스크립트가 직접 실행될 때 (import 된게 아닐 때) uvicorn 엔진을 이용해 웹 서버를 구동합니다.
# 0.0.0.0은 외부 컴퓨터에서도 접속 가능하게 열어두는 것이며, 포트는 8888을 사용합니다.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)

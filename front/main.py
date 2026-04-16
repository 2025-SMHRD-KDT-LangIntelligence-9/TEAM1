import os
import sys
import subprocess  # 외부 프로그램(스캐너 앱)을 실행하기 위한 라이브러리
import pygetwindow as gw  # 현재 열려있는 브라우저 창을 제어(최소화)하기 위한 라이브러리
import requests  # 백엔드 서버(192.168.0.77)와 데이터를 주고받기 위한 통신 라이브러리
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# [1] FastAPI 애플리케이션 초기화 및 기본 설정
# FastAPI 앱 객체를 생성합니다.
app = FastAPI()

# 현재 main.py 파일이 위치한 폴더의 절대 경로를 가져옵니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 정적 파일(이미지, CSS 등)이 들어갈 static 폴더와 HTML 화면이 들어갈 templates 폴더 경로 설정
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# 혹시 폴더가 없다면 자동으로 생성하여 에러를 방지합니다.
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# 인터넷 주소창에 /static/... 으로 접속하면 static 폴더 안의 파일을 보여주도록 연결합니다.
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 파이썬 데이터를 HTML 화면에 입혀서 보여주기 위해 Jinja2 템플릿 엔진을 설정합니다.
templates = Jinja2Templates(directory=templates_dir)

# 우리가 통신할 진짜 백엔드(DB 처리) 서버의 주소를 변수로 저장해 둡니다.
BACKEND_URL = "http://192.168.0.77:8000"

# [2] 화면 라우팅 (페이지 이동 처리)
# 메인 홈 화면 (http://127.0.0.1:8888/)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 접속한 브라우저의 쿠키에 'user_session'이라는 로그인 토큰이 있는지 확인합니다.
    is_logged_in = request.cookies.get("user_session") is not None
    
    # index.html을 화면에 띄우면서, 로그인 여부(is_logged_in)를 전달해 버튼 모양을 바꿉니다.
    return templates.TemplateResponse(
        request=request, name="index.html", context={"is_logged_in": is_logged_in}
    )

# 로그인/회원가입 화면 (http://127.0.0.1:8888/login)
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # login.html 화면을 그대로 사용자에게 보여줍니다.
    return templates.TemplateResponse(request=request, name="login.html")

# [3] 백엔드 통신 및 인증 로직 (안전한 버전)

@app.post("/login_process")
async def process_login(response: Response, email: str = Form(...), password: str = Form(...)):
    try:
        res = requests.post(f"{BACKEND_URL}/login", json={"email": email, "password": password})
        
        if res.status_code == 200:
            token = res.json().get("access_token", "")
            redirect = RedirectResponse(url="/", status_code=303)
            redirect.set_cookie(key="user_session", value=token) 
            return redirect
        else:
            # 실패 시 완벽한 HTML로 응답
            return HTMLResponse("""
                <meta charset='utf-8'>
                <script>
                    alert('로그인 실패! 이메일과 비번을 확인하세요.');
                    history.back();
                </script>
            """)
    except Exception as e:
        # [핵심] 에러 메시지 내의 따옴표를 제거하여 자바스크립트 문법 파괴 방지
        safe_msg = str(e).replace("'", "").replace('"', "")
        return HTMLResponse(f"""
            <meta charset='utf-8'>
            <script>
                alert('백엔드 서버 연결 오류! 서버가 켜져 있는지 확인하세요.\\n내용: {safe_msg}');
                history.back();
            </script>
        """)

# 회원가입 데이터 처리
@app.post("/register_process")
async def process_register(
    email: str = Form(...), password: str = Form(...), name: str = Form(...), 
    dept: str = Form(""), job: str = Form("")
):
    try:
        user_data = {"email": email, "password": password, "name": name, "dept": dept, "job": job}
        res = requests.post(f"{BACKEND_URL}/register", json=user_data)
        
        if res.status_code == 200:
            # ✅ 금고 저장 방식을 버리고, 100% 확실한 주소창 꼬리표 방식으로 되돌립니다.
            return HTMLResponse(f"""
                <meta charset='utf-8'>
                <script>
                    alert('가입 완료! 로그인해주세요.');
                    window.location.href='/login?email={email}';
                </script>
            """)
        else:
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

# 로그아웃 처리
@app.get("/logout")
async def logout():
    # 메인 홈으로 이동하도록 설정
    redirect = RedirectResponse(url="/", status_code=303)
    # 브라우저에 저장된 쿠키(토큰)를 삭제하여 권한을 없앰
    redirect.delete_cookie("user_session")
    return redirect

# [4] 마이페이지 및 스캐너 연동
# 마이페이지 화면 (http://127.0.0.1:8888/mypage)
@app.get("/mypage", response_class=HTMLResponse)
async def mypage(request: Request):
    # 1. 쿠키에서 로그인 토큰 꺼내기
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    # 🌟 [추가된 부분] 브라우저 쿠키에서 동의 상태를 읽어옵니다. (기본값은 "true")
    consent_cookie = request.cookies.get("user_consent", "true")
    is_consented = (consent_cookie.lower() == "true") # true면 True로, false면 False로 변환
    
    # 2. 기본 이름 설정
    real_name = "고객"

    # 3. 백엔드에서 진짜 이름 가져오기
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # [수정된 부분] 백엔드의 정확한 주소인 '/user' 로 요청을 보냅니다!
        api_url = f"{BACKEND_URL}/user" 
        res = requests.get(api_url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            user_data = res.json()
            # 백엔드가 준 데이터에서 'name'을 쏙 뽑아옵니다.
            real_name = user_data.get("name", "고객")
            
    except Exception as e:
        print(f"[에러] 이름 가져오기 실패: {e}")

    # 4. 화면 그리기
    return templates.TemplateResponse(
        request=request, 
        name="mypage.html", 
        # 🌟 [추가된 부분] 화면에 이름과 함께 '동의 여부(is_consented)'도 전달합니다!
        context={
            "user_name": real_name,
            "is_consented": is_consented
        }
    )

# 마이페이지 내 교정 기록 데이터 가져오기 (백엔드에서 조회 후 프론트로 전달)
@app.get("/api/history")
async def get_history(request: Request):
    # 브라우저 쿠키에서 로그인 토큰을 꺼냅니다.
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})

    # 백엔드 서버에 나임을 증명하기 위해 헤더에 토큰을 담습니다.
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 백엔드 서버의 /history 주소로 내 기록을 달라고 요청합니다.
        res = requests.get(f"{BACKEND_URL}/history", headers=headers)
        if res.status_code == 200:
            # 백엔드가 준 JSON 데이터를 그대로 프론트엔드로 전달합니다.
            return res.json()
        else:
            return {"history": []}
    except:
        return {"history": []}

# 마이페이지 - 설정 및 관리 (비밀번호 변경 & 회원 탈퇴)

@app.put("/api/update-password")
async def update_password(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"message": "로그인이 필요합니다."})
    
    # [핵심] 프론트에서 보낸 '기존 비밀번호'와 '새 비밀번호'를 모두 꺼냅니다.
    data = await request.json()
    current_pw = data.get("current_password")
    new_pw = data.get("new_password")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 백엔드 서버(192.168.0.77)가 원하는 규칙 그대로 2개를 세트로 묶어서 보냅니다.
        payload = {
            "current_password": current_pw,
            "new_password": new_pw
        }
        res = requests.put(f"{BACKEND_URL}/user", headers=headers, json=payload)
        
        if res.status_code == 200:
            return {"status": "success", "message": "비밀번호가 변경되었습니다."}
        else:
            # 백엔드가 거절했을 때(예: 기존 비밀번호 틀림), 백엔드가 보낸 이유를 화면에 전달합니다.
            error_msg = res.json().get("detail", "비밀번호 변경에 실패했습니다.")
            return JSONResponse(status_code=res.status_code, content={"message": error_msg})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.delete("/api/delete-account")
async def delete_account(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"message": "로그인이 필요합니다."})
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # [1단계 콤보] 자식 데이터(교정 기록)부터 싹 지우기!
        # 주의: 백엔드의 '전체 삭제' API 주소가 '/history/all' 이라고 가정했습니다.
        # (만약 백엔드 팀원분이 다른 주소로 만들었다면 이곳을 수정해 주세요!)
        requests.delete(f"{BACKEND_URL}/history/all", headers=headers)

        # [2단계 콤보] 방해물이 사라졌으니 진짜 유저 계정 지우기!
        res = requests.delete(f"{BACKEND_URL}/user", headers=headers)
        
        if res.status_code == 200:
            # 성공 시 로그인 쿠키 파괴 후 성공 메시지 전달
            response = JSONResponse(content={"status": "success", "message": "회원 탈퇴가 완료되었습니다."})
            response.delete_cookie("user_session")
            return response
        else:
            return JSONResponse(status_code=res.status_code, content={"message": "탈퇴 처리에 실패했습니다."})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# 👉 특정 교정 기록 1개 삭제하기 (mypage.html 에서 사용)
@app.delete("/api/history/{item_id}")
async def delete_single_history(item_id: int, request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"status": "error", "message": "로그인이 필요합니다."})
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 🌟 [여기 수정됨!] 백엔드가 요구하는 '?corr_idxs=숫자' 형태로 주소를 정확히 맞춰서 보냅니다!
        res = requests.delete(f"{BACKEND_URL}/history?corr_idxs={item_id}", headers=headers)
        
        if res.status_code == 200:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=res.status_code, content={"status": "error", "message": "기록 삭제에 실패했습니다."})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# 👉 3-5. 대화 기록 저장 동의 상태 업데이트 (백엔드 안 거치고 쿠키에 저장!)
@app.post("/api/update-consent")
async def update_consent(request: Request):
    data = await request.json()
    is_consent = data.get("consent") # 프론트에서 온 True 또는 False

    # 백엔드로 가지 않고, 곧바로 "성공" 응답을 만들면서 브라우저 쿠키에 상태를 구워버립니다.
    response = JSONResponse(content={"status": "success"})
    response.set_cookie(key="user_consent", value=str(is_consent).lower()) # "true" 또는 "false"로 저장
    return response

# 스캐너 데스크톱 앱(scan_corr.py) 실행
@app.post("/start-scanner")
async def start_scanner(request: Request):
    try:
        token = request.cookies.get("user_session")
        if not token:
            return {"status": "error", "message": "로그인이 필요합니다."}

        # 🌟 [핵심] 방금 저장해둔 브라우저 쿠키에서 동의 상태를 꺼냅니다. (기본값은 "true")
        consent_status = request.cookies.get("user_consent", "true")

        active_window = gw.getActiveWindow()
        if active_window:
            active_window.minimize() 

        # 🌟 [핵심] 파이썬 스캐너를 켤 때, 토큰(sys.argv[1])과 함께 동의상태(sys.argv[2])도 넘겨줍니다!
        subprocess.Popen([sys.executable, "scan_corr.py", token, consent_status])
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------------------------------------------------
# [추가됨] 실시간 이메일 중복 확인 (프론트와 백엔드 연결 다리)
# ---------------------------------------------------------
@app.get("/api/check-email")
async def check_email(email: str):
    try:
        # 백엔드 서버(192.168.0.77)의 /check-email 로 물어봅니다.
        res = requests.get(f"{BACKEND_URL}/check-email?email={email}", timeout=3)
        if res.status_code == 200:
            data = res.json()
            # 백엔드가 {"available": true/false} 로 대답해주므로 똑같이 전달합니다.
            return JSONResponse(content={"available": data.get("available")})
        else:
            return JSONResponse(content={"available": False})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
    
# [5] 서버 실행부

if __name__ == "__main__":
    # 로컬 컴퓨터(127.0.0.1)의 8888 포트에서 이 FastAPI 앱을 실행합니다.
    uvicorn.run(app, host="127.0.0.1", port=8888)

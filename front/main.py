import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import subprocess
import pygetwindow as gw
import requests
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# [1] FastAPI 초기화 및 설정
app = FastAPI()
if getattr(sys, 'frozen', False):
    # PyInstaller로 묶인 exe 상태일 때 (main.exe가 있는 진짜 폴더를 바라봄)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # VScode 등에서 그냥 파이썬 스크립트로 실행할 때
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

BACKEND_URL = "http://192.168.0.77:8000"

# [2] 화면 라우팅
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    token = request.cookies.get("user_session")
    is_logged_in = token is not None
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "is_logged_in": is_logged_in,
            "access_token": token if token else ""
        }
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

# [3] 백엔드 통신 및 인증
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
            return HTMLResponse("""
                <meta charset='utf-8'>
                <script>
                    alert('로그인 실패! 이메일과 비번을 확인하세요.');
                    history.back();
                </script>
            """)
    except Exception as e:
        safe_msg = str(e).replace("'", "").replace('"', "")
        return HTMLResponse(f"""
            <meta charset='utf-8'>
            <script>
                alert('서버 연결 오류! 서버가 켜져 있는지 확인하세요.\\n내용: {safe_msg}');
                history.back();
            </script>
        """)

@app.post("/register_process")
async def process_register(
    email: str = Form(...), password: str = Form(...), name: str = Form(...), 
    dept: str = Form(""), job: str = Form("")
):
    try:
        user_data = {"email": email, "password": password, "name": name, "dept": dept, "job": job}
        res = requests.post(f"{BACKEND_URL}/register", json=user_data)
        
        if res.status_code == 200:
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

@app.get("/logout")
async def logout():
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.delete_cookie("user_session")
    return redirect

# [4] 마이페이지 및 설정
@app.get("/mypage", response_class=HTMLResponse)
async def mypage(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    consent_cookie = request.cookies.get("user_consent", "true")
    is_consented = (consent_cookie.lower() == "true")
    
    real_name = "고객"
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BACKEND_URL}/user", headers=headers, timeout=5)
        
        if res.status_code == 200:
            real_name = res.json().get("name", "고객")
    except Exception as e:
        print(f"[에러] 이름 가져오기 실패: {e}")

    return templates.TemplateResponse(
        request=request, 
        name="mypage.html", 
        context={
            "user_name": real_name,
            "is_consented": is_consented
        }
    )

@app.get("/api/history")
async def get_history(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})

    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{BACKEND_URL}/history", headers=headers)
        if res.status_code == 200:
            return res.json()
        return {"history": []}
    except:
        return {"history": []}

@app.put("/api/update-password")
async def update_password(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"message": "로그인이 필요합니다."})
    
    data = await request.json()
    payload = {
        "current_password": data.get("current_password"),
        "new_password": data.get("new_password")
    }

    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.put(f"{BACKEND_URL}/user", headers=headers, json=payload)
        
        if res.status_code == 200:
            return {"status": "success", "message": "비밀번호가 변경되었습니다."}
        else:
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
        requests.delete(f"{BACKEND_URL}/history/all", headers=headers)
        res = requests.delete(f"{BACKEND_URL}/user", headers=headers)
        
        if res.status_code == 200:
            response = JSONResponse(content={"status": "success", "message": "회원 탈퇴 완료"})
            response.delete_cookie("user_session")
            return response
        return JSONResponse(status_code=res.status_code, content={"message": "탈퇴 처리에 실패했습니다."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.delete("/api/history/{item_id}")
async def delete_single_history(item_id: int, request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return JSONResponse(status_code=401, content={"status": "error", "message": "로그인이 필요합니다."})
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.delete(f"{BACKEND_URL}/history?corr_idxs={item_id}", headers=headers)
        
        if res.status_code == 200:
            return {"status": "success"}
        return JSONResponse(status_code=res.status_code, content={"status": "error", "message": "기록 삭제 실패"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/update-consent")
async def update_consent(request: Request):
    data = await request.json()
    response = JSONResponse(content={"status": "success"})
    response.set_cookie(key="user_consent", value=str(data.get("consent")).lower())
    return response

# [5] 스캐너 앱 연동 및 프록시 중계 서버
@app.post("/start-scanner")
async def start_scanner(request: Request):
    try:
        token = request.cookies.get("user_session")
        if not token:
            return {"status": "error", "message": "로그인이 필요합니다."}

        consent_status = request.cookies.get("user_consent", "true")

        active_window = gw.getActiveWindow()
        if active_window:
            active_window.minimize() 

        # 🌟 구워진 데스크톱 앱(exe)을 실행합니다
        subprocess.Popen(["scan_corr.exe", token, consent_status])
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/analyze")
async def proxy_analyze(request: Request):
    try:
        data = await request.json()
        token = request.headers.get("Authorization")
        headers = {"Authorization": token} if token and token != "None" else {}

        res = requests.post(f"{BACKEND_URL}/analyze", json=data, headers=headers, timeout=15)
        return JSONResponse(status_code=res.status_code, content=res.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "중계 서버 오류"})

@app.post("/save")
async def proxy_save(request: Request):
    try:
        token = request.headers.get("Authorization")
        data = await request.json()
        
        res = requests.post(f"{BACKEND_URL}/save", json=data, headers={"Authorization": token}, timeout=5)
        return JSONResponse(status_code=res.status_code, content=res.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.get("/api/check-email")
async def check_email(email: str):
    try:
        res = requests.get(f"{BACKEND_URL}/check-email?email={email}", timeout=3)
        if res.status_code == 200:
            return JSONResponse(content={"available": res.json().get("available")})
        return JSONResponse(content={"available": False})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# [6] 서버 실행부
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)

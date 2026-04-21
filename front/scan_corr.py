import threading, time, sys, json, textwrap, asyncio
import requests, pyperclip, pyautogui, psutil, websockets, ctypes
import pygetwindow as gw
import customtkinter as ctk
from pynput import keyboard
import os
import urllib.parse
import winreg
import re

# [A] 스캐너 중복 실행 방지 (Highlander 패턴 유지)
current_pid = os.getpid() 
for proc in psutil.process_iter(['pid', 'name']):
    try:
        if proc.info['name'] == 'scan_corr.exe' and proc.info['pid'] != current_pid:
            proc.kill() 
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

AUTH_TOKEN = None

# 한글 깨짐 방지용 인코딩 세팅
if sys.stdout and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# [B] URI 스킴 자동 등록 
def register_uri_scheme():
    try:
        exe_path = os.path.abspath(sys.argv[0])
        key_path = r"Software\Classes\toneguard"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "ToneGuard Scanner")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
    except Exception:
        pass  

# [1] API 및 기본 설정 
API_ANALYZE_URL = "http://192.168.0.6:8888/analyze"
API_SAVE_URL = "http://192.168.0.6:8888/save"

raw_arg = sys.argv[1] if len(sys.argv) > 1 else ""
USER_TOKEN = ""
USER_CONSENT = "true"

# 정규식 필터 유지
if "token=" in raw_arg:
    token_match = re.search(r'token=([^&]+)', raw_arg)
    consent_match = re.search(r'consent=([^&]+)', raw_arg)
    
    if token_match:
        USER_TOKEN = token_match.group(1).replace("Bearer ", "").replace("Bearer%20", "").strip()
        
    if consent_match:
        USER_CONSENT = consent_match.group(1).strip().lower()
else:
    USER_TOKEN = raw_arg.strip()
    USER_CONSENT = sys.argv[2].lower() if len(sys.argv) > 2 else "true"

# 🚨 [여기에 방어막 코드 추가!] 🚨토큰(USER_TOKEN)이 비어있다면? = 웹사이트를 통하지 않고 바탕화면에서 직접 켰다면!
if not USER_TOKEN:
    import ctypes
    # 윈도우 기본 경고창 띄우기
    ctypes.windll.user32.MessageBoxW(
        0, 
        "스캐너 단독으로는 실행할 수 없습니다.\n\n웹사이트에 접속하여 로그인한 뒤, [스캔 시작] 버튼을 눌러 실행해 주세요.", 
        "ToneGuard 실행 안내", 
        0x30 | 0x0  # 경고 아이콘(0x30) + 확인 버튼(0x0)
    )
    sys.exit()  # 프로그램 즉시 종료!

TARGET_APPS = ["kakaotalk", "slack", "discord", "telegram", "line"]
typing_timer = None

# [2] 텍스트 캡처 로직
def capture_text(app):
    if not app.filter_on or not app.is_scanning or app.is_popup_open: return
    
    app.is_popup_open = True
    app.fixed_popup_x = app.fixed_popup_y = None
    time.sleep(0.1)
    pyperclip.copy('')
    
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.2)
    
    try:
        txt = pyperclip.paste()
        if txt.strip():
            app.btn_scan.configure(text="분석 중...", fg_color="#F59E0B")
            threading.Thread(target=analyze_text, args=(app, txt,), daemon=True).start()
        else:
            app.is_popup_open = False
    except:
        app.is_popup_open = False

# [3] 제어판 UI 구성
def setup_scanner_ui(app):
    card = ctk.CTkFrame(app.scanner_frame, corner_radius=20, fg_color="#1E293B", border_width=1, border_color="#3B82F6")
    card.pack(pady=10, padx=10, fill="both", expand=True)
    
    top = ctk.CTkFrame(card, fg_color="transparent")
    top.pack(fill="x", padx=15, pady=10)
    
    app.switch_filter = ctk.CTkSwitch(top, text="AUTO", font=("Pretendard", 12, "bold"), command=lambda: toggle_filter(app), width=50)
    app.switch_filter.pack(side="left")
    ctk.CTkButton(top, text="Main", font=("Pretendard", 11, "bold"), fg_color="#334155", width=50, height=24, command=app.close_scanner_window).pack(side="left", padx=10)
    
    app.slider_alpha = ctk.CTkSlider(top, from_=0.4, to=1.0, width=80, command=lambda v: app.attributes('-alpha', v))
    app.slider_alpha.set(1.0)
    app.slider_alpha.pack(side="right")

    app.btn_scan = ctk.CTkButton(card, text="스캔 시작", command=lambda: toggle_scan(app), font=("Pretendard", 16, "bold"), width=180, height=45, corner_radius=25)
    app.btn_scan.pack(expand=True, pady=(5, 5))
    app.lbl_status = ctk.CTkLabel(card, text="Ready to Scan", font=("Pretendard", 11), text_color="#94A3B8")
    app.lbl_status.pack(side="bottom", pady=10)

def toggle_scan(app):
    app.is_scanning = not app.is_scanning
    if app.is_scanning:
        app.btn_scan.configure(text="STOP", fg_color="#EF4444", hover_color="#DC2626")
        app.lbl_status.configure(text="● 메신저 대기 중...", text_color="#10B981")
        app.switch_filter.select()
        app.filter_on = True
    else:
        app.btn_scan.configure(text="스캔 시작", fg_color="#3B82F6", hover_color="#2563EB")
        app.lbl_status.configure(text="Ready to Scan", text_color="#94A3B8")
        app.switch_filter.deselect()
        app.filter_on = False
        app.fixed_popup_x = app.fixed_popup_y = None

def toggle_filter(app): 
    app.filter_on = app.switch_filter.get()

# [4] 서버 API 연동 (분석 요청)
def analyze_text(app, txt):
    global AUTH_TOKEN
    try:
        current_token = AUTH_TOKEN if AUTH_TOKEN else f"Bearer {USER_TOKEN}"
        headers = {"Authorization": current_token}
        res = requests.post(API_ANALYZE_URL, json={"text": txt.strip()}, headers=headers, timeout=15)
        
        app.btn_scan.configure(text="STOP" if app.is_scanning else "SCAN START", fg_color="#EF4444" if app.is_scanning else "#3B82F6")

        if res.status_code == 200:
            data = res.json()
            app.after(0, lambda: show_popup(app, txt, data.get("corrections", {}), data.get("context_type", "일반")))
        else:
            app.is_popup_open = False
    except:
        app.is_popup_open = False
        # 🚨 해결 2: 에러 발생 시 UI가 '스캔 시작(파란색)'으로 꼬여버리는 현상 방지
        # 현재 상태(스캔 중인지 아닌지)에 맞게 버튼을 정확히 복구합니다.
        if app.is_scanning:
            app.btn_scan.configure(text="STOP", fg_color="#EF4444", hover_color="#DC2626")
        else:
            app.btn_scan.configure(text="스캔 시작", fg_color="#3B82F6", hover_color="#2563EB")

# [5] 팝업창 UI 및 교정 텍스트 복사 적용
def show_popup(app, original, corrs, context):
    pop = ctk.CTkToplevel(app)
    pop.title("ToneGuard AI")
    pop.attributes('-topmost', True)
    
    if app.fixed_popup_x is None:
        mx, my = pyautogui.position()
        app.fixed_popup_x, app.fixed_popup_y = mx - 190, max(10, my - 310)
    pop.geometry(f"300x250+{app.fixed_popup_x}+{app.fixed_popup_y}")
    pop.configure(fg_color="#0F172A")

    def close():
        app.is_popup_open = False
        pop.destroy()
        
    pop.protocol("WM_DELETE_WINDOW", close)
    pop.bind("<Escape>", lambda e: close())

    header = ctk.CTkFrame(pop, fg_color="transparent")
    header.pack(fill="x", padx=15, pady=(12, 8))
    ctk.CTkButton(header, text="↺ 재분석", width=70, height=28, fg_color="#F59E0B", text_color="black", font=("Pretendard", 11, "bold"), command=lambda: [close(), threading.Thread(target=analyze_text, args=(app, original,), daemon=True).start()]).pack(side="left")
    ctk.CTkLabel(header, text=f"[{context}] 분석 완료", font=("Pretendard", 12, "bold"), text_color="#3B82F6").pack(side="right")

    for name, key, color in [("정중하게", "polite", "#2563EB"), ("친근하게", "friendly", "#10B981"), ("단호하게", "firm", "#475569")]:
        corr_text = corrs.get(key, "내용 없음")
        display_text = f"[{name}]\n{textwrap.fill(corr_text, width=25)}"
        ctk.CTkButton(pop, text=display_text, width=270, height=55, fg_color="#1E293B", border_color=color, border_width=1, font=("Pretendard", 12), command=lambda t=corr_text, n=name: apply_text(app, t, n, original, context, close)).pack(pady=3, padx=7)

def apply_text(app, corr, tone, orig, ctx, close_fn):
    global AUTH_TOKEN, USER_CONSENT
    try: pyperclip.copy(corr)
    except: pass
    
    app.is_pasting = True
    close_fn()
    
    def paste_and_save():
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'v')
        app.is_pasting = False
        
        # USER_CONSENT가 "true"일 때만 전송
        if USER_CONSENT == "true":
            try: 
                requests.post(API_SAVE_URL, json={"upload_text": orig, "corr_text": corr, "tone_type": ctx, "selected_tone": tone}, headers={"Authorization": AUTH_TOKEN if AUTH_TOKEN else f"Bearer {USER_TOKEN}"}, timeout=5)
            except: pass
            
    threading.Thread(target=paste_and_save, daemon=True).start()

# [6] 메인 앱 클래스 및 타겟 창 감시
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Scanner")
        win_w, win_h = 240, 210
        self.geometry(f"{win_w}x{win_h}+{self.winfo_screenwidth() - win_w - 30}+30")
        self.attributes('-topmost', True)
        self.is_scanning = self.filter_on = self.is_popup_open = self.is_pasting = False
        self.fixed_popup_x = self.fixed_popup_y = None
        
        self.scanner_frame = ctk.CTkFrame(self, fg_color="#0F172A")
        self.scanner_frame.pack(fill="both", expand=True)
        setup_scanner_ui(self)

        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

    def on_key_press(self, key):
        if not self.is_scanning or not self.filter_on or self.is_popup_open or self.is_pasting: return
        try:
            active_win = gw.getActiveWindow()
            if not active_win: return
            win_title = active_win.title

            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try: proc_name = psutil.Process(pid.value).name().lower()
            except: proc_name = ""

            if not any(app in win_title.lower() or app in proc_name for app in TARGET_APPS):
                self.lbl_status.configure(text="일반 앱 사용 중...", text_color="#64748B")
                return

            display_name = "카카오톡" if "kakaotalk" in proc_name else (win_title[:10] + "..." if len(win_title) > 10 else win_title)
            self.lbl_status.configure(text=f"✅ {display_name} 감지됨!", text_color="#10B981")

            global typing_timer
            if typing_timer: typing_timer.cancel()
            
            # 타이머 2.0초
            typing_timer = threading.Timer(2.0, capture_text, args=[self])
            typing_timer.start()
        except: pass

    def close_scanner_window(self):
        self.keyboard_listener.stop()
        try:
            for win in gw.getWindowsWithTitle("ToneGuard"):
                if win.isMinimized: win.restore()
                win.activate()
        except: pass
        self.destroy()

# [7] 웹소켓 서버 (프론트 통신)
def start_websocket_thread(app_instance):
    async def websocket_handler(websocket):
        global AUTH_TOKEN, USER_CONSENT  
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get("command") == "START_SCAN":
                        AUTH_TOKEN = data.get("token")
                        if "consent" in data:
                            USER_CONSENT = str(data.get("consent")).lower()
                            
                        if not app_instance.is_scanning: 
                            app_instance.after(0, lambda: toggle_scan(app_instance))
                            
                    elif data.get("command") == "UPDATE_CONSENT":
                        USER_CONSENT = str(data.get("consent")).lower()

                except json.JSONDecodeError:
                    if message == "START_SCAN" and not app_instance.is_scanning:
                        app_instance.after(0, lambda: toggle_scan(app_instance))
        except websockets.exceptions.ConnectionClosed: pass

    async def start_websocket_server():
        async with websockets.serve(websocket_handler, "127.0.0.1", 8765):
            await asyncio.Future()

    def run_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_websocket_server())

    threading.Thread(target=run_server, daemon=True).start()

# [8] 프로그램 실행
if __name__ == "__main__":
    register_uri_scheme()  
    ctk.set_appearance_mode("dark")
    app = App()
    start_websocket_thread(app)
    app.mainloop()

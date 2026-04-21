import threading, time, sys, json, textwrap, asyncio # 시간 지연, 멀티태스킹, 문자열 처리 등 파이썬 기본 도구들
import requests, pyperclip, pyautogui, psutil, websockets, ctypes # 통신, 클립보드 복사, 키보드/마우스 제어, 프로세스 관리 등을 위한 외부 도구들
import pygetwindow as gw # 현재 화면에 띄워진 프로그램 창(예: 카카오톡)의 이름을 알아내기 위한 도구
import customtkinter as ctk # 예쁘고 둥근 모서리의 세련된 UI(버튼, 창)를 만들기 위한 디자인 도구
from pynput import keyboard # 사용자가 키보드를 치는 것을 실시간으로 감지하는 도구
import os
import urllib.parse
import winreg # 윈도우 레지스트리를 건드려 'toneguard://' 주소를 등록하기 위한 도구
import re # 문자열에서 필요한 부분(토큰 등)만 쏙쏙 뽑아내기 위한 정규표현식 도구

# =========================================================
# [A] 스캐너 중복 실행 방지 (Highlander 패턴 유지)
# =========================================================
current_pid = os.getpid() # 현재 방금 켜진 이 스캐너 프로그램의 고유 번호(PID)를 기억합니다.
for proc in psutil.process_iter(['pid', 'name']):
    try:
        # 내 컴퓨터에서 돌고 있는 모든 프로그램을 뒤져서, 이름이 'scan_corr.exe'인데 내 번호랑 다른 '과거의 나'를 찾습니다.
        if proc.info['name'] == 'scan_corr.exe' and proc.info['pid'] != current_pid:
            proc.kill() # 여러 개가 동시에 켜져서 꼬이는 것을 막기 위해, 예전 프로그램은 즉시 종료시킵니다.
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass # 프로그램이 이미 꺼졌거나 권한이 없어서 못 끄는 에러는 그냥 무시하고 넘어갑니다.

AUTH_TOKEN = None # 웹사이트에서 발급받은 로그인 입장권(토큰)을 기억해둘 빈 바구니입니다.

# 콘솔창(터미널)에 한글을 출력할 때 글자가 깨지지 않도록 기본 인코딩을 UTF-8로 강제 설정합니다.
if sys.stdout and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# =========================================================
# [B] URI 스킴 자동 등록 (웹사이트에서 버튼 누르면 앱이 켜지게 하는 마법)
# =========================================================
def register_uri_scheme():
    try:
        exe_path = os.path.abspath(sys.argv[0]) # 현재 이 프로그램(exe)이 깔려있는 진짜 위치를 찾습니다.
        key_path = r"Software\Classes\toneguard"
        # 윈도우 레지스트리에 'toneguard://' 라는 나만의 주소를 등록합니다.
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "ToneGuard Scanner")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        # 그 주소를 누르면 바로 이 exe 프로그램이 켜지도록 연결해 줍니다.
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
    except Exception:
        pass  # 혹시 백신 프로그램 등이 막아서 실패해도 앱이 튕기지 않게 조용히 넘어갑니다.

# =========================================================
# [1] API 및 기본 설정
# =========================================================
# 분석과 저장을 담당하는 파이썬 중계 서버의 주소입니다.
API_ANALYZE_URL = "http://192.168.0.6:8888/analyze"
API_SAVE_URL = "http://192.168.0.6:8888/save"

# 웹사이트에서 'toneguard://...' 로 앱을 켰을 때, 뒤에 꼬리표처럼 달고 온 텍스트를 통째로 가져옵니다.
raw_arg = sys.argv[1] if len(sys.argv) > 1 else ""
USER_TOKEN = ""
USER_CONSENT = "true"

# 정규식을 이용해 꼬리표 안에서 'token=' 부분과 'consent=' 부분의 데이터를 깔끔하게 분리해냅니다.
if "token=" in raw_arg:
    token_match = re.search(r'token=([^&]+)', raw_arg)
    consent_match = re.search(r'consent=([^&]+)', raw_arg)
    
    if token_match:
        # 쓸데없는 'Bearer' 글자나 공백을 떼어내고 순수 토큰만 저장합니다.
        USER_TOKEN = token_match.group(1).replace("Bearer ", "").replace("Bearer%20", "").strip()
        
    if consent_match:
        # 데이터 저장 동의 여부를 뽑아내서 소문자(true/false)로 저장합니다.
        USER_CONSENT = consent_match.group(1).strip().lower()
else:
    # 꼬리표가 예전 방식일 경우를 대비한 호환성 코드입니다.
    USER_TOKEN = raw_arg.strip()
    USER_CONSENT = sys.argv[2].lower() if len(sys.argv) > 2 else "true"

# 🚨 [방어막 코드] 웹사이트를 거치지 않고 바탕화면에서 아이콘을 더블클릭해서 켰을 경우!
if not USER_TOKEN:
    import ctypes
    # 윈도우 기본 경고창을 띄워 사용자에게 웹사이트에서 켜야 한다고 친절히 안내합니다.
    ctypes.windll.user32.MessageBoxW(
        0, 
        "스캐너 단독으로는 실행할 수 없습니다.\n\n웹사이트에 접속하여 로그인한 뒤, [스캔 시작] 버튼을 눌러 실행해 주세요.", 
        "ToneGuard 실행 안내", 
        0x30 | 0x0  # 0x30은 노란색 경고 아이콘, 0x0은 [확인] 버튼 하나만 띄우라는 의미입니다.
    )
    sys.exit()  # 안내창을 띄우고 나면 프로그램을 즉시 종료시킵니다.

# 스캐너가 감시할 메신저 프로그램들의 이름 목록입니다.
TARGET_APPS = ["kakaotalk", "slack", "discord", "telegram", "line"]
typing_timer = None # 타이핑이 끝났는지 확인하기 위한 타이머 변수입니다.

# =========================================================
# [2] 텍스트 캡처 로직 (키보드로 친 글자 가져오기)
# =========================================================
def capture_text(app):
    # 스캐너가 꺼져 있거나, 이미 팝업이 떠 있는 상태라면 글자를 긁어오지 않습니다.
    if not app.filter_on or not app.is_scanning or app.is_popup_open: return
    
    app.is_popup_open = True # 이제 팝업을 띄울 거니까 다른 작업은 잠시 멈추라고 깃발을 듭니다.
    app.fixed_popup_x = app.fixed_popup_y = None # 팝업이 뜰 위치를 초기화합니다.
    time.sleep(0.1)
    pyperclip.copy('') # 클립보드(복사 공간)를 텅 비웁니다.
    
    # 키보드의 Ctrl + A (전체 선택)를 눌러서 내가 친 글자를 블록 지정합니다.
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    # 키보드의 Ctrl + C (복사)를 눌러서 블록 지정된 글자를 클립보드로 가져옵니다.
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.2)
    
    try:
        txt = pyperclip.paste() # 방금 복사한 글자를 변수(txt)에 담습니다.
        if txt.strip(): # 글자가 한 글자라도 비어있지 않다면
            app.btn_scan.configure(text="분석 중...", fg_color="#F59E0B") # 버튼을 노란색 '분석 중...'으로 바꿉니다.
            # 화면이 멈추지 않게 백그라운드(스레드)에서 서버로 분석 요청을 보냅니다.
            threading.Thread(target=analyze_text, args=(app, txt,), daemon=True).start()
        else:
            # 복사된 글자가 없으면 팝업 상태를 해제하고 다시 대기합니다.
            app.is_popup_open = False
    except:
        app.is_popup_open = False # 에러가 나도 스캐너가 먹통이 되지 않게 팝업 상태를 해제합니다.

# =========================================================
# [3] 제어판 UI 구성 (스캐너의 작은 윈도우 창 디자인)
# =========================================================
def setup_scanner_ui(app):
    # 전체를 감싸는 둥글고 네이비색인 예쁜 카드 배경을 만듭니다.
    card = ctk.CTkFrame(app.scanner_frame, corner_radius=20, fg_color="#1E293B", border_width=1, border_color="#3B82F6")
    card.pack(pady=10, padx=10, fill="both", expand=True)
    
    # 상단 메뉴바 (Auto 스위치, Main 버튼, 투명도 조절기)를 담을 투명 박스를 만듭니다.
    top = ctk.CTkFrame(card, fg_color="transparent")
    top.pack(fill="x", padx=15, pady=10)
    
    # [AUTO] 기능 껐다 켜는 스위치 (클릭 시 toggle_filter 실행)
    app.switch_filter = ctk.CTkSwitch(top, text="AUTO", font=("Pretendard", 12, "bold"), command=lambda: toggle_filter(app), width=50)
    app.switch_filter.pack(side="left")
    
    # 프로그램 창을 꺼버리고 백그라운드로 숨는 [Main] 버튼
    ctk.CTkButton(top, text="Main", font=("Pretendard", 11, "bold"), fg_color="#334155", width=50, height=24, command=app.close_scanner_window).pack(side="left", padx=10)
    
    # 스캐너 창의 투명도를 조절하는 슬라이더 (0.4 ~ 1.0)
    app.slider_alpha = ctk.CTkSlider(top, from_=0.4, to=1.0, width=80, command=lambda v: app.attributes('-alpha', v))
    app.slider_alpha.set(1.0) # 기본값은 불투명(1.0)
    app.slider_alpha.pack(side="right")

    # 중앙의 크고 파란 [스캔 시작] 버튼
    app.btn_scan = ctk.CTkButton(card, text="스캔 시작", command=lambda: toggle_scan(app), font=("Pretendard", 16, "bold"), width=180, height=45, corner_radius=25)
    app.btn_scan.pack(expand=True, pady=(5, 5))
    
    # 하단의 현재 상태를 알려주는 작은 회색 글씨 (Ready to Scan)
    app.lbl_status = ctk.CTkLabel(card, text="Ready to Scan", font=("Pretendard", 11), text_color="#94A3B8")
    app.lbl_status.pack(side="bottom", pady=10)

# 중앙의 [스캔 시작 / STOP] 버튼을 눌렀을 때 상태를 바꿔주는 함수입니다.
def toggle_scan(app):
    app.is_scanning = not app.is_scanning # 스캔 상태를 반대로 뒤집습니다 (켜짐 <-> 꺼짐).
    if app.is_scanning:
        # 스캔이 켜지면 버튼을 빨간색 STOP으로 바꾸고 감지를 시작합니다.
        app.btn_scan.configure(text="STOP", fg_color="#EF4444", hover_color="#DC2626")
        app.lbl_status.configure(text="● 메신저 대기 중...", text_color="#10B981")
        app.switch_filter.select() # AUTO 스위치도 강제로 켭니다.
        app.filter_on = True
    else:
        # 스캔이 꺼지면 원래 파란색 버튼으로 되돌립니다.
        app.btn_scan.configure(text="스캔 시작", fg_color="#3B82F6", hover_color="#2563EB")
        app.lbl_status.configure(text="Ready to Scan", text_color="#94A3B8")
        app.switch_filter.deselect() # AUTO 스위치도 끕니다.
        app.filter_on = False
        app.fixed_popup_x = app.fixed_popup_y = None # 팝업 위치 초기화

# AUTO 스위치를 수동으로 클릭했을 때 필터 상태를 변경하는 함수입니다.
def toggle_filter(app): 
    app.filter_on = app.switch_filter.get()

# =========================================================
# [4] 서버 API 연동 (AI에게 문장 분석 요청하기)
# =========================================================
def analyze_text(app, txt):
    global AUTH_TOKEN
    try:
        # 웹소켓으로 받은 토큰이 있으면 그걸 쓰고, 없으면 처음에 프로그램 켤 때 받은 토큰을 씁니다.
        current_token = AUTH_TOKEN if AUTH_TOKEN else f"Bearer {USER_TOKEN}"
        headers = {"Authorization": current_token}
        
        # 내가 친 글자(txt)를 포장해서 중계 서버(192.168.0.6)로 분석해달라고 던집니다.
        res = requests.post(API_ANALYZE_URL, json={"text": txt.strip()}, headers=headers, timeout=15)
        
        # 분석이 끝났으니 중앙 버튼을 다시 원래 스캔 상태 색상으로 복원합니다.
        app.btn_scan.configure(text="STOP" if app.is_scanning else "SCAN START", fg_color="#EF4444" if app.is_scanning else "#3B82F6")

        if res.status_code == 200: # 서버가 정상적으로 교정 문장들을 만들어줬다면
            data = res.json()
            # UI가 멈추지 않도록 안전하게 show_popup 함수를 불러서 팝업창을 띄웁니다.
            app.after(0, lambda: show_popup(app, txt, data.get("corrections", {}), data.get("context_type", "일반")))
        else:
            app.is_popup_open = False # 서버 에러 시 팝업 취소
    except:
        app.is_popup_open = False # 인터넷 끊김 등 에러 발생 시 팝업 취소
        # 🚨 [해결 2] 분석 중 인터넷이 끊겨도 버튼이 꼬이지 않도록, 현재 스캔 상태에 맞게 버튼을 정확히 복구합니다.
        if app.is_scanning:
            app.btn_scan.configure(text="STOP", fg_color="#EF4444", hover_color="#DC2626")
        else:
            app.btn_scan.configure(text="스캔 시작", fg_color="#3B82F6", hover_color="#2563EB")

# =========================================================
# [5] 팝업창 UI 및 교정 텍스트 복사 적용 (AI가 준 답변을 화면에 띄움)
# =========================================================
def show_popup(app, original, corrs, context):
    pop = ctk.CTkToplevel(app) # 메인 창 외에 새로 뜨는 작은 팝업창을 만듭니다.
    pop.title("ToneGuard AI")
    pop.attributes('-topmost', True) # 팝업창이 항상 맨 위에 보이게 고정합니다.
    
    # 팝업창이 마우스 커서 근처에 예쁘게 뜨도록 위치를 계산합니다.
    if app.fixed_popup_x is None:
        mx, my = pyautogui.position()
        app.fixed_popup_x, app.fixed_popup_y = mx - 190, max(10, my - 310)
    pop.geometry(f"300x250+{app.fixed_popup_x}+{app.fixed_popup_y}")
    pop.configure(fg_color="#0F172A") # 팝업창 배경색

    # 팝업을 닫을 때 스캐너가 다시 글자를 잡을 수 있도록 깃발(is_popup_open)을 내립니다.
    def close():
        app.is_popup_open = False
        pop.destroy()
        
    pop.protocol("WM_DELETE_WINDOW", close) # X버튼 누르면 close 실행
    pop.bind("<Escape>", lambda e: close()) # ESC키 누르면 close 실행

    # 팝업 상단의 '↺ 재분석' 버튼과 '[업무체] 분석 완료' 글자를 배치합니다.
    header = ctk.CTkFrame(pop, fg_color="transparent")
    header.pack(fill="x", padx=15, pady=(12, 8))
    ctk.CTkButton(header, text="↺ 재분석", width=70, height=28, fg_color="#F59E0B", text_color="black", font=("Pretendard", 11, "bold"), command=lambda: [close(), threading.Thread(target=analyze_text, args=(app, original,), daemon=True).start()]).pack(side="left")
    ctk.CTkLabel(header, text=f"[{context}] 분석 완료", font=("Pretendard", 12, "bold"), text_color="#3B82F6").pack(side="right")

    # 서버가 준 정중하게, 친근하게, 단호하게 3가지 말투의 교정 결과를 버튼으로 쭉 만들어 붙입니다.
    for name, key, color in [("정중하게", "polite", "#2563EB"), ("친근하게", "friendly", "#10B981"), ("단호하게", "firm", "#475569")]:
        corr_text = corrs.get(key, "내용 없음")
        display_text = f"[{name}]\n{textwrap.fill(corr_text, width=25)}" # 글자가 길면 여러 줄로 예쁘게 자릅니다.
        # 이 교정 문장 버튼을 클릭하면 apply_text 함수가 실행되면서 메신저에 붙여넣기 됩니다.
        ctk.CTkButton(pop, text=display_text, width=270, height=55, fg_color="#1E293B", border_color=color, border_width=1, font=("Pretendard", 12), command=lambda t=corr_text, n=name: apply_text(app, t, n, original, context, close)).pack(pady=3, padx=7)

# 사용자가 교정된 문장 중 하나를 클릭했을 때 실행되는 함수입니다.
def apply_text(app, corr, tone, orig, ctx, close_fn):
    global AUTH_TOKEN, USER_CONSENT
    try: pyperclip.copy(corr) # 클릭한 문장을 클립보드에 복사합니다.
    except: pass
    
    app.is_pasting = True # 방금 내가 붙여넣기를 했다고 깃발을 들어 스캐너가 오해하지 않게 합니다.
    close_fn() # 팝업창을 닫습니다.
    
    # 0.3초 뒤에 메신저 창에 자동으로 Ctrl+V(붙여넣기)를 시켜줍니다.
    def paste_and_save():
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'v')
        app.is_pasting = False # 붙여넣기 완료
        
        # 만약 사용자가 '데이터 저장'에 동의(true)했다면, 이 교정 기록을 서버 DB에 저장해달라고 보냅니다.
        if USER_CONSENT == "true":
            try: 
                requests.post(API_SAVE_URL, json={"upload_text": orig, "corr_text": corr, "tone_type": ctx, "selected_tone": tone}, headers={"Authorization": AUTH_TOKEN if AUTH_TOKEN else f"Bearer {USER_TOKEN}"}, timeout=5)
            except: pass
            
    threading.Thread(target=paste_and_save, daemon=True).start()

# =========================================================
# [6] 메인 앱 클래스 및 타겟 창(메신저) 감시 로직
# =========================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Scanner") # 프로그램 이름
        win_w, win_h = 240, 210 # 창 크기
        # 모니터 오른쪽 아래 구석에 프로그램이 켜지도록 위치를 설정합니다.
        self.geometry(f"{win_w}x{win_h}+{self.winfo_screenwidth() - win_w - 30}+30")
        self.attributes('-topmost', True) # 스캐너 제어판은 항상 위에 떠 있게 합니다.
        
        # 스캐너의 현재 상태를 나타내는 변수들을 모두 False로 초기화합니다.
        self.is_scanning = self.filter_on = self.is_popup_open = self.is_pasting = False
        self.fixed_popup_x = self.fixed_popup_y = None
        
        self.scanner_frame = ctk.CTkFrame(self, fg_color="#0F172A")
        self.scanner_frame.pack(fill="both", expand=True)
        setup_scanner_ui(self) # 위에서 만든 UI를 이 화면에 붙입니다.

        # 백그라운드에서 키보드 타이핑 소리를 조용히 듣고 있는 감시자를 켭니다.
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

    # 사용자가 키보드를 아무거나 한 글자라도 누를 때마다 실행되는 함수입니다.
    def on_key_press(self, key):
        # 스캔이 꺼져 있거나 팝업이 떠있으면 감시를 무시합니다.
        if not self.is_scanning or not self.filter_on or self.is_popup_open or self.is_pasting: return
        try:
            active_win = gw.getActiveWindow() # 지금 사용자가 클릭해서 보고 있는 맨 앞 창을 가져옵니다.
            if not active_win: return
            win_title = active_win.title # 그 창의 제목(예: "카카오톡", "크롬")

            # 프로그램의 진짜 영문 이름(프로세스명)을 알아내기 위한 윈도우 고급 기술입니다.
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try: proc_name = psutil.Process(pid.value).name().lower()
            except: proc_name = ""

            # 창 제목이나 프로세스명에 TARGET_APPS(카톡, 슬랙 등)가 안 들어있으면 그냥 넘어갑니다.
            if not any(app in win_title.lower() or app in proc_name for app in TARGET_APPS):
                self.lbl_status.configure(text="일반 앱 사용 중...", text_color="#64748B")
                return

            # 카톡이나 슬랙이 맞다면, UI 하단에 "✅ 카카오톡 감지됨!" 이라고 예쁘게 표시합니다.
            display_name = "카카오톡" if "kakaotalk" in proc_name else (win_title[:10] + "..." if len(win_title) > 10 else win_title)
            self.lbl_status.configure(text=f"✅ {display_name} 감지됨!", text_color="#10B981")

            global typing_timer
            # 타이핑 중에는 계속 타이머를 취소시킵니다 (글자를 치고 있을 땐 분석하지 않음).
            if typing_timer: typing_timer.cancel()
            
            # 마지막으로 타자를 친 후, 정확히 2.0초 동안 아무 입력이 없으면 비로소 capture_text(분석 시작)를 실행합니다.
            typing_timer = threading.Timer(2.0, capture_text, args=[self])
            typing_timer.start()
        except: pass

    # 제어판의 [Main] 버튼을 눌러 스캐너 창을 껐을 때 실행되는 함수입니다.
    def close_scanner_window(self):
        self.keyboard_listener.stop() # 키보드 감시를 끕니다.
        self.destroy() # 화면 창을 없앱니다 (단, 웹사이트에서 다시 부를 때까지 백그라운드 서버는 살려둡니다).

# =========================================================
# [7] 웹소켓 서버 (웹사이트와 스캐너가 실시간으로 대화하는 비밀 통로)
# =========================================================
def start_websocket_thread(app_instance):
    # 웹사이트에서 암호(메시지)를 보내면 처리하는 함수입니다.
    async def websocket_handler(websocket):
        global AUTH_TOKEN, USER_CONSENT  
        try:
            async for message in websocket:
                try:
                    data = json.loads(message) # 웹사이트가 보낸 JSON 데이터를 해독합니다.
                    
                    # 1. 웹사이트에서 [스캔 시작] 버튼을 눌렀을 때
                    if data.get("command") == "START_SCAN":
                        AUTH_TOKEN = data.get("token") # 새로 발급된 따끈따끈한 토큰으로 교체합니다.
                        if "consent" in data:
                            USER_CONSENT = str(data.get("consent")).lower() # 동의 여부도 새로 갱신합니다.
                            
                        # 스캐너가 꺼져 있다면 자동으로 스캔을 켭니다(빨간색 STOP 버튼 상태로 됨).
                        if not app_instance.is_scanning: 
                            app_instance.after(0, lambda: toggle_scan(app_instance))
                            
                    # 2. 마이페이지에서 [데이터 저장 동의] 스위치를 껐다 켰을 때
                    elif data.get("command") == "UPDATE_CONSENT":
                        # 즉시 스캐너의 머릿속에 있는 동의 상태를 업데이트합니다! (문제 해결의 핵심 🌟)
                        USER_CONSENT = str(data.get("consent")).lower()

                except json.JSONDecodeError:
                    # 예전 방식(글자만 보내는 방식)으로 [스캔 시작]이 오면 호환성을 위해 처리해 줍니다.
                    if message == "START_SCAN" and not app_instance.is_scanning:
                        app_instance.after(0, lambda: toggle_scan(app_instance))
        except websockets.exceptions.ConnectionClosed: pass

    # 내 컴퓨터의 8765번 포트에 귓속말을 들을 수 있는 비밀 통로를 열어둡니다.
    async def start_websocket_server():
        async with websockets.serve(websocket_handler, "127.0.0.1", 8765):
            await asyncio.Future() # 프로그램이 꺼질 때까지 계속 귀를 열고 대기합니다.

    # 윈도우 창이 멈추지 않게 백그라운드 스레드에서 통신 서버를 돌립니다.
    def run_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_websocket_server())

    threading.Thread(target=run_server, daemon=True).start()

# =========================================================
# [8] 프로그램 시작점 (아이콘을 더블클릭하거나 웹사이트가 부를 때 제일 먼저 실행되는 곳)
# =========================================================
if __name__ == "__main__":
    register_uri_scheme()  # 윈도우에 'toneguard://' 주소를 등록합니다.
    ctk.set_appearance_mode("dark") # 프로그램의 전체 색상 테마를 세련된 다크모드로 맞춥니다.
    app = App() # 위에서 만든 메인 앱(화면+감시자)을 준비합니다.
    start_websocket_thread(app) # 웹사이트의 말을 들을 수 있는 웹소켓 통신망을 오픈합니다.
    app.mainloop() # 이제 화면을 띄우고 무한 루프를 돌며 사용자의 입력을 기다립니다.

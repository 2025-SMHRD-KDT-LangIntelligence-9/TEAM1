import customtkinter as ctk
import threading, pyautogui, pyperclip, time, requests, textwrap, sys
import pygetwindow as gw
from pynput import keyboard
import ctypes  # 윈도우 시스템에 접근하기 위한 라이브러리
import psutil  # 실행 중인 프로세스(exe)를 확인하기 위한 라이브러리

# =====================================================================
# [1] API 설정 및 사용자 인증 토큰 수신
# =====================================================================
API_ANALYZE_URL = "http://192.168.0.77:8000/analyze"
API_SAVE_URL = "http://192.168.0.77:8000/save"

USER_TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
# 🌟 [이 줄을 추가해 주세요!] main.py가 넘겨준 두 번째 인자(동의 상태)를 받습니다.
USER_CONSENT = sys.argv[2] if len(sys.argv) > 2 else "true"
typing_timer = None

# 🎯 [핵심] 우리가 감시할 앱 명단 (영어 exe 이름과 한글 제목 모두 포함)
TARGET_APPS = ["kakaotalk", "slack", "discord", "telegram", "line"]


# =====================================================================
# [2] 텍스트 캡처 로직 (메신저가 확인된 상태에서만 실행됨)
# =====================================================================
def capture_text(app):
    if not app.filter_on or not app.is_scanning or app.is_popup_open: 
        return

    app.is_popup_open = True 
    app.fixed_popup_x = app.fixed_popup_y = None
    
    time.sleep(0.1)
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
    except Exception:
        app.is_popup_open = False

# =====================================================================
# [3] 제어판 UI
# =====================================================================
def setup_scanner_ui(app):
    main_card = ctk.CTkFrame(app.scanner_frame, corner_radius=20, fg_color="#1E293B", border_width=1, border_color="#3B82F6") 
    main_card.pack(pady=10, padx=10, fill="both", expand=True)
    
    top = ctk.CTkFrame(main_card, fg_color="transparent")
    top.pack(fill="x", padx=15, pady=10)
    
    app.switch_filter = ctk.CTkSwitch(top, text="AUTO", font=("Pretendard", 12, "bold"), command=lambda: toggle_filter(app), progress_color="#3B82F6", width=50)
    app.switch_filter.pack(side="left")

    ctk.CTkButton(top, text="Main", font=("Pretendard", 11, "bold"), fg_color="#334155", width=50, height=24, command=app.close_scanner_window).pack(side="left", padx=10)

    app.slider_alpha = ctk.CTkSlider(top, from_=0.4, to=1.0, width=80, command=lambda v: app.attributes('-alpha', v), button_color="#3B82F6", button_hover_color="#2563EB")
    app.slider_alpha.set(1.0); app.slider_alpha.pack(side="right")

    app.btn_scan = ctk.CTkButton(main_card, text="스캔 시작", command=lambda: toggle_scan(app), font=("Pretendard", 16, "bold"), width=180, height=45, corner_radius=25, fg_color="#3B82F6", text_color="white", hover_color="#2563EB")
    app.btn_scan.pack(expand=True, pady=(5, 5))
    
    app.lbl_status = ctk.CTkLabel(main_card, text="Ready to Scan", font=("Pretendard", 11), text_color="#94A3B8")
    app.lbl_status.pack(side="bottom", pady=10)

def toggle_scan(app):
    app.is_scanning = not app.is_scanning
    if app.is_scanning:
        app.btn_scan.configure(text="STOP", fg_color="#EF4444", hover_color="#DC2626")
        app.lbl_status.configure(text="● 메신저 대기 중...", text_color="#10B981")
        app.switch_filter.select(); app.filter_on = True
    else:
        app.btn_scan.configure(text="스캔 시작", fg_color="#3B82F6", hover_color="#2563EB")
        app.lbl_status.configure(text="Ready to Scan", text_color="#94A3B8")
        app.switch_filter.deselect(); app.filter_on = False
        app.fixed_popup_x = app.fixed_popup_y = None

def toggle_filter(app): 
    app.filter_on = app.switch_filter.get()

# =====================================================================
# [4] 백엔드 API 연동
# =====================================================================
def analyze_text(app, txt):
    try:
        headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        response = requests.post(API_ANALYZE_URL, json={"text": txt.strip()}, headers=headers, timeout=15)
        
        app.btn_scan.configure(text="STOP" if app.is_scanning else "SCAN START", fg_color="#EF4444" if app.is_scanning else "#3B82F6")

        if response.status_code == 200:
            res_data = response.json()
            app.after(0, lambda: show_popup(app, txt, res_data.get("corrections", {}), res_data.get("context_type", "일반")))
        else: 
            app.is_popup_open = False
    except Exception: 
        app.is_popup_open = False
        app.btn_scan.configure(text="STOP", fg_color="#EF4444")

# =====================================================================
# [5] 콤팩트 말투 교정 팝업창
# =====================================================================
def show_popup(app, original, corrs, context):
    pop = ctk.CTkToplevel(app)
    pop.title(f"ToneGuard AI")
    pop.attributes('-topmost', True)
    
    pop_w, pop_h = 300, 250 
    
    if app.fixed_popup_x is None:
        mx, my = pyautogui.position() 
        app.fixed_popup_x, app.fixed_popup_y = mx - 190, max(10, my - 310) 
    pop.geometry(f"{pop_w}x{pop_h}+{app.fixed_popup_x}+{app.fixed_popup_y}")
    pop.configure(fg_color="#0F172A") 

    def close(): 
        app.is_popup_open = False 
        pop.destroy()
    pop.protocol("WM_DELETE_WINDOW", close)

    header = ctk.CTkFrame(pop, fg_color="transparent")
    header.pack(fill="x", padx=15, pady=(12, 8))
    
    ctk.CTkButton(header, text="↺ 재분석", width=70, height=28, fg_color="#F59E0B", hover_color="#D97706", text_color="black", font=("Pretendard", 11, "bold"),
                  command=lambda: [close(), threading.Thread(target=analyze_text, args=(app, original,), daemon=True).start()]).pack(side="left")
    
    ctk.CTkLabel(header, text=f"[{context}] 분석 완료", font=("Pretendard", 12, "bold"), text_color="#3B82F6").pack(side="right")

    tones = [("정중하게", "polite", "#2563EB"), ("친근하게", "friendly", "#10B981"), ("단호하게", "firm", "#475569")]
    for name, key, color in tones:
        corr_text = corrs.get(key, "내용 없음")
        # 🌟 [여기 추가!] 글자가 버튼을 넘어가지 않도록 일정 글자 수(예: 23자)마다 강제 줄바꿈
        wrapped_text = textwrap.fill(corr_text, width=25)         
        display_text = f"[{name}]\n{wrapped_text}"
        
        btn = ctk.CTkButton(pop, text=display_text, width=270, height=55, fg_color="#1E293B", border_width=1, border_color=color,
                            hover_color="#334155", anchor="center", font=("Pretendard", 12), # 폰트 크기도 12로 살짝 줄이면 예쁩니다
                            command=lambda t=corr_text, n=name: apply_text(app, t, n, original, context, close))
        btn.pack(pady=3, padx=7) # 여백(pady, padx)도 살짝 줄였습니다

def apply_text(app, corr, tone, orig, ctx, close_fn):
    try: pyperclip.copy(corr)
    except: pass
    app.is_pasting = True 
    close_fn()
    
    def paste_and_save():
        time.sleep(0.3) 
        pyautogui.hotkey('ctrl', 'v')
        app.is_pasting = False
        
        # 🌟 [핵심] 동의(true) 상태일 때만 백엔드로 /save 요청을 날립니다!
        if USER_CONSENT.lower() == "true":
            try: 
                payload = {"upload_text": orig, "corr_text": corr, "tone_type": ctx, "selected_tone": tone}
                requests.post(API_SAVE_URL, json=payload, headers={"Authorization": f"Bearer {USER_TOKEN}"}, timeout=5)
            except: pass
            
    threading.Thread(target=paste_and_save, daemon=True).start()

# =====================================================================
# [6] 메인 앱 클래스 (강력한 메신저 감지 로직)
# =====================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Scanner")
        
        win_w, win_h = 240, 210
        scr_w = self.winfo_screenwidth()
        self.geometry(f"{win_w}x{win_h}+{scr_w - win_w - 30}+30")
        
        self.attributes('-topmost', True)
        self.is_scanning = False
        self.filter_on = False
        self.is_popup_open = False
        self.is_pasting = False
        self.fixed_popup_x = self.fixed_popup_y = None
        
        self.scanner_frame = ctk.CTkFrame(self, fg_color="#0F172A")
        self.scanner_frame.pack(fill="both", expand=True)
        setup_scanner_ui(self)

        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

    def on_key_press(self, key):
        if not self.is_scanning or not self.filter_on or self.is_popup_open or self.is_pasting:
            return
            
        try:
            active_win = gw.getActiveWindow()
            if not active_win: return
            win_title = active_win.title

            # ---------------------------------------------------------
            # 🔍 [추가됨] 프로세스(실행 파일) 이름 알아내기
            # ---------------------------------------------------------
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            try:
                proc_name = psutil.Process(pid.value).name().lower() # 예: 'kakaotalk.exe'
            except:
                proc_name = ""

            # 창 제목(win_title)이나 프로세스 이름(proc_name)에 타겟 앱이 있는지 2중 검사
            is_target = any(app in win_title.lower() or app in proc_name for app in TARGET_APPS)

            if not is_target:
                self.lbl_status.configure(text=f"일반 앱 사용 중...", text_color="#64748B")
                return

            # 화면에 표시할 이름 예쁘게 다듬기
            if "kakaotalk" in proc_name:
                display_name = "카카오톡"
            else:
                display_name = win_title[:10] + "..." if len(win_title) > 10 else win_title
                
            self.lbl_status.configure(text=f"✅ {display_name} 감지됨!", text_color="#10B981")

            global typing_timer
            if typing_timer is not None:
                typing_timer.cancel()
                
            typing_timer = threading.Timer(1.5, capture_text, args=[self])
            typing_timer.start()

        except Exception:
            pass

    def close_scanner_window(self):
        self.keyboard_listener.stop()
        try:
            windows = gw.getWindowsWithTitle("ToneGuard")
            for win in windows:
                try:
                    if win.isMinimized: win.restore()
                    win.activate()
                except: pass
        except: pass
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()

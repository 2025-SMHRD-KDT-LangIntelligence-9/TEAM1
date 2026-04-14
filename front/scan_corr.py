import customtkinter as ctk
import threading, pyautogui, pyperclip, time, requests, textwrap, sys
import pygetwindow as gw
from pynput import keyboard # 사용자 키보드 입력을 백그라운드에서 감지하기 위한 라이브러리

# =====================================================================
# [1] API 설정 및 사용자 인증 토큰 수신
# =====================================================================
API_ANALYZE_URL = "http://192.168.0.77:8000/analyze"
API_SAVE_URL = "http://192.168.0.77:8000/save"

# 웹 서버(main.py)에서 스캐너를 실행할 때 넘겨준 JWT 토큰을 받아옵니다.
# sys.argv[1]에 토큰 값이 들어있으며, 없다면 빈 문자열로 처리합니다.
USER_TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""

# 키보드 입력이 1.5초간 멈췄는지 체크하기 위한 전역 타이머 변수
typing_timer = None


# =====================================================================
# [2] 메신저 창 확인 및 텍스트 캡처 (모든 창 허용 - 강제 테스트 모드)
# =====================================================================
def capture_text(app):
    print("\n--- [디버그] 1.5초 대기 완료! 캡처 함수 실행 ---")
    
    if not app.filter_on or not app.is_scanning or app.is_popup_open: 
        print("[디버그] 스위치가 꺼져있거나 이미 팝업이 열려있어 중단합니다.")
        return

    # [수정] 메신저 창인지 검사하는 로직을 완전히 삭제했습니다. (메모장에서도 작동하도록)
    try:
        active_window = gw.getActiveWindow()
        if active_window:
            print(f"[디버그] 현재 글을 쓰고 있는 창: '{active_window.title}'")
    except:
        pass

    print("[디버그] 키보드 단축키(Ctrl+A, Ctrl+C) 강제 전송!")
    app.is_popup_open = True 
    app.fixed_popup_x = app.fixed_popup_y = None
    
    # [수정] 윈도우가 단축키를 인식할 수 있도록 딜레이를 조금 더 길게 줬습니다.
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    
    try:
        txt = pyperclip.paste()
        print(f"[디버그] 복사 성공! 클립보드 내용: '{txt}'")
        
        if txt.strip():
            print("[디버그] 백엔드로 텍스트 전송 시작...")
            threading.Thread(target=analyze_text, args=(app, txt,), daemon=True).start()
        else: 
            print("[디버그] 복사된 텍스트가 비어있습니다. (단축키가 안 먹혔을 확률 높음)")
            app.is_popup_open = False 
    except Exception as e:
        print(f"[디버그] 치명적 에러: 클립보드를 읽을 수 없습니다 ({e})")
        app.is_popup_open = False


# =====================================================================
# [3] UI 화면 구성 (스캐너 제어판)
# =====================================================================
def setup_scanner_ui(app):
    main_card = ctk.CTkFrame(app.scanner_frame, corner_radius=20, fg_color="#1e1e1e", border_width=1, border_color="#3d3d3d") 
    main_card.pack(pady=10, padx=10, fill="both", expand=True)
    
    top = ctk.CTkFrame(main_card, fg_color="transparent")
    top.pack(fill="x", padx=15, pady=15)
    
    app.switch_filter = ctk.CTkSwitch(top, text="ON", font=("맑은 고딕", 12, "bold"), command=lambda: toggle_filter(app), progress_color="#10b981", width=50)
    app.switch_filter.pack(side="left")

    ctk.CTkButton(top, text="메인", font=("맑은 고딕", 11), fg_color="#3d3d3d", width=50, height=24, command=app.close_scanner_window).pack(side="left", padx=10)

    app.slider_alpha = ctk.CTkSlider(top, from_=0.3, to=1.0, width=90, command=lambda v: app.attributes('-alpha', v))
    app.slider_alpha.set(1.0); app.slider_alpha.pack(side="right")

    app.btn_scan = ctk.CTkButton(main_card, text="스캔 시작", command=lambda: toggle_scan(app), font=("맑은 고딕", 16, "bold"), width=170, height=35, corner_radius=30, fg_color="#52D3D8", text_color="black")
    app.btn_scan.pack(expand=True)
    
    app.lbl_filter_desc = ctk.CTkLabel(main_card, text="OFF: Manual Mode", font=("맑은 고딕", 12), text_color="#a1a1aa")
    app.lbl_filter_desc.pack(side="bottom", pady=15)

def toggle_scan(app):
    app.is_scanning = not app.is_scanning
    if app.is_scanning:
        app.btn_scan.configure(text="중지", fg_color="#ef4444", text_color="white")
        app.lbl_filter_desc.configure(text="ON: 메신저 타이핑 대기중...", text_color="#10b981")
        app.switch_filter.select(); app.filter_on = True
    else:
        app.btn_scan.configure(text="스캔 시작", fg_color="#52D3D8", text_color="black")
        app.lbl_filter_desc.configure(text="OFF: 스캔 중지됨", text_color="#a1a1aa")
        app.switch_filter.deselect(); app.filter_on = False
        app.fixed_popup_x = app.fixed_popup_y = None

def toggle_filter(app): 
    app.filter_on = app.switch_filter.get()


# =====================================================================
# [4] 백엔드 API 연동 (디버깅 프린트 추가)
# =====================================================================
def analyze_text(app, txt):
    print(f"[디버그] 백엔드로 전송 시도... URL: {API_ANALYZE_URL}")
    try:
        headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        response = requests.post(API_ANALYZE_URL, json={"text": txt.strip()}, headers=headers, timeout=20)
        print(f"[디버그] 백엔드 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            res_data = response.json()
            print(f"[디버그] 백엔드 응답 데이터 수신 완료. 팝업 표시 시도.")
            app.after(0, lambda: show_popup(app, txt, res_data.get("corrections", {}), res_data.get("context_type", "일반")))
        else: 
            print(f"[디버그] 백엔드 에러 발생 (코드 {response.status_code}). 팝업 취소.")
            app.is_popup_open = False
            
    except Exception as e: 
        print(f"[디버그] 백엔드 연결 실패: {e}")
        app.is_popup_open = False


# =====================================================================
# [5] 말투 대안 제시 팝업창 띄우기
# =====================================================================
def show_popup(app, original, corrs, context):
    pop = ctk.CTkToplevel(app)
    pop.title(f"✨ 말투 교정 ({context})")
    pop.attributes('-topmost', True) # 다른 모든 창보다 항상 위에 떠있도록 설정
    pop_w, pop_h = 420, 360 
    
    # 팝업창 위치를 현재 마우스 포인터 주변(작성 중이던 텍스트 위쪽)으로 계산합니다.
    if app.fixed_popup_x is None:
        mx, my = pyautogui.position() 
        app.fixed_popup_x, app.fixed_popup_y = mx - 210, max(10, my - 300) 
    pop.geometry(f"{pop_w}x{pop_h}+{app.fixed_popup_x}+{app.fixed_popup_y}")

    # [중요] 팝업창 우측 상단 X 버튼을 눌러 닫을 때 상태 변수 초기화
    def close(): 
        app.is_popup_open = False 
        pop.destroy()
    pop.protocol("WM_DELETE_WINDOW", close)

    # 팝업 상단: 재분석 버튼 및 안내 텍스트
    top_frame = ctk.CTkFrame(pop, fg_color="transparent")
    top_frame.pack(fill="x", padx=20, pady=(15, 10))
    
    # 재분석 클릭 시: 팝업을 닫고 동일한 원문으로 analyze_text 스레드를 다시 실행합니다.
    btn_reanalyze = ctk.CTkButton(top_frame, text="재분석", width=100, height=35, fg_color="#F59E0B", 
                                  command=lambda: [close(), threading.Thread(target=analyze_text, args=(app, original,), daemon=True).start()])
    btn_reanalyze.pack(side="left", padx=(0, 20))
    ctk.CTkLabel(top_frame, text="적용할 말투 선택:", font=("맑은 고딕", 13, "bold"), text_color="white").pack(side="left")

    # 서버에서 받은 3가지 톤(정중함, 친근함, 단호함)에 맞춰 버튼을 생성합니다.
    tones = {"정중하게": "polite", "친근하게": "friendly", "단호하게": "firm"}
    for name, key in tones.items():
        corr_text = corrs.get(key, "교정 실패")
        wrapped = textwrap.fill(f"[{name}] {corr_text}", width=32)
        
        # 사용자가 이 대안을 클릭하면 apply_text 함수가 호출되어 교정문이 붙여넣기 됩니다.
        ctk.CTkButton(pop, text=wrapped, width=380, height=max(60, 20 + (wrapped.count('\n')+1)*22),
                      fg_color="#2563EB", hover_color="#1D4ED8", anchor="center", font=("맑은 고딕", 12),
                      command=lambda txt=corr_text, n=name: apply_text(app, txt, n, original, context, close)).pack(pady=6)


# =====================================================================
# [6] 사용자가 교정 문구를 선택했을 때 (실제 텍스트 변경 및 DB 저장)
# =====================================================================
def apply_text(app, corr, tone, orig, ctx, close_fn):
    # 1. 선택한 교정 문구를 시스템 클립보드에 복사하고, 팝업을 닫습니다.
    try:
        pyperclip.copy(corr)
    except Exception:
        pass
    app.is_pasting = True 
    close_fn() # 팝업 종료
    
    # 2. 백그라운드 스레드에서 메신저에 붙여넣기(Ctrl+V)를 실행하고 기록을 DB에 저장합니다.
    def paste_and_save():
        # 창이 완전히 닫히고 메신저 창에 포커스가 갈 때까지 아주 잠깐 대기합니다.
        time.sleep(0.35) 
        pyautogui.hotkey('ctrl', 'v')
        app.is_pasting = False # 붙여넣기 완료 플래그 해제
        
        try: 
            # 마이페이지에서 볼 수 있도록 백엔드의 /save API에 교정 기록을 전송합니다.
            payload = {"upload_text": orig, "corr_text": corr, "tone_type": ctx, "selected_tone": tone}
            requests.post(API_SAVE_URL, json=payload, headers={"Authorization": f"Bearer {USER_TOKEN}"}, timeout=5)
        except Exception: 
            pass
            
    threading.Thread(target=paste_and_save, daemon=True).start()


# =====================================================================
# [7] 메인 스캐너 앱 클래스 구동
# =====================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ToneGuard Scanner")
        
        # --- [수정된 부분: 우측 상단 자동 배치 로직] ---
        window_width = 250
        window_height = 200
        
        # 1. 사용자의 모니터 전체 해상도(너비)를 자동으로 읽어옵니다.
        screen_width = self.winfo_screenwidth()
        
        # 2. (모니터 끝 - 스캐너 너비 - 여백 20px)을 계산하여 X 좌표를 구합니다.
        x_position = screen_width - window_width - 20
        y_position = 20  # 위쪽에서 20px 여백을 줍니다.
        
        # 3. 크기와 위치를 세팅합니다. (형식: "너비x높이+X좌표+Y좌표")
        self.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        # -------------------------------------------------------------

        self.attributes('-topmost', True) # 제어판을 항상 화면 맨 위에 띄웁니다.
        
        # 각종 기능 상태를 관리하는 플래그(변수)들
        self.is_scanning = False
        self.filter_on = False
        self.is_popup_open = False
        self.is_pasting = False
        self.fixed_popup_x = None
        self.fixed_popup_y = None
        
        # 화면 요소 렌더링
        self.scanner_frame = ctk.CTkFrame(self)
        self.scanner_frame.pack(fill="both", expand=True)
        setup_scanner_ui(self)

        # 백그라운드 키보드 리스너 시작
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

    # 사용자가 키보드 자판을 하나 누를 때마다 호출되는 함수입니다.
    def on_key_press(self, key):
        # 스캔 기능이 꺼져있거나, 이미 처리 중(팝업, 붙여넣기)이면 작동하지 않습니다.
        if not self.is_scanning or not self.filter_on or self.is_popup_open or self.is_pasting:
            return
            
        global typing_timer
        # 키를 누를 때마다 진행 중이던 타이머를 즉시 취소합니다.
        if typing_timer is not None:
            typing_timer.cancel()
            
        # 키보드 입력이 멈춘 시점부터 다시 1.5초를 셉니다.
        # 1.5초 동안 아무 타자도 치지 않으면 capture_text 함수가 자동으로 실행됩니다.
        typing_timer = threading.Timer(1.5, capture_text, args=[self])
        typing_timer.start()

    def close_scanner_window(self):
        # 1. 백그라운드 키보드 리스너 종료
        self.keyboard_listener.stop()
        
        # 2. 강력한 메인 웹페이지 복구 로직
        try:
            # 브라우저 제목에 'ToneGuard'가 포함된 모든 창을 찾습니다.
            windows = gw.getWindowsWithTitle("ToneGuard")
            
            for win in windows:
                try:
                    # 유령 창이든 진짜 창이든 일단 모두 최소화 해제 및 활성화 시도
                    if win.isMinimized:
                        win.restore()  
                    win.activate()
                except Exception:
                    # 유령 창(제어 불가능한 창)에서 발생하는 에러는 튕기지 않게 조용히 무시합니다.
                    pass 
                    
        except Exception as e:
            print(f"[디버그] 메인 화면 복구 전체 실패: {e}")

        # 3. 스캐너 프로그램 완전히 종료
        self.destroy()


# 프로그램 진입점
if __name__ == "__main__":
    ctk.set_appearance_mode("dark") # 다크 모드 적용
    app = App()
    app.mainloop()
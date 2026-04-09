import customtkinter as ctk
import threading
import pyautogui
import pyperclip
from pynput import keyboard
import time
import sys
import requests  # 서버와 HTTP 통신을 담당하는 핵심 라이브러리
from tkinter import messagebox
import textwrap  # 긴 문장을 버튼 크기에 맞춰 줄바꿈해주는 도구

# 터미널 출력 시 한글 깨짐 방지 설정
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# ⭐ [1] 전역 설정 (서버 접속 정보)
# ==========================================
# 백엔드 서버의 기본 주소입니다. 팀 환경에 따라 IP가 변경될 수 있습니다.
BASE_URL = "http://192.168.0.77:8000"
API_REGISTER_URL = f"{BASE_URL}/register"  # 회원가입 API 엔드포인트
API_LOGIN_URL = f"{BASE_URL}/login"        # 로그인 API 엔드포인트
API_ANALYZE_URL = f"{BASE_URL}/analyze"      # AI 문장 분석 API 엔드포인트

ctk.set_appearance_mode("Dark") # 다크 모드 테마 적용
ctk.set_default_color_theme("blue")

# ==========================================
# ⭐ [2] 메인 애플리케이션 클래스
# ==========================================
class FinalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ToneGuard AI 스캐너")
        self.geometry("400x550") 
        self.attributes('-topmost', True) # 항상 다른 창 위에 표시
        self.protocol("WM_DELETE_WINDOW", self.on_logout_and_exit) # 종료 시 호출

        # 프로그램 상태 제어 변수들
        self.is_scanning = False    # 키보드 스캔 시작/중지 상태
        self.filter_on = False      # AI 필터 활성화 여부
        self.is_popup_open = False  # 팝업창 중복 생성 방지 락(Lock)
        self.is_pasting = False     # 프로그램이 자동 붙여넣기 중인지 체크 (무한루프 방지)
        self.typing_timer = None    # 사용자가 타자를 멈췄는지 감지하는 타이머
        self.listener = None        # 키보드 입력 이벤트 감지기
        self.current_user_id = None # 로그인 성공 시 서버에서 받은 사용자 식별자
        self.fixed_popup_x = None  # 💡 [추가] 팝업창의 처음 X 좌표를 기억합니다.
        self.fixed_popup_y = None  # 💡 [추가] 팝업창의 처음 Y 좌표를 기억합니다.

        # 화면 전환을 위한 각 프레임 객체 생성
        self.login_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.register_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")

        # UI 요소 배치 (로그인, 회원가입, 메인 화면)
        self.setup_login_ui()
        self.setup_register_ui()
        self.setup_main_ui()
        
        # 첫 화면으로 로그인 프레임 표시
        self.login_frame.pack(expand=True, fill="both")

    def on_logout_and_exit(self):
        """프로그램 종료 시 키보드 리스너를 안전하게 중지합니다."""
        if messagebox.askokcancel("종료", "프로그램을 종료하시겠습니까?"):
            if self.listener: self.listener.stop()
            self.destroy()

    # ------------------------------------------
    # 🎨 [3] UI 구성 함수 (프레임별 요소 배치)
    # ------------------------------------------
    def setup_login_ui(self):
        """로그인 카드 UI 구성"""
        card = ctk.CTkFrame(self.login_frame, corner_radius=30, fg_color="#2b2b2b", border_width=2, border_color="#3d3d3d")
        card.pack(pady=40, padx=30, fill="both", expand=True)
        ctk.CTkLabel(card, text="ToneGuard", font=("Inter", 28, "bold"), text_color="#3b82f6").pack(pady=(40, 5))
        self.entry_email = ctk.CTkEntry(card, placeholder_text="Email", width=220, height=45, corner_radius=15, fg_color="#1e1e1e")
        self.entry_email.pack(pady=10)
        self.entry_pwd = ctk.CTkEntry(card, placeholder_text="Password", show="*", width=220, height=45, corner_radius=15, fg_color="#1e1e1e")
        self.entry_pwd.pack(pady=10)
        ctk.CTkButton(card, text="Sign In", command=self.check_login_flow, width=220, height=45, corner_radius=20, font=("Inter", 14, "bold"), fg_color="#3b82f6").pack(pady=25)

    def setup_register_ui(self):
        """회원가입 카드 UI 구성"""
        reg_card = ctk.CTkFrame(self.register_frame, corner_radius=30, fg_color="#2b2b2b", border_width=2, border_color="#3d3d3d")
        reg_card.pack(pady=30, padx=30, fill="both", expand=True)
        form_frame = ctk.CTkFrame(reg_card, fg_color="transparent")
        form_frame.pack(padx=20)
        self.reg_email = self.create_reg_input(form_frame, "이 메 일 :", "user@email.com", 0)
        self.reg_pwd = self.create_reg_input(form_frame, "비 밀 번 호 :", "Password", 1, show="*")
        self.reg_name = self.create_reg_input(form_frame, "이 름 :", "Name", 2)
        ctk.CTkButton(reg_card, text="Sign Up", command=self.process_register, width=240, height=45, corner_radius=22, fg_color="#10b981").pack(pady=(30, 5))
        ctk.CTkButton(reg_card, text="Back", command=self.go_to_login, fg_color="transparent").pack()

    def create_reg_input(self, master, label_text, placeholder, row_num, show=None):
        """회원가입 입력창 반복 생성을 위한 헬퍼 함수"""
        lbl = ctk.CTkLabel(master, text=label_text, font=("맑은 고딕", 13), text_color="white", anchor="w")
        lbl.grid(row=row_num, column=0, padx=(0, 15), pady=8, sticky="w")
        entry = ctk.CTkEntry(master, placeholder_text=placeholder, show=show, width=220, height=38, corner_radius=15, fg_color="#1e1e1e")
        entry.grid(row=row_num, column=1, pady=8, sticky="e")
        return entry

    def setup_main_ui(self):
        """로그인 후 나타나는 메인 대시보드 UI"""
        main_card = ctk.CTkFrame(self.main_frame, corner_radius=25, fg_color="#1e1e1e") 
        main_card.pack(pady=10, padx=10, fill="both", expand=True)
        self.switch_filter = ctk.CTkSwitch(main_card, text="AI Correction Filter", command=self.toggle_filter, progress_color="#10b981")
        self.switch_filter.pack(pady=(35, 15))
        self.btn_scan = ctk.CTkButton(main_card, text="START SCANNER", command=self.toggle_scan, width=190, height=48, fg_color="#52D3D8", text_color="black")
        self.btn_scan.pack(pady=10)
        self.lbl_filter_desc = ctk.CTkLabel(main_card, text="OFF: Manual Mode", text_color="#555555")
        self.lbl_filter_desc.pack()

    def go_to_login(self):
        self.register_frame.pack_forget()
        self.login_frame.pack(expand=True, fill="both")

    def toggle_scan(self):
        self.is_scanning = not self.is_scanning
        self.btn_scan.configure(text="중지" if self.is_scanning else "시작", fg_color="red" if self.is_scanning else "#52D3D8")

    def toggle_filter(self):
        self.filter_on = self.switch_filter.get() 

    # ==========================================
    # 🔄 [4] 서버 통신 로직 (API 기반 연동)
    # ==========================================
    def process_register(self):
        """
        사용자 정보를 JSON 형태로 묶어 서버의 /register API로 보냅니다.
        """
        payload = {
            "email": self.reg_email.get().strip(),
            "password": self.reg_pwd.get().strip(),
            "name": self.reg_name.get().strip()
        }
        
        try:
            response = requests.post(API_REGISTER_URL, json=payload, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("성공", "회원가입이 완료되었습니다!")
                self.go_to_login()
            else:
                # 서버에서 보낸 에러 메시지를 사용자에게 알림
                messagebox.showerror("실패", response.json().get("detail", "가입 오류"))
        except Exception as e:
            messagebox.showerror("에러", f"서버 연결 실패: {e}")

    def check_login_flow(self):
        """
        입력한 이메일/비밀번호를 서버의 /login API로 보내 인증을 요청합니다.
        """
        payload = {
            "email": self.entry_email.get().strip(),
            "password": self.entry_pwd.get().strip()
        }

        # 테스트용 관리자 계정 (개발 편의를 위해 유지)
        if payload["email"] == "admin" and payload["password"] == "1234":
            self.start_main_app()
            return

        try:
            response = requests.post(API_LOGIN_URL, json=payload, timeout=5)
            if response.status_code == 200:
                result = response.json()
                self.current_user_id = result.get("user_id") # 로그인 성공 시 사용자 고유 ID 저장
                self.start_main_app()
            else:
                messagebox.showerror("실패", "이메일 또는 비밀번호가 틀렸습니다.")
        except Exception as e:
            messagebox.showerror("에러", f"서버 연결 실패: {e}")

    def start_main_app(self):
        """인증 성공 후 키보드 리스너를 실행하고 메인 화면으로 전환합니다."""
        self.login_frame.pack_forget()
        self.main_frame.pack(expand=True, fill="both")
        self.geometry("320x240")
        if self.listener: self.listener.stop()
        # 사용자의 키 입력을 실시간으로 모니터링하는 스레드 시작
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    # ==========================================
    # 🧠 [5] AI 자동 교정 로직 (스캐너 기능)
    # ==========================================
    def on_press(self, key):
        """
        키를 누를 때마다 호출됩니다. 
        타자를 멈추면 2.5초 후 텍스트를 캡처하는 타이머를 작동시킵니다.
        """
        # 프로그램이 자동 붙여넣기(is_pasting) 중일 때는 자기 자신의 입력을 무시합니다.
        if not self.is_scanning or self.is_popup_open or self.is_pasting: return
        
        if self.typing_timer: self.typing_timer.cancel() # 이전 타이머가 있으면 취소
        # 2.5초간 입력이 없으면 capture_text 함수 실행 예약
        self.typing_timer = threading.Timer(2.5, self.capture_text)
        self.typing_timer.start()

    def capture_text(self):
        """전체 선택(Ctrl+A)과 복사(Ctrl+C)를 통해 현재 창의 텍스트를 가져옵니다."""
        if not self.filter_on or self.is_popup_open: return
        self.is_popup_open = True
        
        pyautogui.hotkey('ctrl', 'a') # 전체 선택
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'c') # 클립보드에 복사
        time.sleep(0.1)
        
        text = pyperclip.paste() # 복사된 텍스트 읽기
        if text.strip():
            # 💡 서버 분석은 시간이 걸리므로 별도 스레드(Thread)에서 실행하여 UI 멈춤 방지
            threading.Thread(target=self.analyze_text_from_server, args=(text,), daemon=True).start()
        else: self.is_popup_open = False

    def analyze_text_from_server(self, text):
        """서버의 /analyze API로 텍스트를 보내 AI 교정본을 받아옵니다."""
        try:
            payload = {"text": text.strip()}
            response = requests.post(API_ANALYZE_URL, json=payload, timeout=20)
            if response.status_code == 200:
                result = response.json()
                # 💡 UI 업데이트는 반드시 메인 스레드에서 수행해야 하므로 after() 사용
                self.after(0, lambda: self.show_popup(text, result.get("corrections"), result.get("context_type")))
            else: self.is_popup_open = False
        except: self.is_popup_open = False

    def show_popup(self, original_text, corrections, context_type):
        """교정된 말투 3가지를 보여주는 팝업창을 생성합니다."""
        popup = ctk.CTkToplevel(self)
        popup.title(f"✨ 감지 상황: {context_type}")
        popup.attributes('-topmost', True)
        
        popup_width, popup_height = 400, 280

        # 💡 [핵심 로직] 처음 위치를 기억하거나, 기억된 위치를 사용합니다.
        if self.fixed_popup_x is None or self.fixed_popup_y is None:
            # 1. 처음 실행 시: 마우스 위치를 기준으로 좌표를 계산하고 저장합니다.
            mx, my = pyautogui.position()
            self.fixed_popup_x = mx - 200
            self.fixed_popup_y = my - 170 - popup_height
            
            # 화면 밖으로 나가지 않게 최소값 방어
            if self.fixed_popup_y < 0: self.fixed_popup_y = 10
            print(f"📌 처음 위치 고정 완료: {self.fixed_popup_x}, {self.fixed_popup_y}")
        
        # 2. 고정된 좌표를 사용하여 창을 띄웁니다.
        popup.geometry(f"{popup_width}x{popup_height}+{self.fixed_popup_x}+{self.fixed_popup_y}")

        def on_close():
            self.is_popup_open = False
            popup.destroy()

        ctk.CTkLabel(popup, text="적용할 말투 선택:", font=("맑은 고딕", 12, "bold")).pack(pady=10)

        def click(corrected_text):
            """사용자가 선택한 말투를 원본 텍스트 위치에 덮어씁니다."""
            pyperclip.copy(corrected_text or original_text)
            self.is_pasting = True # 방어막 가동 (무한루프 방지)
            on_close()
            
            def delayed_paste():
                time.sleep(0.3) # 팝업이 닫히고 원래 창에 포커스가 갈 때까지 대기
                pyautogui.hotkey('ctrl', 'v') # 자동 붙여넣기
                time.sleep(0.5) 
                self.is_pasting = False # 방어막 해제
            threading.Thread(target=delayed_paste, daemon=True).start()

        # 서버에서 받은 3가지 톤 매핑
        tone_mapping = {"정중하게": corrections.get("polite"), "친근하게": corrections.get("friendly"), "단호하게": corrections.get("firm")}
        
        for tone, txt in tone_mapping.items():
            # 💡 버튼 너비에 맞춰 문장을 줄바꿈하여 가독성 확보
            wrapped = textwrap.fill(f"[{tone}] {txt}", width=28)
            ctk.CTkButton(popup, text=wrapped, width=360, height=60, command=lambda t=txt: click(t)).pack(pady=4)

# ==========================================
# 🚀 프로그램 시작점
# ==========================================
if __name__ == "__main__":
    app = FinalApp()
    app.mainloop()
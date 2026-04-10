import customtkinter as ctk        # 현대적인 GUI 제작을 위한 라이브러리
import threading, sys, os, ctypes
from PIL import Image
from pynput import keyboard
from tkinter import messagebox

# 분할 파일 임포트
import login, scan_corr

# DPI 배율 인식
try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception: pass

# 터미널 한글 깨짐 방지
if sys.stdout is not None: sys.stdout.reconfigure(encoding='utf-8')

ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("blue")

class FinalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ToneGuard AI 스캐너")
        
        # 화면 크기 계산
        self.sw, self.sh = self.winfo_screenwidth(), self.winfo_screenheight()
        lw, lh = int(self.sw * 0.66), int(self.sh * 0.66)
        self.large_geometry = f"{lw}x{lh}+{(self.sw-lw)//2}+{(self.sh-lh)//2}" 
        self.small_geometry = f"420x600+{(self.sw-420)//2}+{(self.sh-600)//2}" 
        self.scanner_w, self.scanner_h = 280, 170
        
        self.geometry(self.large_geometry)
        self.protocol("WM_DELETE_WINDOW", self.on_logout_and_exit)

        # 상태 변수
        self.is_scanning = self.filter_on = self.is_popup_open = self.is_pasting = False
        self.typing_timer = self.listener = self.current_user_id = self.token = None
        self.fixed_popup_x = self.fixed_popup_y = None  

        # 프레임 바구니
        self.landing_frame = ctk.CTkFrame(self, fg_color="transparent") 
        self.login_frame = ctk.CTkFrame(self, fg_color="transparent")   
        self.register_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.scanner_frame = ctk.CTkFrame(self, fg_color="transparent") 

        # UI 초기화 호출 (연결)
        self.setup_landing_ui()  
        login.setup_auth_ui(self)
        scan_corr.setup_scanner_ui(self)
        
        self.landing_frame.pack(expand=True, fill="both")

    def on_logout_and_exit(self):
        if messagebox.askokcancel("종료", "프로그램을 종료하시겠습니까?"):
            if self.listener: self.listener.stop()
            self.destroy()

    def setup_landing_ui(self):
        """유라님 원본 랜딩 페이지 디자인 (exe 경로 마법 적용)"""
        header = ctk.CTkFrame(self.landing_frame, fg_color="transparent", height=80)
        header.pack(fill="x", padx=40, pady=20)
        
        # ⭐ [.exe 마법] 실행 파일 내부의 임시 폴더에서 로고를 찾는 로직입니다.
        try:
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS  # exe 실행 시 경로
            else:
                base_path = os.path.abspath(".") # 개발 중 경로
                
            logo_path = os.path.join(base_path, "logo.png")
            self.logo_img = ctk.CTkImage(Image.open(logo_path), size=(150, 100))
            ctk.CTkLabel(header, image=self.logo_img, text="").pack(side="left")
        except:
            ctk.CTkLabel(header, text="🟦 ToneGuard", font=("Inter", 24, "bold"), text_color="#3b82f6").pack(side="left")

        self.h_btn_f = ctk.CTkFrame(header, fg_color="transparent"); self.h_btn_f.pack(side="right")
        self.btn_go_login = ctk.CTkButton(self.h_btn_f, text="로그인", font=("맑은 고딕", 14, "bold"), width=100, height=40, corner_radius=8, command=self.go_to_login_screen)
        self.btn_go_login.pack(side="right", padx=5)
        self.btn_mypage = ctk.CTkButton(self.h_btn_f, text="마이페이지", font=("맑은 고딕", 14), width=100, height=40, corner_radius=8, fg_color="#11acb7", border_width=1); self.btn_logout = ctk.CTkButton(self.h_btn_f, text="로그아웃", font=("맑은 고딕", 14), width=90, height=40, corner_radius=8, fg_color="#720a0a", command=self.process_logout)

        hero = ctk.CTkFrame(self.landing_frame, fg_color="transparent"); hero.pack(expand=True, fill="both", pady=(50, 0))
        ctk.CTkLabel(hero, text="TONE GUARD · AI 말투 교정", font=("맑은 고딕", 12, "bold"), text_color="#3b82f6").pack(pady=10)
        ctk.CTkLabel(hero, text="무심코 보낸 한 줄이\n관계를 바꿉니다", font=("맑은 고딕", 42, "bold"), text_color="white", justify="center").pack(pady=15)
        ctk.CTkLabel(hero, text="보내기 전, 말투를 한 번 더.\n톤가드가 당신의 메시지를 다듬어 드립니다.", font=("맑은 고딕", 16), text_color="#a1a1aa", justify="center").pack(pady=20)
        ctk.CTkButton(hero, text="Scan(스캔)", font=("맑은 고딕", 16, "bold"), width=200, height=55, corner_radius=8, command=self.open_scanner_window).pack(pady=20)

        feat = ctk.CTkFrame(self.landing_frame, fg_color="transparent"); feat.pack(fill="x", padx=80, pady=(0, 60))
        feat.grid_columnconfigure((0, 1, 2), weight=1)
        def create_card(col, dot, title, desc):
            c = ctk.CTkFrame(feat, fg_color="#2b2b2b", corner_radius=15, border_width=1, border_color="#3d3d3d", height=120); c.grid(row=0, column=col, padx=15, sticky="ew"); c.grid_propagate(False)
            ctk.CTkLabel(c, text="●", font=("Arial", 16), text_color=dot).pack(anchor="w", padx=20, pady=(20, 5)); ctk.CTkLabel(c, text=title, font=("맑은 고딕", 16, "bold")).pack(anchor="w", padx=20); ctk.CTkLabel(c, text=desc, font=("맑은 고딕", 13), text_color="#a1a1aa").pack(anchor="w", padx=20, pady=(5, 20))
        create_card(0, "#3b82f6", "실시간 감지", "슬랙·디스코드 메시지를 즉시 분석"); create_card(1, "#10b981", "톤 분석", "공격성·직접성·감정 수치 제공"); create_card(2, "#f59e0b", "대안 제시", "상황에 맞는 교정 문장 3가지 추천")

    # 제어 로직
    def go_to_login_screen(self): self.landing_frame.pack_forget(); self.geometry(self.small_geometry); self.login_frame.pack(expand=True, fill="both")
    def cancel_login(self): self.login_frame.pack_forget(); self.geometry(self.large_geometry); self.landing_frame.pack(expand=True, fill="both")
    def start_main_app(self): self.login_frame.pack_forget(); self.geometry(self.large_geometry); self.landing_frame.pack(expand=True, fill="both"); self.btn_go_login.pack_forget(); self.btn_logout.pack(side="right", padx=5); self.btn_mypage.pack(side="right", padx=5)
    def process_logout(self): self.token = None; (self.listener.stop() if self.listener else None); self.btn_mypage.pack_forget(); self.btn_logout.pack_forget(); self.btn_go_login.pack(side="right", padx=5)
    def open_scanner_window(self):
        if not self.token: messagebox.showwarning("안내", "로그인이 필요합니다."); self.go_to_login_screen(); return
        self.landing_frame.pack_forget(); self.geometry(f"{self.scanner_w}x{self.scanner_h}"); self.after(200, self.move_to_top_right); self.attributes('-topmost', True); self.scanner_frame.pack(expand=True, fill="both")
        (self.listener.stop() if self.listener else None); self.listener = keyboard.Listener(on_press=self.on_press); self.listener.start()
    def move_to_top_right(self): self.geometry(f"+{self.sw - self.scanner_w - 20}+20")
    def close_scanner_window(self):
        if self.is_scanning: scan_corr.toggle_scan(self)
        self.attributes('-topmost', False); self.scanner_frame.pack_forget(); self.geometry(self.large_geometry); self.landing_frame.pack(expand=True, fill="both")
    def on_press(self, key):
        if not self.is_scanning or self.is_popup_open or self.is_pasting: return
        if self.typing_timer: self.typing_timer.cancel()
        self.typing_timer = threading.Timer(1.5, lambda: scan_corr.capture_text(self)); self.typing_timer.start()

if __name__ == "__main__":
    app = FinalApp(); app.mainloop()
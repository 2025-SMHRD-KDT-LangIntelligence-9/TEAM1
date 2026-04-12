import customtkinter as ctk  # 세련된 파스텔/다크 테마 UI를 만들기 위한 라이브러리
# 아래 라이브러리들은 향후 실제 스캔 로직(캡처, 통신)이 들어올 때 사용됩니다.
import threading, pyautogui, pyperclip, time, requests, textwrap
import pygetwindow as gw  # 실행 중인 윈도우 창들을 찾아내고 제어하기 위한 라이브러리
import ctypes  # 윈도우 OS의 깊은 시스템 설정에 접근하기 위한 라이브러리

# [윈도우 화면 배율(DPI) 패치]
# 노트북 등 고해상도 모니터에서 윈도우 화면 배율이 125%, 150%로 설정되어 있을 때,
# 창이 엉뚱한 곳에 뜨거나 흐려지는 것을 방지하고 1:1 픽셀로 정확히 매칭시킵니다.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# [스캐너 메인 클래스]
class ScannerApp(ctk.CTk):
    def __init__(self):
        # ctk.CTk(부모 클래스)의 초기화 메서드를 실행하여 창을 생성합니다.
        super().__init__()
        self.title("ToneGuard Scanner")  # 창의 제목 표시줄 설정
        
        # --- 1. 초기 창 설정 ---
        self.scanner_w, self.scanner_h = 230, 150  # 스캐너 창의 가로, 세로 크기 지정
        self.geometry(f"{self.scanner_w}x{self.scanner_h}")  # 창 크기 적용
        self.attributes('-topmost', True)  # 다른 모든 창들보다 항상 맨 위에 떠 있게 설정
        self.resizable(False, False)       # 마우스로 창 크기를 임의로 조절하지 못하게 고정
        
        # --- 상태를 기억하는 변수들 ---
        self.is_scanning = False   # 현재 스캔이 돌아가고 있는지 (True/False)
        self.filter_on = False     # 필터 스위치가 켜져 있는지 (True/False)
        self.is_popup_open = False # 교정 결과 팝업이 떠 있는지 (True/False)
        self.token = "test_token"  # 향후 웹에서 넘겨받을 사용자 인증 토큰 (임시)

        # --- 2. UI 그리기 ---
        self.setup_ui()  # 아래에 정의된 UI 생성 함수를 호출하여 화면을 그립니다.
        
        # --- 3. 창 위치 조정 ---
        # 창이 OS 메모리에 완전히 생성될 시간을 주기 위해 0.2초(200ms) 뒤에 이동 함수를 실행합니다.
        self.after(200, self.move_to_top_right)

    def move_to_top_right(self):
        """창을 모니터 우측 상단으로 이동시키는 함수"""
        sw = self.winfo_screenwidth()  # 현재 사용 중인 모니터의 전체 가로 픽셀 길이
        x = sw - self.scanner_w - 20   # 전체 길이에서 창 너비와 여백(20)을 빼서 X 좌표 계산
        y = 50                         # 위에서부터 50픽셀 떨어진 Y 좌표
        self.geometry(f"+{x}+{y}")     # 계산된 X, Y 좌표로 창을 순간이동 시킵니다.

    def close_and_restore_main(self):
        """메인창(웹 브라우저)을 다시 띄우고 스캐너는 종료하는 함수"""
        try:
            # pygetwindow를 이용해 제목에 "ToneGuard AI Scanner"가 포함된 창을 모두 찾습니다.
            target_title = "ToneGuard AI Scanner"
            windows = gw.getWindowsWithTitle(target_title)
            
            # 찾은 창이 하나라도 있다면
            if windows:
                browser_win = windows[0]       # 첫 번째 창을 선택
                browser_win.restore()          # 작업 표시줄에 숨겨진 창을 원래 크기로 복구
                browser_win.activate()         # 창을 클릭한 것처럼 맨 앞으로 포커싱
        except Exception as e:
            print(f"창 복구 오류: {e}")        # 에러 발생 시 콘솔에 출력 (사용자에겐 안 보임)
        finally:
            self.destroy()                     # 브라우저 복구 성공 여부와 상관없이 스캐너 창 자신을 종료

    def setup_ui(self):
        """스캐너의 버튼, 스위치 등 모든 UI 요소를 배치하는 함수"""
        
        # [1] 메인 카드 프레임: 전체를 감싸는 둥근 테두리의 배경 상자
        main_card = ctk.CTkFrame(self, corner_radius=20, fg_color="#1e1e1e", border_width=1, border_color="#3d3d3d")
        main_card.pack(pady=10, padx=10, fill="both", expand=True)

        # --- [2] 상단 컨트롤 라인 영역 (스위치 | 메인버튼 | 슬라이더) ---
        # 배경이 투명한 프레임을 만들어 내부 요소들을 가로로 배치할 준비를 합니다.
        top = ctk.CTkFrame(main_card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=15) 

        # ⭐ [레이아웃 핵심] 3개의 열(Column)을 1:1:1 비율로 똑같이 나눕니다.
        # 이렇게 하면 각 요소가 차지하는 공간이 균등해져서 배치가 불규칙해지지 않습니다.
        top.columnconfigure(0, weight=1) # 0번 칸: 왼쪽 스위치용
        top.columnconfigure(1, weight=1) # 1번 칸: 가운데 메인 버튼용
        top.columnconfigure(2, weight=1) # 2번 칸: 오른쪽 슬라이더용

        # 1. 자동 감지 필터 스위치 (왼쪽 끝 정렬)
        self.switch_filter = ctk.CTkSwitch(top, text="ON", font=("맑은 고딕", 12, "bold"), 
                                           command=self.toggle_filter, progress_color="#10b981", width=40)
        # sticky="w"는 West(서쪽), 즉 칸의 왼쪽 벽에 딱 붙으라는 의미입니다.
        self.switch_filter.grid(row=0, column=0, sticky="w")

        # 2. 메인 복귀 버튼 (정중앙 정렬)
        # grid의 1번 칸에 배치하면 별도 설정 없이도 해당 칸의 정가운데에 놓입니다.
        self.btn_main = ctk.CTkButton(top, text="메인", font=("맑은 고딕", 11), fg_color="#3d3d3d", 
                                      width=55, height=24, command=self.close_and_restore_main)
        self.btn_main.grid(row=0, column=1)

        # 3. 투명도 조절 슬라이더 (오른쪽 끝 정렬)
        self.slider_alpha = ctk.CTkSlider(top, from_=0.3, to=1.0, width=100, 
                                          command=lambda v: self.attributes('-alpha', v))
        self.slider_alpha.set(1.0) 
        # sticky="e"는 East(동쪽), 즉 칸의 오른쪽 벽에 딱 붙으라는 의미입니다.
        self.slider_alpha.grid(row=0, column=2, sticky="e")


        # --- [3] 중앙 거대 스캔 시작/중지 버튼 ---
        # 상단 영역과 별개로 메인 카드의 수직 흐름에 따라 배치합니다.
        self.btn_scan = ctk.CTkButton(main_card, text="스캔 시작", command=self.toggle_scan, 
                                      font=("맑은 고딕", 16, "bold"), width=170, height=35, 
                                      corner_radius=30, fg_color="#52D3D8", text_color="black")
        self.btn_scan.pack(expand=True) # expand=True를 통해 위아래 남는 공간의 정중앙에 위치시킵니다.
        
        # --- [4] 하단 현재 상태 알림 텍스트 ---
        self.lbl_status = ctk.CTkLabel(main_card, text="OFF: Manual Mode", font=("맑은 고딕", 12), text_color="#a1a1aa")
        self.lbl_status.pack(side="bottom", pady=10) # 카드 프레임의 맨 아래에 배치

    def toggle_scan(self):
        """스캔 시작/중지 버튼을 눌렀을 때 상태와 디자인을 바꾸는 함수"""
        self.is_scanning = not self.is_scanning # True/False 상태를 반대로 뒤집음
        
        if self.is_scanning:
            # 스캔 시작 시: 버튼을 빨간색 '중지'로 변경하고 상태 텍스트 업데이트
            self.btn_scan.configure(text="중지", fg_color="#ef4444", text_color="white")
            self.lbl_status.configure(text="ON: Monitoring...", text_color="#10b981")
            self.filter_on = True        # 필터 켜기
            self.switch_filter.select()  # 스위치 UI도 켜진 상태로 변경
        else:
            # 스캔 중지 시: 원래의 민트색 '스캔 시작' 버튼으로 원상 복구
            self.btn_scan.configure(text="스캔 시작", fg_color="#52D3D8", text_color="black")
            self.lbl_status.configure(text="OFF: Manual Mode", text_color="#a1a1aa")
            self.filter_on = False       # 필터 끄기
            self.switch_filter.deselect()# 스위치 UI도 꺼진 상태로 변경

    def toggle_filter(self):
        """스위치를 직접 클릭했을 때 필터 상태(True/False)를 업데이트하는 함수"""
        self.filter_on = self.switch_filter.get()

# [프로그램 실행 진입점]
# 이 파이썬 파일이 직접 실행될 때만 아래 코드가 작동합니다.
if __name__ == "__main__":
    app = ScannerApp() # 클래스를 기반으로 앱 객체 생성
    app.mainloop()     # 프로그램이 종료되지 않고 계속 화면에 떠 있도록 루프 실행
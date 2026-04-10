import customtkinter as ctk
import requests
from tkinter import messagebox

# 서버 주소 설정
BASE_URL = "http://192.168.0.77:8000"
API_REGISTER_URL = f"{BASE_URL}/register"
API_LOGIN_URL = f"{BASE_URL}/login"

def setup_auth_ui(app):
    """로그인 및 회원가입 UI 통합 설정"""
    setup_login_ui(app)
    setup_register_ui(app)

def setup_login_ui(app):
    """로그인 카드 UI 구성"""
    card = ctk.CTkFrame(app.login_frame, corner_radius=30, fg_color="#2b2b2b", border_width=2, border_color="#3d3d3d")
    card.pack(pady=40, padx=30, fill="both", expand=True)
    
    ctk.CTkLabel(card, text="ToneGuard", font=("Inter", 28, "bold"), text_color="#3b82f6").pack(pady=(40, 5))
    
    app.entry_email = ctk.CTkEntry(card, placeholder_text="Email", width=220, height=45, corner_radius=15)
    app.entry_email.pack(pady=10)
    app.entry_pwd = ctk.CTkEntry(card, placeholder_text="Password", show="*", width=220, height=45, corner_radius=15)
    app.entry_pwd.pack(pady=10)
    
    ctk.CTkButton(card, text="Sign In", command=lambda: check_login_flow(app), width=220, height=45, corner_radius=20, fg_color="#3b82f6").pack(pady=25)
    ctk.CTkButton(card, text="회원가입 하기", command=lambda: [app.login_frame.pack_forget(), app.register_frame.pack(expand=True, fill="both")], fg_color="transparent", text_color="#a1a1aa").pack()
    ctk.CTkButton(card, text="메인으로 돌아가기", command=app.cancel_login, fg_color="transparent", text_color="#ef4444").pack()

def setup_register_ui(app):
    """회원가입 양식 UI 구성"""
    reg_card = ctk.CTkFrame(app.register_frame, corner_radius=30, fg_color="#2b2b2b", border_width=2, border_color="#3d3d3d")
    reg_card.pack(pady=30, padx=30, fill="both", expand=True)
    f = ctk.CTkFrame(reg_card, fg_color="transparent")
    f.pack(padx=20)
    
    def create_input(lbl, ph, r, s=None):
        ctk.CTkLabel(f, text=lbl, font=("맑은 고딕", 13), text_color="white", anchor="w").grid(row=r, column=0, padx=(0, 15), pady=8, sticky="w")
        e = ctk.CTkEntry(f, placeholder_text=ph, show=s, width=220, height=38, corner_radius=15)
        e.grid(row=r, column=1, pady=8, sticky="e")
        return e

    app.reg_email = create_input("이 메 일 :", "user@email.com", 0)
    app.reg_pwd = create_input("비 밀 번 호 :", "Password", 1, "*")
    app.reg_name = create_input("이 름 :", "Name", 2)
    app.reg_nick = create_input("닉 네 임 :", "Nickname", 3)
    app.reg_dept = create_input("부 서 :", "Department", 4)
    app.reg_job = create_input("직 책 :", "Job Title", 5)

    ctk.CTkButton(reg_card, text="Sign Up", command=lambda: process_register(app), width=240, height=45, corner_radius=22, fg_color="#10b981").pack(pady=(20, 5))
    ctk.CTkButton(reg_card, text="Back", command=lambda: [app.register_frame.pack_forget(), app.login_frame.pack(expand=True, fill="both")], fg_color="transparent").pack()

def check_login_flow(app):
    p = {"email": app.entry_email.get().strip(), "password": app.entry_pwd.get().strip()}
    try:
        r = requests.post(API_LOGIN_URL, json=p, timeout=10)
        if r.status_code == 200:
            res = r.json()
            app.token, app.current_user_id = res.get("access_token"), res.get("user_id")
            app.start_main_app()
        else: messagebox.showerror("실패", "로그인 실패")
    except: messagebox.showerror("에러", "서버 연결 실패")

def process_register(app):
    p = {"email": app.reg_email.get().strip(), "password": app.reg_pwd.get().strip(), "name": app.reg_name.get().strip(),
         "nick": app.reg_nick.get().strip(), "dept": app.reg_dept.get().strip(), "job": app.reg_job.get().strip()}
    try:
        if requests.post(API_REGISTER_URL, json=p, timeout=10).status_code == 200:
            messagebox.showinfo("성공", "가입 완료!"); app.go_to_login_screen()
        else: messagebox.showerror("실패", "가입 오류")
    except: messagebox.showerror("에러", "서버 연결 실패")
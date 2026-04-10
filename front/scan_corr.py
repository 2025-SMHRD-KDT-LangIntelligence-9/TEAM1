import customtkinter as ctk
import threading, pyautogui, pyperclip, time, requests, textwrap

API_ANALYZE_URL = "http://192.168.0.77:8000/analyze"
API_SAVE_URL = "http://192.168.0.77:8000/save"

def setup_scanner_ui(app):
    """우측 상단 작은 스캐너 창 UI"""
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
        app.lbl_filter_desc.configure(text="ON: Monitoring...", text_color="#10b981")
        app.switch_filter.select(); app.filter_on = True
    else:
        app.btn_scan.configure(text="스캔 시작", fg_color="#52D3D8", text_color="black")
        app.lbl_filter_desc.configure(text="OFF: Manual Mode", text_color="#a1a1aa")
        app.switch_filter.deselect(); app.filter_on = False
        app.fixed_popup_x = app.fixed_popup_y = None

def toggle_filter(app): app.filter_on = app.switch_filter.get()

def capture_text(app):
    if not app.filter_on or app.is_popup_open: return
    app.is_popup_open = True; app.fixed_popup_x = app.fixed_popup_y = None
    pyautogui.hotkey('ctrl', 'a'); time.sleep(0.1); pyautogui.hotkey('ctrl', 'c'); time.sleep(0.1)
    txt = pyperclip.paste()
    if txt.strip(): threading.Thread(target=analyze_text, args=(app, txt,), daemon=True).start()
    else: app.is_popup_open = False

def analyze_text(app, txt):
    try:
        h = {"Authorization": f"Bearer {app.token}"}
        r = requests.post(API_ANALYZE_URL, json={"text": txt.strip()}, headers=h, timeout=20)
        if r.status_code == 200:
            res = r.json()
            app.after(0, lambda: show_popup(app, txt, res.get("corrections", {}), res.get("context_type", "일반")))
        else: app.is_popup_open = False
    except: app.is_popup_open = False

def show_popup(app, original, corrs, context):
    pop = ctk.CTkToplevel(app); pop.title(f"✨ 말투 교정 ({context})"); pop.attributes('-topmost', True)
    pop_w, pop_h = 420, 360 
    if app.fixed_popup_x is None:
        mx, my = pyautogui.position()
        app.fixed_popup_x, app.fixed_popup_y = mx - 210, max(10, my - 400)
    pop.geometry(f"{pop_w}x{pop_h}+{app.fixed_popup_x}+{app.fixed_popup_y}")

    def close(): app.is_popup_open = False; pop.destroy()
    pop.protocol("WM_DELETE_WINDOW", close)

    top_frame = ctk.CTkFrame(pop, fg_color="transparent"); top_frame.pack(fill="x", padx=20, pady=(15, 10))
    ctk.CTkButton(top_frame, text="재분석", width=100, height=35, fg_color="#F59E0B", command=lambda: [close(), threading.Thread(target=analyze_text, args=(app, original,), daemon=True).start()]).pack(side="left", padx=(0, 20))
    ctk.CTkLabel(top_frame, text="적용할 말투 선택:", font=("맑은 고딕", 13, "bold"), text_color="white").pack(side="left")

    tones = {"정중하게": "polite", "친근하게": "friendly", "단호하게": "firm"}
    for name, k in tones.items():
        t = corrs.get(k, "교정 실패"); wrapped = textwrap.fill(f"[{name}] {t}", width=32)
        ctk.CTkButton(pop, text=wrapped, width=380, height=max(60, 20 + (wrapped.count('\n')+1)*22),
                      fg_color="#2563EB", hover_color="#1D4ED8", anchor="center", font=("맑은 고딕", 12),
                      command=lambda txt=t, n=name: apply_text(app, txt, n, original, context, close)).pack(pady=6)

def apply_text(app, corr, tone, orig, ctx, close_fn):
    pyperclip.copy(corr); app.is_pasting = True; close_fn()
    def p():
        time.sleep(0.3); pyautogui.hotkey('ctrl', 'v'); app.is_pasting = False
        try: requests.post(API_SAVE_URL, json={"upload_text": orig, "corr_text": corr, "tone_type": ctx, "selected_tone": tone},
                          headers={"Authorization": f"Bearer {app.token}"}, timeout=5)
        except: pass
    threading.Thread(target=p, daemon=True).start()
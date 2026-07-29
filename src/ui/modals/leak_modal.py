import customtkinter as ctk
import threading
import os
import time
from typing import Optional, Dict, Any, List

from src.core.config import get_resource_path
from src.core.leak_test import run_deep_dns_leak_test

class DeepLeakAuditModal(ctk.CTkToplevel):
    def __init__(self, parent, active_provider_name: str = "Cloudflare", doh_url: str = ""):
        super().__init__(parent)
        
        self.parent = parent
        self.active_provider_name = active_provider_name
        self.doh_url = doh_url
        
        self.title("CipherDNS - Privacy & DNS Leak Audit")
        self.resizable(False, False)
        self.configure(fg_color="#0D0D0D")
        
        # Center relative to parent
        self.update_idletasks()
        if parent:
            p_x = parent.winfo_x()
            p_y = parent.winfo_y()
            p_w = parent.winfo_width()
            p_h = parent.winfo_height()
            c_x = max(0, p_x + (p_w - 700) // 2)
            c_y = max(0, p_y + (p_h - 530) // 2)
            self.geometry(f"700x530+{c_x}+{c_y}")
        else:
            self.geometry("700x530")
        
        # Window Icon
        assets_dir = get_resource_path("assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            self.after(200, lambda: self.iconbitmap(app_icon_path))
            
        self.transient(parent)
        self.grab_set()
        
        self.build_ui()

    def build_ui(self):
        # 1. Top Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=8)
        header_frame.pack(fill="x", padx=16, pady=(16, 8))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🔍 Deep Privacy & DNS Leak Audit", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(anchor="w", padx=16, pady=(12, 2))
        
        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="5-Vector Multi-Round Resolver Matrix & TLS 1.3 DoH Security Inspector", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#888888"
        )
        subtitle_label.pack(anchor="w", padx=16, pady=(0, 12))

        # 2. Main Content Frame
        self.content_frame = ctk.CTkFrame(self, fg_color="#121212", corner_radius=8)
        self.content_frame.pack(fill="both", expand=True, padx=16, pady=8)

        # 2A. INTRO VIEW (Initially Visible)
        self.intro_box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.intro_box.pack(fill="both", expand=True, padx=16, pady=16)

        intro_heading = ctk.CTkLabel(
            self.intro_box,
            text="Audit Vector Overview",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        intro_heading.pack(anchor="w", pady=(0, 8))

        info_card = ctk.CTkFrame(self.intro_box, fg_color="#1A1A1A", corner_radius=6)
        info_card.pack(fill="x", pady=(0, 16))

        vectors_text = (
            "• Vector 1: Multi-Round 36-Sample Resolver Leak Matrix (IPv4/IPv6)\n"
            "• Vector 2: DoH TLS 1.3 Connection & SSL Certificate Verification\n"
            "• Vector 3: DNSSEC Signature Enforcement Check (dnssec-failed.org)\n"
            "• Vector 4: Ad & Tracker Shield Verification\n"
            "• Vector 5: Transparent ISP DNS Proxy Interception Check"
        )
        info_lbl = ctk.CTkLabel(
            info_card,
            text=vectors_text,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#CCCCCC",
            justify="left"
        )
        info_lbl.pack(anchor="w", padx=16, pady=14)

        # Start Audit Button
        btn_box = ctk.CTkFrame(self.intro_box, fg_color="transparent")
        btn_box.pack(pady=10)

        self.start_btn = ctk.CTkButton(
            btn_box,
            text="🚀 Start Leak Audit",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#D9534F",
            hover_color="#C9302C",
            height=42,
            width=190,
            corner_radius=6,
            command=self._on_start_click
        )
        self.start_btn.pack()

        # 2B. LIVE RUNNING CONSOLE VIEW (Initially Hidden)
        self.run_box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        
        self.progress_bar = ctk.CTkProgressBar(self.run_box, height=8, corner_radius=4)
        self.progress_bar.set(0.05)
        self.progress_bar.configure(progress_color="#D9534F")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.console_log = ctk.CTkTextbox(
            self.run_box,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#080808",
            text_color="#00FF66",
            corner_radius=6,
            wrap="word"
        )
        self.console_log.pack(fill="both", expand=True)

        # 2C. COMPLETED RESULTS VIEW (Initially Hidden)
        self.results_scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")

        # 3. Bottom Action Bar
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_bar.pack(fill="x", padx=16, pady=(0, 16))

        self.close_btn = ctk.CTkButton(
            self.bottom_bar,
            text="Close",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#262626",
            hover_color="#3A3A3A",
            height=36,
            width=100,
            command=self.destroy
        )
        self.close_btn.pack(side="right")

    def _on_start_click(self):
        # Hide Intro View
        self.intro_box.pack_forget()

        # Show Live Console View
        self.run_box.pack(fill="both", expand=True, padx=16, pady=16)

        # Execute Audit in Background Thread
        threading.Thread(target=self._execute_audit, daemon=True).start()

    def _execute_audit(self):
        def update_progress(msg: str, pct: float):
            self.after(0, lambda: self._append_log(msg, pct))

        results = run_deep_dns_leak_test(
            callback=update_progress,
            active_provider_name=self.active_provider_name,
            doh_url=self.doh_url
        )

        self.after(0, lambda: self._render_results(results))

    def _append_log(self, msg: str, pct: float):
        timestamp = time.strftime("%H:%M:%S")
        self.console_log.insert("end", f"[{timestamp}] {msg}\n")
        self.console_log.see("end")
        self.progress_bar.set(pct)

    def _render_results(self, results: Dict[str, Any]):
        timestamp = time.strftime("%H:%M:%S")
        self.console_log.insert("end", f"[{timestamp}] [DONE] Audit Completed Successfully.\n")
        self.console_log.see("end")
        self.progress_bar.set(1.0)

        # Brief pause to allow reading final log line
        self.after(600, lambda: self._switch_to_results_view(results))

    def _switch_to_results_view(self, results: Dict[str, Any]):
        # Hide Console View
        self.run_box.pack_forget()

        # Show Results View
        self.results_scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # Build Verdict Badge Card
        badge_color = results.get("badge_color", "#2ECC71")
        verdict_card = ctk.CTkFrame(self.results_scroll, fg_color=badge_color, corner_radius=6)
        verdict_card.pack(fill="x", pady=(0, 12))

        v_title = ctk.CTkLabel(
            verdict_card, 
            text=results.get("badge_title", "100% SECURE"),
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        v_title.pack(anchor="w", padx=16, pady=(10, 2))

        v_sub = ctk.CTkLabel(
            verdict_card, 
            text=results.get("badge_subtitle", ""),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#F0F0F0"
        )
        v_sub.pack(anchor="w", padx=16, pady=(0, 10))

        # 4 Mini Cards Grid
        grid_frame = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 12))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="diag")

        doh_info = results.get("doh_status", {})
        dnssec_info = results.get("dnssec_status", {})
        adblock_info = results.get("adblock_status", {})
        transparent_proxy = results.get("transparent_proxy_detected", False)

        # Card 1: DoH TLS
        c1 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=6)
        c1.grid(row=0, column=0, padx=3, sticky="ew")
        ctk.CTkLabel(c1, text="🔒 DoH TLS 1.3", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(c1, text="Verified" if doh_info.get("is_connected") else "Failed", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#2ECC71" if doh_info.get("is_connected") else "#E74C3C").pack(anchor="w", padx=8, pady=(0, 8))

        # Card 2: DNSSEC
        c2 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=6)
        c2.grid(row=0, column=1, padx=3, sticky="ew")
        ctk.CTkLabel(c2, text="🛡️ DNSSEC", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(c2, text="Enforced" if dnssec_info.get("is_active") else "Inactive", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#2ECC71" if dnssec_info.get("is_active") else "#F39C12").pack(anchor="w", padx=8, pady=(0, 8))

        # Card 3: Ad Shield
        c3 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=6)
        c3.grid(row=0, column=2, padx=3, sticky="ew")
        ctk.CTkLabel(c3, text="⛨ Ad Shield", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(c3, text=f"Active ({adblock_info.get('blocked')}/{adblock_info.get('total')})" if adblock_info.get("is_active") else "Standard", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#2ECC71" if adblock_info.get("is_active") else "#A0A0A0").pack(anchor="w", padx=8, pady=(0, 8))

        # Card 4: Transparent Proxy
        c4 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=6)
        c4.grid(row=0, column=3, padx=3, sticky="ew")
        ctk.CTkLabel(c4, text="🌐 ISP Proxy", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(c4, text="Intercepted!" if transparent_proxy else "Clean", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#E74C3C" if transparent_proxy else "#2ECC71").pack(anchor="w", padx=8, pady=(0, 8))

        # Resolvers Table Title
        table_title = ctk.CTkLabel(
            self.results_scroll,
            text="📊 Upstream Resolvers Detected (36-Sample Matrix)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        table_title.pack(anchor="w", pady=(10, 6))

        resolvers = results.get("resolvers", [])
        if not resolvers:
            no_data = ctk.CTkLabel(self.results_scroll, text="No upstream resolver anomalies detected.", text_color="#A0A0A0")
            no_data.pack(anchor="w")
        else:
            for item in resolvers:
                r_card = ctk.CTkFrame(self.results_scroll, fg_color="#181818", corner_radius=6)
                r_card.pack(fill="x", pady=3)
                
                status_color = "#E74C3C" if item.get("is_leak") else "#2ECC71"
                
                left_box = ctk.CTkFrame(r_card, fg_color="transparent")
                left_box.pack(side="left", padx=12, pady=8)
                
                ip_lbl = ctk.CTkLabel(left_box, text=f"IP: {item.get('ip')}", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#FFFFFF")
                ip_lbl.pack(anchor="w")
                
                prov_lbl = ctk.CTkLabel(left_box, text=f"{item.get('provider')} ({item.get('country')})", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#888888")
                prov_lbl.pack(anchor="w")
                
                badge = ctk.CTkLabel(
                    r_card,
                    text=item.get("status_text", ""),
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color="#FFFFFF",
                    fg_color=status_color,
                    corner_radius=4,
                    padx=10,
                    pady=3
                )
                badge.pack(side="right", padx=12, pady=8)

import customtkinter as ctk
import threading
import os
from typing import Optional, Dict, Any, List

from src.core.config import get_resource_path
from src.core.leak_test import run_deep_dns_leak_test

class DeepLeakAuditModal(ctk.CTkToplevel):
    def __init__(self, parent, active_provider_name: str = "Cloudflare", doh_url: str = ""):
        super().__init__(parent)
        
        self.parent = parent
        self.active_provider_name = active_provider_name
        self.doh_url = doh_url
        
        self.title("CipherDNS - Deep Security & Privacy Audit")
        self.geometry("940x680")
        self.resizable(False, False)
        self.configure(fg_color="#0F0F0F")
        
        # Window Icon
        assets_dir = get_resource_path("assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            self.after(200, lambda: self.iconbitmap(app_icon_path))
            
        # Center relative to parent
        self.transient(parent)
        self.grab_set()
        
        self.build_ui()

    def build_ui(self):
        # 1. Top Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="#181818", corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🔍 Deep Security & DNS Leak Audit", 
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(anchor="w", padx=20, pady=(15, 2))
        
        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="5-Vector Multi-Round Resolver Matrix, TLS 1.3 DoH Handshake & DNSSEC Enforcement Test", 
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#A0A0A0"
        )
        subtitle_label.pack(anchor="w", padx=20, pady=(0, 15))

        # 2. Welcome / Explanation Card (Initial View)
        self.intro_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=10)
        self.intro_frame.pack(fill="both", expand=True, padx=20, pady=10)

        intro_title = ctk.CTkLabel(
            self.intro_frame,
            text="What will this audit test?",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        intro_title.pack(anchor="w", padx=25, pady=(20, 10))

        features = [
            ("🔍 1. Multi-Round Resolver Matrix", "Sends 36 unique UUID subdomains across IPv4/IPv6 to verify if unencrypted ISP DNS servers are leaking queries."),
            ("🔒 2. DoH TLS 1.3 Handshake & Certs", "Audits active DoH socket connection, TLS version, cipher suite, and certificate authenticity."),
            ("🛡️ 3. DNSSEC Signature Validation", "Resolves dnssec-failed.org to test if your resolver actively blocks invalid/spoofed DNSSEC signatures."),
            ("⛨ 4. Ad & Tracker Shield Verification", "Probes network-level blocking of tracking and telemetry domains."),
            ("🌐 5. Transparent ISP Proxy Check", "Tests if your ISP intercepts unencrypted UDP 53 packets in the background.")
        ]

        for title, desc in features:
            f_box = ctk.CTkFrame(self.intro_frame, fg_color="#1C1C1C", corner_radius=8)
            f_box.pack(fill="x", padx=25, pady=4)
            
            t_lbl = ctk.CTkLabel(f_box, text=title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#D9534F")
            t_lbl.pack(anchor="w", padx=15, pady=(6, 0))
            
            d_lbl = ctk.CTkLabel(f_box, text=desc, font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#B0B0B0", justify="left")
            d_lbl.pack(anchor="w", padx=15, pady=(0, 6))

        # Centered Start Audit Button
        start_box = ctk.CTkFrame(self.intro_frame, fg_color="transparent")
        start_box.pack(pady=20)

        self.start_btn = ctk.CTkButton(
            start_box,
            text="🚀 Start Leak Audit",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#D9534F",
            hover_color="#C9302C",
            height=46,
            width=230,
            corner_radius=8,
            command=self._on_start_click
        )
        self.start_btn.pack()

        # 3. Progress & Status Bar Frame (Initially Hidden)
        self.progress_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=10)
        
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Initializing 5-Vector Security Audit...",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#4F53D9"
        )
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=10, corner_radius=5)
        self.progress_bar.set(0.05)
        self.progress_bar.configure(progress_color="#D9534F")

        # 4. Main Results Scroll Container (Initially Hidden)
        self.results_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")

    def _on_start_click(self):
        # Hide intro view
        self.intro_frame.pack_forget()

        # Show progress frame
        self.progress_frame.pack(fill="x", padx=20, pady=10)
        self.status_label.pack(anchor="w", padx=20, pady=(15, 8))
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 15))

        # Show results container
        self.results_scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Execute audit in background thread
        threading.Thread(target=self._execute_audit, daemon=True).start()

    def _execute_audit(self):
        def update_progress(msg: str, pct: float):
            self.after(0, lambda: self._on_progress(msg, pct))

        results = run_deep_dns_leak_test(
            callback=update_progress,
            active_provider_name=self.active_provider_name,
            doh_url=self.doh_url
        )

        self.after(0, lambda: self._render_results(results))

    def _on_progress(self, msg: str, pct: float):
        self.status_label.configure(text=msg)
        self.progress_bar.set(pct)

    def _render_results(self, results: Dict[str, Any]):
        self.status_label.configure(text="Audit Completed!", text_color="#2ECC71")
        self.progress_bar.set(1.0)

        # Build Security Verdict Badge
        badge_color = results.get("badge_color", "#2ECC71")
        verdict_card = ctk.CTkFrame(self.results_scroll, fg_color=badge_color, corner_radius=10)
        verdict_card.pack(fill="x", pady=(0, 15))

        v_title = ctk.CTkLabel(
            verdict_card, 
            text=results.get("badge_title", "100% SECURE"),
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        v_title.pack(anchor="w", padx=20, pady=(15, 2))

        v_sub = ctk.CTkLabel(
            verdict_card, 
            text=results.get("badge_subtitle", ""),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#F0F0F0"
        )
        v_sub.pack(anchor="w", padx=20, pady=(0, 15))

        # 5-Vector Diagnostics Grid
        grid_frame = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 15))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="diag")

        doh_info = results.get("doh_status", {})
        dnssec_info = results.get("dnssec_status", {})
        adblock_info = results.get("adblock_status", {})
        transparent_proxy = results.get("transparent_proxy_detected", False)

        # Card 1: DoH TLS
        c1 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=8)
        c1.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkLabel(c1, text="🔒 DoH TLS 1.3", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(c1, text="Verified" if doh_info.get("is_connected") else "Failed", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#2ECC71" if doh_info.get("is_connected") else "#E74C3C").pack(anchor="w", padx=10, pady=(0, 10))

        # Card 2: DNSSEC
        c2 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=8)
        c2.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkLabel(c2, text="🛡️ DNSSEC", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(c2, text="Enforced" if dnssec_info.get("is_active") else "Inactive", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#2ECC71" if dnssec_info.get("is_active") else "#F39C12").pack(anchor="w", padx=10, pady=(0, 10))

        # Card 3: Ad Shield
        c3 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=8)
        c3.grid(row=0, column=2, padx=5, sticky="ew")
        ctk.CTkLabel(c3, text="⛨ Ad & Tracker Shield", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(c3, text=f"Active ({adblock_info.get('blocked')}/{adblock_info.get('total')})" if adblock_info.get("is_active") else "Standard", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#2ECC71" if adblock_info.get("is_active") else "#A0A0A0").pack(anchor="w", padx=10, pady=(0, 10))

        # Card 4: Transparent Proxy
        c4 = ctk.CTkFrame(grid_frame, fg_color="#181818", corner_radius=8)
        c4.grid(row=0, column=3, padx=5, sticky="ew")
        ctk.CTkLabel(c4, text="🌐 ISP Proxy Intercept", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(c4, text="Intercepted!" if transparent_proxy else "Clean (No Proxy)", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#E74C3C" if transparent_proxy else "#2ECC71").pack(anchor="w", padx=10, pady=(0, 10))

        # Resolvers Table Section
        table_title = ctk.CTkLabel(
            self.results_scroll,
            text="📊 Detected Upstream Resolvers (36-Sample Audit Matrix)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        table_title.pack(anchor="w", pady=(15, 10))

        resolvers = results.get("resolvers", [])
        if not resolvers:
            no_data = ctk.CTkLabel(self.results_scroll, text="No upstream resolver anomalies detected.", text_color="#A0A0A0")
            no_data.pack(anchor="w")
        else:
            for item in resolvers:
                r_card = ctk.CTkFrame(self.results_scroll, fg_color="#181818", corner_radius=8)
                r_card.pack(fill="x", pady=4)
                
                status_color = "#E74C3C" if item.get("is_leak") else "#2ECC71"
                
                left_box = ctk.CTkFrame(r_card, fg_color="transparent")
                left_box.pack(side="left", padx=15, pady=10)
                
                ip_lbl = ctk.CTkLabel(left_box, text=f"IP: {item.get('ip')}", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color="#FFFFFF")
                ip_lbl.pack(anchor="w")
                
                prov_lbl = ctk.CTkLabel(left_box, text=f"{item.get('provider')} ({item.get('country')})", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#A0A0A0")
                prov_lbl.pack(anchor="w")
                
                badge = ctk.CTkLabel(
                    r_card,
                    text=item.get("status_text", ""),
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    text_color="#FFFFFF",
                    fg_color=status_color,
                    corner_radius=6,
                    padx=12,
                    pady=4
                )
                badge.pack(side="right", padx=15, pady=10)

        # Close Button Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        close_btn = ctk.CTkButton(
            btn_frame, 
            text="Close Audit", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#D9534F",
            hover_color="#C9302C",
            height=40,
            command=self.destroy
        )
        close_btn.pack(side="right")

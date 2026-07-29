import customtkinter as ctk
import sys
import ctypes
import os
import threading
import time
import concurrent.futures
import pystray
from pystray import MenuItem as item
from PIL import Image

from src.core.network import (
    is_admin,
    get_network_adapters,
    get_active_profile,
    ping_profile,
    benchmark_profiles,
    get_current_network_name
)
from src.core.dns import apply_dns
from src.core.config import load_profiles, load_settings, save_settings, get_resource_path
from src.core.shield import (
    test_adblocking,
    test_dnssec_validation,
    test_doh_tls_status,
    flush_dns_cache
)
from src.core.autostart import is_autostart_enabled, set_autostart
from src.ui.components.profile_card import ProfileCard

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

ctk.set_appearance_mode("Dark")


class ApplyLogModal(ctk.CTkToplevel):
    def __init__(self, master, profile_name: str, adapter_name: str):
        super().__init__(master)
        self.title("DNS Configuration Log")
        self.geometry("580x440")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        assets_dir = get_resource_path("assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            self.after(200, lambda: self.iconbitmap(app_icon_path))

        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 580) // 2
        y = master.winfo_y() + (master.winfo_height() - 440) // 2
        self.geometry(f"+{x}+{y}")

        self.header = ctk.CTkLabel(
            self, text="⚙️ Applying DNS Configuration...",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#D9534F"
        )
        self.header.pack(pady=(18, 5))

        self.sub_header = ctk.CTkLabel(
            self, text=f"Profile: {profile_name}  |  Adapter: {adapter_name}",
            font=ctk.CTkFont(size=12), text_color="gray70"
        )
        self.sub_header.pack(pady=(0, 10))

        # Log Text Area
        self.textbox = ctk.CTkTextbox(
            self, width=530, height=260,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#101010", text_color="#00FF00", corner_radius=8
        )
        self.textbox.pack(padx=20, pady=5)
        self.textbox.configure(state="disabled")

        self.close_btn = ctk.CTkButton(
            self, text="Close", command=self.destroy,
            width=140, height=38, fg_color="#333333", hover_color="#555555",
            font=ctk.CTkFont(weight="bold"), state="disabled"
        )
        self.close_btn.pack(pady=12)

    def append_log(self, log_lines: list[str]):
        self.textbox.configure(state="normal")
        for line in log_lines:
            self.textbox.insert("end", line + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def mark_complete(self, success: bool, message: str):
        self.textbox.configure(state="normal")
        status_line = f"\n=== RESULT: {'SUCCESS' if success else 'ERROR'} ==="
        self.textbox.insert("end", status_line + "\n")
        self.textbox.insert("end", f"Message: {message}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

        if success:
            self.header.configure(text="✅ DNS Successfully Applied!", text_color="#00FF00")
        else:
            self.header.configure(text="❌ Error Applying DNS Settings", text_color="#D9534F")

        self.close_btn.configure(state="normal", fg_color="#C9302C", hover_color="#AC2925")


class CipherDNSApp(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=("#F5F5F5", "#080808"))

        self.title("CipherDNS")
        self.geometry("1020x760")
        self.resizable(False, False)

        # Check if launched in autostart / silent mode
        self.is_silent_autostart = "--autostart" in sys.argv
        if self.is_silent_autostart:
            self.withdraw()

        # 1. Immediate local profile & settings loading (0ms)
        self.base_profiles = load_profiles()
        self.app_settings = load_settings()
        self.profiles = self.get_all_profiles()

        # Initial fallback state before async PowerShell checks complete
        self.adapters = []
        self.active_profile_id = None
        self.selected_profile_id = self.profiles[0]['id'] if self.profiles else 'clear'

        self.pings = {p['id']: None for p in self.profiles}
        self.fastest_profile_id = None

        self.last_seen_network = None
        self.monitoring = True
        self.is_applying = False
        self.is_benchmarking = False
        self.last_apply_logs = []

        # 2. Load icons & Build UI immediately
        self.load_images()
        self.build_ui()

        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.setup_tray()

        if self.is_silent_autostart and hasattr(self, 'tray_icon') and self.tray_icon:
            self.after(1000, lambda: self.tray_icon.notify("CipherDNS started silently in the background.", "CipherDNS Auto-Start"))

        # 3. Asynchronously query network adapters & active profile in background
        threading.Thread(target=self._async_initial_adapter_check, daemon=True).start()

        # 4. Start speed test
        self.after(100, self.start_speed_test)
        
        # 5. Start auto-switch monitor thread
        threading.Thread(target=self._network_monitor_loop, daemon=True).start()

    def _async_initial_adapter_check(self):
        adapters = get_network_adapters()
        default_adapter = adapters[0] if adapters else "No active adapter"
        active_prof = get_active_profile(default_adapter, self.profiles) if default_adapter != "No active adapter" else None

        def apply_initial_state():
            self.adapters = adapters
            adapter_vals = self.adapters if self.adapters else ["No active adapter"]
            self.adapter_menu.configure(values=adapter_vals)
            self.adapter_var.set(default_adapter)

            if active_prof:
                self.active_profile_id = active_prof
                self.selected_profile_id = active_prof

            self.render_cards(force_rebuild=False)

        self.after(0, apply_initial_state)

    def get_all_profiles(self) -> list[dict]:
        profiles = list(self.base_profiles)

        nextdns_id = self.app_settings.get("nextdns_id", "")
        is_configured = bool(nextdns_id)
        nextdns = {
            "id": "nextdns",
            "name": "NextDNS",
            "ipv4": ["45.90.28.0", "45.90.30.0"],
            "ipv6": ["2a07:a8c0::", "2a07:a8c1::"],
            "doh": f"https://dns.nextdns.io/{nextdns_id}" if is_configured else "https://dns.nextdns.io/",
            "description": f"ID: {nextdns_id}" if is_configured else "Click gear to configure ID.",
            "is_configured": is_configured,
            "features": ["malware", "ads", "trackers", "family"]
        }

        clear_idx = next((i for i, p in enumerate(profiles) if p['id'] == 'clear'), len(profiles))
        profiles.insert(clear_idx, nextdns)

        customs = self.app_settings.get("custom_profiles", [])
        for c in customs:
            c['is_custom'] = True
            profiles.insert(clear_idx, c)
            clear_idx += 1

        return profiles

    def hide_window(self):
        self.withdraw()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.notify("CipherDNS is still protecting you in the background.", "CipherDNS Minimized")
            except Exception:
                pass

    def setup_tray(self):
        assets_dir = get_resource_path("assets")
        app_icon_png = os.path.join(assets_dir, "app_icon.png")

        try:
            image = Image.open(app_icon_png)
        except Exception:
            image = Image.new('RGB', (64, 64), color='#C9302C')

        def on_show(icon, item):
            self.after(0, self.deiconify)
            self.after(0, self.lift)

        def on_quit(icon, item):
            self.monitoring = False
            try:
                icon.stop()
            except Exception:
                pass
            self.after(0, self.destroy)

        def on_set_profile(icon, clicked_item):
            profile = next((p for p in self.profiles if p['name'] == clicked_item.text), None)
            if profile:
                self.after(0, lambda: self._apply_dns_from_tray(profile))

        def on_flush_dns_tray(icon, item):
            self.after(0, self.trigger_flush_dns)

        menu_items = [
            item("Show CipherDNS", on_show, default=True),
            item("🧹 Flush DNS Cache", on_flush_dns_tray),
            pystray.Menu.SEPARATOR
        ]

        for p in self.profiles:
            menu_items.append(item(p['name'], on_set_profile))

        menu_items.extend([
            pystray.Menu.SEPARATOR,
            item("Quit", on_quit)
        ])

        self.tray_icon = pystray.Icon("CipherDNS", image, "CipherDNS", pystray.Menu(*menu_items))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def update_tray_menu(self):
        if not hasattr(self, 'tray_icon') or not self.tray_icon:
            return

        def on_show(icon, item):
            self.after(0, self.deiconify)
            self.after(0, self.lift)

        def on_quit(icon, item):
            self.monitoring = False
            try:
                icon.stop()
            except Exception:
                pass
            self.after(0, self.destroy)

        def on_set_profile(icon, clicked_item):
            profile = next((p for p in self.profiles if p['name'] == clicked_item.text), None)
            if profile:
                self.after(0, lambda: self._apply_dns_from_tray(profile))

        def on_flush_dns_tray(icon, item):
            self.after(0, self.trigger_flush_dns)

        menu_items = [
            item("Show CipherDNS", on_show, default=True),
            item("🧹 Flush DNS Cache", on_flush_dns_tray),
            pystray.Menu.SEPARATOR
        ]

        for p in self.profiles:
            menu_items.append(item(p['name'], on_set_profile))

        menu_items.extend([
            pystray.Menu.SEPARATOR,
            item("Quit", on_quit)
        ])

        self.tray_icon.menu = pystray.Menu(*menu_items)

    def trigger_flush_dns(self):
        def run_flush():
            success, msg = flush_dns_cache()
            self.after(0, lambda: self._on_flush_complete(success, msg))

        threading.Thread(target=run_flush, daemon=True).start()

    def _on_flush_complete(self, success: bool, msg: str):
        if success:
            self.status_label.configure(text="✅ DNS Cache Flushed!", text_color="#00FF00")
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.notify("DNS resolver cache cleared.", "CipherDNS")
        else:
            self.status_label.configure(text=f"❌ Flush Error: {msg}", text_color="#D9534F")

    def _apply_dns_from_tray(self, profile):
        if profile['id'] == 'nextdns' and not profile.get('is_configured'):
            self.tray_icon.notify("NextDNS is not configured. Please open the app.", "CipherDNS Error")
            return

        adapter = self.adapter_var.get()
        if adapter in ["No active adapter", "Scanning adapters..."]:
            self.tray_icon.notify("Error: No network adapter selected!", "CipherDNS Error")
            return

        strict = self.fallback_var.get()

        def run_apply():
            success, msg, logs = apply_dns(adapter, profile, strict_doh=strict)
            self.after(0, lambda: self._on_tray_apply_complete(success, msg, profile))

        threading.Thread(target=run_apply, daemon=True).start()

    def _on_tray_apply_complete(self, success, msg, profile):
        if success:
            self.tray_icon.notify(f"Successfully applied: {profile['name']}", "CipherDNS")
            self.selected_profile_id = profile['id']
            self.update_active_profile()
            self._save_network_memory(profile['id'])
        else:
            self.tray_icon.notify(f"Failed to apply: {msg}", "CipherDNS Error")

    def start_speed_test(self):
        if hasattr(self, 'status_label') and not self.is_benchmarking:
            self.status_label.configure(text="Running speed tests...", text_color="yellow")
        threading.Thread(target=self._run_pings_in_background, daemon=True).start()

    def _run_pings_in_background(self):
        workers = max(1, len(self.profiles))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_pid = {executor.submit(ping_profile, p): p['id'] for p in self.profiles if p['id'] != 'clear'}
            for future in concurrent.futures.as_completed(future_to_pid):
                pid = future_to_pid[future]
                try:
                    ms = future.result()
                    self.pings[pid] = ms
                except Exception:
                    self.pings[pid] = None

        valid_pings = {k: v for k, v in self.pings.items() if v is not None}
        if valid_pings:
            self.fastest_profile_id = min(valid_pings, key=valid_pings.get)

        self.after(0, self._on_speed_test_complete)

    def _on_speed_test_complete(self):
        if not self.is_applying and not self.is_benchmarking and hasattr(self, 'status_label'):
            self.status_label.configure(text="Ready.", text_color="gray")
        self.render_cards(force_rebuild=False)

    def auto_select_fastest(self):
        """Runs a 3-sample latency benchmark across all providers and applies the fastest one automatically."""
        if self.is_benchmarking or self.is_applying:
            return

        self.is_benchmarking = True
        self.auto_fastest_btn.configure(state="disabled")
        self.status_label.configure(text="⚡ Benchmarking lowest latency DNS...", text_color="yellow")

        def run_benchmark():
            fastest_id, results = benchmark_profiles(self.profiles, samples_count=3)
            self.after(0, lambda: self._on_benchmark_complete(fastest_id, results))

        threading.Thread(target=run_benchmark, daemon=True).start()

    def _on_benchmark_complete(self, fastest_id: str | None, results: dict[str, int]):
        self.is_benchmarking = False
        self.auto_fastest_btn.configure(state="normal")

        if results:
            for pid, avg_ms in results.items():
                self.pings[pid] = avg_ms

        if fastest_id:
            self.fastest_profile_id = fastest_id
            fastest_prof = next((p for p in self.profiles if p['id'] == fastest_id), None)
            if fastest_prof:
                self.selected_profile_id = fastest_id
                self.render_cards(force_rebuild=False)
                self.status_label.configure(text=f"⚡ Auto-selected fastest: {fastest_prof['name']} ({results.get(fastest_id, 0)}ms)", text_color="#00FF00")
                # Automatically apply the fastest DNS provider!
                self.apply_dns_action()
                return

        self.status_label.configure(text="Benchmark complete.", text_color="gray")
        self.render_cards(force_rebuild=False)

    def on_autostart_toggle(self):
        enabled = self.autostart_var.get()
        success = set_autostart(enabled)
        if not success:
            self.autostart_var.set(not enabled)
            self.status_label.configure(text="❌ Failed to update startup registry!", text_color="#D9534F")

    def load_images(self):
        self.icons = {}
        assets_dir = get_resource_path("assets")

        app_icon_ico = os.path.join(assets_dir, "app_icon.ico")
        app_icon_png = os.path.join(assets_dir, "app_icon.png")

        if not os.path.exists(app_icon_ico) and os.path.exists(app_icon_png):
            try:
                img = Image.open(app_icon_png)
                img.save(app_icon_ico, format="ICO", sizes=[(72, 72)])
            except Exception:
                pass

        if os.path.exists(app_icon_ico):
            try:
                self.iconbitmap(app_icon_ico)
            except Exception:
                pass

        for p in self.profiles:
            img_path = os.path.join(assets_dir, f"{p['id']}.png")
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    self.icons[p['id']] = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
                except Exception:
                    self.icons[p['id']] = None
            else:
                self.icons[p['id']] = None

    def on_autoswitch_toggle(self):
        self.app_settings['auto_switch'] = self.auto_switch_var.get()
        save_settings(self.app_settings)

    def build_ui(self):
        # === 3-ZONE INTEGRATED DASHBOARD HEADER ===
        self.header_container = ctk.CTkFrame(self, fg_color="transparent")
        self.header_container.pack(fill="x", padx=25, pady=(18, 10))

        # --- LEFT ZONE: Network Adapter Card ---
        self.adapter_card = ctk.CTkFrame(self.header_container, fg_color="#121212", corner_radius=10)
        self.adapter_card.pack(side="left", anchor="n", padx=(0, 10), ipady=6, ipadx=10)

        ctk.CTkLabel(self.adapter_card, text="Network Adapter", font=ctk.CTkFont(weight="bold", size=12), text_color="gray70").pack(anchor="w", padx=8, pady=(4, 2))

        default_adapter = self.adapters[0] if self.adapters else "Scanning adapters..."
        self.adapter_var = ctk.StringVar(value=default_adapter)
        self.adapter_menu = ctk.CTkOptionMenu(
            self.adapter_card,
            values=self.adapters if self.adapters else ["Scanning adapters..."],
            variable=self.adapter_var,
            width=210,
            fg_color="#1E1E1E",
            button_color="#C9302C",
            button_hover_color="#AC2925",
            command=self.on_adapter_change
        )
        self.adapter_menu.pack(anchor="w", padx=8, pady=(0, 4))

        # --- CENTER ZONE: App Title & Feature Legend Pill ---
        self.center_card = ctk.CTkFrame(self.header_container, fg_color="transparent")
        self.center_card.pack(side="left", expand=True, fill="both")

        self.header = ctk.CTkLabel(self.center_card, text="🛡️ CipherDNS", font=ctk.CTkFont(size=28, weight="bold"), text_color="#D9534F")
        self.header.pack(anchor="center", pady=(0, 0))

        self.subtitle = ctk.CTkLabel(self.center_card, text="Modern DNS over HTTPS (DoH) Manager", font=ctk.CTkFont(size=12), text_color="gray")
        self.subtitle.pack(anchor="center", pady=(0, 6))

        self.legend_frame = ctk.CTkFrame(self.center_card, fg_color="#1A1A1A", corner_radius=12)
        self.legend_frame.pack(anchor="center", ipady=2, ipadx=8)

        items = [("⛨ Malware", "#FF6B6B"), ("⊘ Ads", "#FDCB6E"), ("◉ Trackers", "#74B9FF"), ("♥ Family", "#55EFC4")]
        for i, (text, color) in enumerate(items):
            lbl = ctk.CTkLabel(self.legend_frame, text=text, font=ctk.CTkFont(size=12, weight="bold"), text_color=color)
            lbl.pack(side="left", padx=8)
            if i < len(items) - 1:
                sep = ctk.CTkLabel(self.legend_frame, text="•", font=ctk.CTkFont(size=11), text_color="gray40")
                sep.pack(side="left")

        # --- RIGHT ZONE: Controls & Switches Card ---
        self.switches_card = ctk.CTkFrame(self.header_container, fg_color="#121212", corner_radius=10)
        self.switches_card.pack(side="right", anchor="n", padx=(10, 0), ipady=6, ipadx=10)

        # Row 1: Strict DoH
        self.row1_frame = ctk.CTkFrame(self.switches_card, fg_color="transparent")
        self.row1_frame.pack(fill="x", padx=8, pady=(2, 2))

        self.fallback_var = ctk.BooleanVar(value=False)
        self.fallback_switch = ctk.CTkSwitch(self.row1_frame, text="Strict DoH ", variable=self.fallback_var, progress_color="#C9302C", font=ctk.CTkFont(size=12))
        self.fallback_switch.pack(side="left")

        self.info_btn = ctk.CTkButton(
            self.row1_frame, text="?", width=20, height=20, corner_radius=10,
            fg_color="#333333", hover_color="#C9302C", font=ctk.CTkFont(weight="bold", size=10), command=self.show_doh_info
        )
        self.info_btn.pack(side="left", padx=(4, 0))

        # Row 2: Auto-Switch
        self.auto_switch_var = ctk.BooleanVar(value=self.app_settings.get("auto_switch", False))
        self.auto_switch_chk = ctk.CTkSwitch(
            self.switches_card, text="Auto-Switch (Smart Memory)", variable=self.auto_switch_var, progress_color="#00CC00", command=self.on_autoswitch_toggle, font=ctk.CTkFont(size=12)
        )
        self.auto_switch_chk.pack(anchor="w", padx=8, pady=(2, 2))

        # Row 3: Windows Auto-Start
        self.autostart_var = ctk.BooleanVar(value=is_autostart_enabled())
        self.autostart_chk = ctk.CTkSwitch(
            self.switches_card, text="Start with Windows", variable=self.autostart_var, progress_color="#00CC00", command=self.on_autostart_toggle, font=ctk.CTkFont(size=12)
        )
        self.autostart_chk.pack(anchor="w", padx=8, pady=(2, 2))

        # === CARDS SECTION HEADER ===
        self.cards_header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_header_frame.pack(fill="x", padx=30, pady=(15, 5))

        self.cards_title = ctk.CTkLabel(self.cards_header_frame, text="Available DNS Providers", font=ctk.CTkFont(weight="bold", size=16))
        self.cards_title.pack(side="left")

        # Auto-Select Fastest DNS Button
        self.auto_fastest_btn = ctk.CTkButton(
            self.cards_header_frame, text="⚡ Auto-Select Fastest", command=self.auto_select_fastest,
            height=30, width=170, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1A1A1A", hover_color="#333333", text_color="#00FF00", corner_radius=6
        )
        self.auto_fastest_btn.pack(side="right")

        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="both", expand=True, padx=25, pady=5)

        self.card_widgets = []

        # === SPACIOUS BOTTOM BAR ===
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#121212", corner_radius=10, height=74)
        self.bottom_frame.pack(fill="x", side="bottom", padx=25, pady=(0, 12))
        self.bottom_frame.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.bottom_frame, text="Ready.", text_color="gray", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_label.pack(side="left", padx=18)

        self.apply_btn = ctk.CTkButton(
            self.bottom_frame, text="Apply DNS", command=self.apply_dns_action, height=52, width=155,
            font=ctk.CTkFont(weight="bold", size=15), fg_color="#C9302C", hover_color="#AC2925", corner_radius=8
        )
        self.apply_btn.pack(side="right", padx=12, pady=11)

        self.security_btn = ctk.CTkButton(
            self.bottom_frame, text="🔍 Leak Audit", command=self.open_security_check, height=52, width=140,
            font=ctk.CTkFont(weight="bold", size=13), fg_color="#262626", hover_color="#444444", corner_radius=8
        )
        self.security_btn.pack(side="right", padx=0, pady=11)

        # 🧹 Flush DNS Cache Button
        self.flush_btn = ctk.CTkButton(
            self.bottom_frame, text="🧹 Flush Cache", command=self.trigger_flush_dns, height=52, width=135,
            font=ctk.CTkFont(weight="bold", size=13), fg_color="#1A1A1A", hover_color="#333333", text_color="gray80", corner_radius=8
        )
        self.flush_btn.pack(side="right", padx=(0, 12), pady=11)

        # Immediate 0ms rendering of DNS cards
        self.render_cards(force_rebuild=True)

    def refresh_adapters(self):
        new_adapters = get_network_adapters()
        if new_adapters != self.adapters:
            self.adapters = new_adapters
            adapter_vals = self.adapters if self.adapters else ["No active adapter"]
            self.adapter_menu.configure(values=adapter_vals)
            if self.adapter_var.get() not in adapter_vals:
                self.adapter_var.set(adapter_vals[0])

    def _save_network_memory(self, profile_id):
        net_name = get_current_network_name()
        if net_name:
            if "network_memory" not in self.app_settings:
                self.app_settings["network_memory"] = {}
            self.app_settings["network_memory"][net_name] = profile_id
            save_settings(self.app_settings)

    def _network_monitor_loop(self):
        while self.monitoring:
            try:
                if self.app_settings.get("auto_switch", False) and not self.is_applying:
                    current_net = get_current_network_name()
                    if current_net and current_net != self.last_seen_network:
                        self.last_seen_network = current_net
                        memory = self.app_settings.get("network_memory", {})

                        if current_net in memory:
                            target_id = memory[current_net]
                            if self.active_profile_id != target_id:
                                self.after(0, lambda tid=target_id, net=current_net: self._auto_apply_dns(tid, net))
            except Exception as e:
                print(f"[App] Network monitor error: {e}")
            time.sleep(5)

    def _auto_apply_dns(self, target_id, network_name):
        adapter = self.adapter_var.get()
        if adapter in ["No active adapter", "Scanning adapters..."]:
            return

        profile = next((p for p in self.profiles if p['id'] == target_id), None)
        if not profile or (profile['id'] == 'nextdns' and not profile.get('is_configured')):
            return

        def run_auto():
            success, msg, logs = apply_dns(adapter, profile, strict_doh=self.fallback_var.get())
            if success:
                self.after(0, lambda: self._on_auto_apply_success(profile, network_name))

        threading.Thread(target=run_auto, daemon=True).start()

    def _on_auto_apply_success(self, profile, network_name):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.notify(f"Auto-switched to {profile['name']} for network '{network_name}'", "CipherDNS Auto-Switch")
        self.selected_profile_id = profile['id']
        self.update_active_profile()

    def update_active_profile(self):
        adapter = self.adapter_var.get()
        if adapter and adapter not in ["No active adapter", "Scanning adapters..."]:
            self.active_profile_id = get_active_profile(adapter, self.profiles)
        else:
            self.active_profile_id = None

        if not self.is_applying and not self.is_benchmarking and "tests" not in self.status_label.cget("text"):
            self.status_label.configure(text="Ready.", text_color="gray")
        self.render_cards(force_rebuild=False)

    def on_adapter_change(self, value):
        self.update_active_profile()

    def render_cards(self, force_rebuild=False):
        if not force_rebuild and len(self.card_widgets) == len(self.profiles) + 1:
            for card in self.card_widgets:
                if getattr(card, 'is_add_card', False):
                    continue

                pid = card.profile['id']
                is_selected = (pid == self.selected_profile_id)
                is_active = (pid == self.active_profile_id)
                ping_val = self.pings.get(pid)
                is_fastest = (pid == self.fastest_profile_id)

                card.update_state(is_selected, is_active)
                card.update_ping(ping_val, is_fastest)
            return

        for w in self.card_widgets:
            w.destroy()
        self.card_widgets.clear()

        columns = 4
        for i in range(columns):
            self.cards_frame.grid_columnconfigure(i, weight=1)

        row, col = 0, 0
        for profile in self.profiles:
            is_selected = (profile['id'] == self.selected_profile_id)
            is_active = (profile['id'] == self.active_profile_id)
            ping_val = self.pings.get(profile['id'])
            is_fastest = (profile['id'] == self.fastest_profile_id)

            icon = self.icons.get(profile['id'])

            on_configure = self.configure_nextdns if profile['id'] == 'nextdns' else None
            on_delete = self.delete_custom_profile if profile.get('is_custom') else None
            has_info = not on_configure and not on_delete and profile['id'] != 'clear'

            card = ProfileCard(
                self.cards_frame, profile, icon, self.select_profile,
                is_selected, is_active, ping_val, is_fastest,
                on_configure=on_configure, on_delete=on_delete, has_info=has_info
            )

            card.grid(row=row, column=col, padx=10, pady=10)
            self.card_widgets.append(card)

            col += 1
            if col >= columns:
                col = 0
                row += 1

        # Add custom DNS card (+)
        add_card = ctk.CTkFrame(self.cards_frame, corner_radius=10, width=215, height=180, fg_color="transparent", border_width=2, border_color="gray30")
        add_card.pack_propagate(False)
        add_card.grid_propagate(False)
        add_card.bind("<Button-1>", self.open_add_custom_dialog)
        add_card.is_add_card = True

        lbl = ctk.CTkLabel(add_card, text="+", font=ctk.CTkFont(size=44, weight="bold"), text_color="gray50")
        lbl.place(relx=0.5, rely=0.4, anchor="center")
        lbl.bind("<Button-1>", self.open_add_custom_dialog)

        lbl2 = ctk.CTkLabel(add_card, text="Add Custom DNS", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray50")
        lbl2.place(relx=0.5, rely=0.7, anchor="center")
        lbl2.bind("<Button-1>", self.open_add_custom_dialog)

        add_card.grid(row=row, column=col, padx=10, pady=10)
        self.card_widgets.append(add_card)

    def select_profile(self, profile_id):
        self.selected_profile_id = profile_id
        self.render_cards(force_rebuild=False)

    def configure_nextdns(self, profile_id):
        win = ctk.CTkToplevel(self)
        win.title("Configure NextDNS")
        win.geometry("350x220")
        win.attributes("-topmost", True)
        win.resizable(False, False)

        assets_dir = get_resource_path("assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            win.after(200, lambda: win.iconbitmap(app_icon_path))

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 220) // 2
        win.geometry(f"+{x}+{y}")

        ctk.CTkLabel(win, text="NextDNS Configuration", font=ctk.CTkFont(size=16, weight="bold"), text_color="#D9534F").pack(pady=(20, 10))
        ctk.CTkLabel(win, text="Enter your Configuration ID (e.g. a1b2c3):", font=ctk.CTkFont(size=12), text_color="gray70").pack(pady=(0, 10))

        id_entry = ctk.CTkEntry(win, placeholder_text="Configuration ID", width=200)
        id_entry.pack(pady=5)
        id_entry.insert(0, self.app_settings.get("nextdns_id", ""))

        def save():
            val = id_entry.get().strip()
            self.app_settings['nextdns_id'] = val
            save_settings(self.app_settings)
            self.profiles = self.get_all_profiles()
            self.update_tray_menu()
            self.render_cards(force_rebuild=True)
            self.start_speed_test()
            win.destroy()

        ctk.CTkButton(win, text="Save", command=save, fg_color="#C9302C", hover_color="#AC2925", width=120).pack(pady=15)

    def open_add_custom_dialog(self, event=None):
        win = ctk.CTkToplevel(self)
        win.title("Add Custom DNS")
        win.geometry("400x380")
        win.attributes("-topmost", True)

        assets_dir = get_resource_path("assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            win.after(200, lambda: win.iconbitmap(app_icon_path))

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 380) // 2
        win.geometry(f"+{x}+{y}")

        ctk.CTkLabel(win, text="Add Custom DNS Profile", font=ctk.CTkFont(size=16, weight="bold"), text_color="#D9534F").pack(pady=(20, 15))

        name_entry = ctk.CTkEntry(win, placeholder_text="Profile Name (e.g. My Pi-Hole)", width=300)
        name_entry.pack(pady=8)

        ipv4_entry = ctk.CTkEntry(win, placeholder_text="IPv4 Address (e.g. 192.168.1.100)", width=300)
        ipv4_entry.pack(pady=8)

        doh_entry = ctk.CTkEntry(win, placeholder_text="DoH URL (e.g. https://dns.local/dns-query)", width=300)
        doh_entry.pack(pady=8)

        error_lbl = ctk.CTkLabel(win, text="", text_color="#D9534F", font=ctk.CTkFont(size=11))
        error_lbl.pack(pady=5)

        def save():
            name = name_entry.get().strip()
            ipv4 = ipv4_entry.get().strip()
            doh = doh_entry.get().strip()

            if not name or not ipv4 or not doh:
                error_lbl.configure(text="Please fill in all fields!")
                return

            new_prof = {
                "id": f"custom_{int(time.time())}",
                "name": name,
                "ipv4": [ipv4],
                "ipv6": [],
                "doh": doh,
                "description": "Custom user profile."
            }
            if "custom_profiles" not in self.app_settings:
                self.app_settings["custom_profiles"] = []
            self.app_settings["custom_profiles"].append(new_prof)
            save_settings(self.app_settings)

            self.profiles = self.get_all_profiles()
            self.update_tray_menu()
            self.render_cards(force_rebuild=True)
            self.start_speed_test()
            win.destroy()

        ctk.CTkButton(win, text="Save", command=save, fg_color="#C9302C", hover_color="#AC2925", width=120).pack(pady=10)

    def delete_custom_profile(self, profile_id):
        if "custom_profiles" in self.app_settings:
            self.app_settings["custom_profiles"] = [p for p in self.app_settings["custom_profiles"] if p['id'] != profile_id]
            save_settings(self.app_settings)
            self.profiles = self.get_all_profiles()
            self.update_tray_menu()
            self.render_cards(force_rebuild=True)

    def show_doh_info(self):
        info_win = ctk.CTkToplevel(self)
        info_win.title("What is Strict DoH?")
        info_win.geometry("440x310")
        info_win.attributes("-topmost", True)
        info_win.resizable(False, False)

        assets_dir = get_resource_path("assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            info_win.after(200, lambda: info_win.iconbitmap(app_icon_path))

        info_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 440) // 2
        y = self.winfo_y() + (self.winfo_height() - 310) // 2
        info_win.geometry(f"+{x}+{y}")

        title = ctk.CTkLabel(info_win, text="Strict DoH (Encrypted Only)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#D9534F")
        title.pack(pady=(20, 10))

        intro = ctk.CTkLabel(
            info_win, text="Strict DoH ensures that your computer communicates with the DNS server EXCLUSIVELY over an encrypted (HTTPS) connection.",
            justify="left", wraplength=400, text_color=("gray20", "gray80"), font=ctk.CTkFont(size=12)
        )
        intro.pack(padx=20, pady=(0, 15))

        strict_title = ctk.CTkLabel(info_win, text="ENABLED (Strict Mode):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00FF00")
        strict_title.pack(padx=20, anchor="w")
        strict_desc = ctk.CTkLabel(
            info_win, text="Maximum security. No compromises. If the network doesn't support it, you lose internet access.",
            justify="left", wraplength=400, text_color=("gray20", "gray80"), font=ctk.CTkFont(size=12)
        )
        strict_desc.pack(padx=20, anchor="w", pady=(0, 15))

        fallback_title = ctk.CTkLabel(info_win, text="DISABLED (Fallback / Default):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF9900")
        fallback_title.pack(padx=20, anchor="w")
        fallback_desc = ctk.CTkLabel(
            info_win, text="More flexible. Falls back to standard, unencrypted DNS in case of connection failure.",
            justify="left", wraplength=400, text_color=("gray20", "gray80"), font=ctk.CTkFont(size=12)
        )
        fallback_desc.pack(padx=20, anchor="w")

        btn = ctk.CTkButton(info_win, text="Got it", command=info_win.destroy, width=100, fg_color="#C9302C", hover_color="#AC2925")
        btn.pack(pady=15)

    def open_security_check(self):
        from src.ui.modals.leak_modal import DeepLeakAuditModal

        adapter = self.adapter_var.get()
        active_prof_name = "Cloudflare"
        doh_url = "https://cloudflare-dns.com/dns-query"

        if adapter and adapter not in ["No active adapter", "Scanning adapters..."]:
            prof_id = get_active_profile(adapter, self.profiles)
            active_prof = next((p for p in self.profiles if p['id'] == prof_id), None)
            if active_prof:
                active_prof_name = active_prof.get("name", "Custom DNS")
                doh_url = (
                    active_prof.get("doh", "") or 
                    active_prof.get("doh_v4", {}).get("template", "") or 
                    active_prof.get("doh_template", "")
                )
                if active_prof.get("id") == "nextdns":
                    nextdns_id = self.app_settings.get("nextdns_id", "").strip()
                    if nextdns_id:
                        doh_url = f"https://dns.nextdns.io/{nextdns_id}"

        DeepLeakAuditModal(self, active_provider_name=active_prof_name, doh_url=doh_url)

    def apply_dns_action(self):
        if self.is_applying:
            return

        adapter = self.adapter_var.get()
        if adapter in ["No active adapter", "Scanning adapters..."]:
            self.status_label.configure(text="Error: No adapter selected!", text_color="#D9534F")
            return

        profile = next((p for p in self.profiles if p['id'] == self.selected_profile_id), None)
        if not profile:
            return

        if profile['id'] == 'nextdns' and not profile.get('is_configured'):
            self.status_label.configure(text="NextDNS ID missing!", text_color="#D9534F")
            self.configure_nextdns(profile['id'])
            return

        strict = self.fallback_var.get()

        self.is_applying = True
        self.status_label.configure(text=f"Applying {profile['name']}...", text_color="yellow")
        self.apply_btn.configure(state="disabled")

        # Create and pop up the Log Modal immediately
        log_modal = ApplyLogModal(self, profile['name'], adapter)

        def run_apply_async():
            success, msg, logs = apply_dns(adapter, profile, strict_doh=strict)
            self.after(0, lambda: self._on_apply_complete(success, msg, logs, profile, log_modal))

        threading.Thread(target=run_apply_async, daemon=True).start()

    def _on_apply_complete(self, success: bool, msg: str, logs: list[str], profile: dict, log_modal: ApplyLogModal):
        self.is_applying = False
        self.apply_btn.configure(state="normal")
        self.last_apply_logs = logs

        # Update modal with complete log output
        log_modal.append_log(logs)
        log_modal.mark_complete(success, msg)

        if success:
            self.status_label.configure(text=f"✅ {profile['name']} Active", text_color="#00FF00")
            self.update_active_profile()
            self._save_network_memory(profile['id'])
        else:
            self.status_label.configure(text=f"❌ Error applying settings!", text_color="#D9534F")


def run_as_admin():
    try:
        script = os.path.abspath(sys.argv[0])
        executable = sys.executable
        if executable.lower().endswith("python.exe"):
            pythonw = executable[:-10] + "pythonw.exe"
            if os.path.exists(pythonw):
                executable = pythonw

        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, f'"{script}"', None, 0)
        sys.exit()
    except Exception as e:
        print(f"Error elevating permissions: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if not is_admin():
        run_as_admin()

    app = CipherDNSApp()
    app.mainloop()

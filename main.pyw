import customtkinter as ctk
import sys
import ctypes
import os
import threading
import time
import concurrent.futures
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from dns_core import is_admin, get_network_adapters, apply_dns, load_profiles, get_active_profile, ping_profile, load_settings, save_settings, get_current_network_name

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

ctk.set_appearance_mode("Dark")

class ProfileCard(ctk.CTkFrame):
    def __init__(self, master, profile, icon_img, command, is_selected=False, is_active=False, ping_ms=None, is_fastest=False, on_configure=None, on_delete=None, has_info=False):
        bg_color = ("#F2DEDE", "#1A1313") if is_selected else ("gray85", "#121212")
        border_color = ("#D9534F", "#D9534F") if is_selected else ("gray70", "#222222")
        bw = 2 if is_selected else 2
        
        super().__init__(master, corner_radius=10, 
                         width=195, height=175, 
                         fg_color=bg_color,
                         border_width=bw,
                         border_color=border_color)
        
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        self.profile = profile
        self.command = command
        self.is_flipped = False
        
        self.bind("<Button-1>", self.on_click)
        
        # --- ELSŐ LAP (FRONT) ---
        self.front_frame = ctk.CTkFrame(self, fg_color="transparent", width=188, height=168)
        self.front_frame.place(x=97.5, y=87.5, anchor="center")
        self.front_frame.pack_propagate(False)
        self.front_frame.bind("<Button-1>", self.on_click)
        
        if icon_img:
            self.icon = ctk.CTkLabel(self.front_frame, text="", image=icon_img)
        else:
            letter = profile['name'][0].upper() if profile.get('name') else "?"
            self.icon = ctk.CTkLabel(self.front_frame, text=letter, font=ctk.CTkFont(size=36, weight="bold"), text_color="gray50")
        
        self.icon.pack(pady=(12, 5))
        self.icon.bind("<Button-1>", self.on_click)
            
        self.name_label = ctk.CTkLabel(self.front_frame, text=profile['name'], font=ctk.CTkFont(size=14, weight="bold"), justify="center", wraplength=180)
        self.name_label.pack(padx=5, fill="x")
        self.name_label.bind("<Button-1>", self.on_click)
        
        self.desc_label = ctk.CTkLabel(self.front_frame, text=profile['description'], font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"), justify="center", wraplength=180)
        self.desc_label.pack(padx=5, pady=(0, 2), fill="both", expand=True)
        self.desc_label.bind("<Button-1>", self.on_click)

        # --- HÁTSÓ LAP (BACK) ---
        self.back_frame = ctk.CTkFrame(self, fg_color="transparent", width=188, height=168)
        # Rejtve (jobbra kitolva) indul
        self.back_frame.place(x=292.5, y=87.5, anchor="center")
        self.back_frame.pack_propagate(False)
        self.back_frame.bind("<Button-1>", self.on_click)
        
        ipv4_list = profile.get('ipv4', [])
        ipv4_str = ipv4_list[0] if ipv4_list else "None"
        
        ipv6_list = profile.get('ipv6', [])
        ipv6_str = ipv6_list[0] if ipv6_list else "None"
        
        raw_doh = profile.get('doh') or profile.get('doh_template') or "None"
        doh_str = raw_doh.replace("https://", "").split("/")[0] if raw_doh != "None" else "None"
        
        inner_back = ctk.CTkFrame(self.back_frame, fg_color="transparent")
        inner_back.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92)
        
        ctk.CTkLabel(inner_back, text="IPv4", font=ctk.CTkFont(size=10, weight="bold"), text_color="#D9534F", height=14, anchor="w").pack(anchor="w", padx=10)
        lbl_v4 = ctk.CTkLabel(inner_back, text=ipv4_str, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray90", height=16, anchor="w")
        lbl_v4.pack(anchor="w", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(inner_back, text="IPv6", font=ctk.CTkFont(size=10, weight="bold"), text_color="#D9534F", height=14, anchor="w").pack(anchor="w", padx=10)
        lbl_v6 = ctk.CTkLabel(inner_back, text=ipv6_str, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray90", height=16, anchor="w")
        lbl_v6.pack(anchor="w", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(inner_back, text="DoH Hostname", font=ctk.CTkFont(size=10, weight="bold"), text_color="#D9534F", height=14, anchor="w").pack(anchor="w", padx=10)
        lbl_doh = ctk.CTkLabel(inner_back, text=doh_str, font=ctk.CTkFont(size=11), text_color="gray80", height=16, anchor="w")
        lbl_doh.pack(anchor="w", padx=10)
        
        for w in inner_back.winfo_children():
            w.bind("<Button-1>", self.on_click)
        inner_back.bind("<Button-1>", self.on_click)

        # --- FELÜLRÉTEGEZETT ELEMEK (Gombok, Badgek - ezek nem mozognak) ---
        if is_active:
            self.badge_frame = ctk.CTkFrame(self, fg_color="#C9302C", corner_radius=9, width=40, height=20)
            self.badge_frame.place(relx=0.96, rely=0.04, anchor="ne")
            self.badge_frame.pack_propagate(False)
            
            badge_lbl = ctk.CTkLabel(self.badge_frame, text="SET", font=ctk.CTkFont(size=10, weight="bold"), text_color="white")
            badge_lbl.place(relx=0.5, rely=0.5, anchor="center")
            
            badge_lbl.bind("<Button-1>", self.on_click)
            self.badge_frame.bind("<Button-1>", self.on_click)

        if profile['id'] != 'clear':
            ping_text = "..." if ping_ms is None else f"{ping_ms} ms"
            ping_color = "gray50"
            if ping_ms is not None:
                if is_fastest:
                    ping_text = f"⚡ {ping_ms} ms"
                    ping_color = "#00FF00"
                elif ping_ms < 50:
                    ping_color = "#00CC00"
                elif ping_ms < 100:
                    ping_color = "#CCCC00"
                else:
                    ping_color = "#CC0000"
                    
            self.ping_lbl = ctk.CTkLabel(self, text=ping_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=ping_color)
            self.ping_lbl.place(relx=0.05, rely=0.04, anchor="nw")
            self.ping_lbl.bind("<Button-1>", self.on_click)

        if on_configure:
            cfg_btn = ctk.CTkButton(self, text="EDIT", width=46, height=24, corner_radius=6, fg_color="#333333", text_color="white", hover_color="#555555", font=ctk.CTkFont(weight="bold", size=11), command=lambda e=None: on_configure(self.profile['id']))
            cfg_btn.place(relx=0.96, rely=0.96, anchor="se")
            
        elif on_delete:
            del_btn = ctk.CTkButton(self, text="DEL", width=46, height=24, corner_radius=6, fg_color="#333333", text_color="white", hover_color="#CC0000", font=ctk.CTkFont(weight="bold", size=11), command=lambda e=None: on_delete(self.profile['id']))
            del_btn.place(relx=0.96, rely=0.96, anchor="se")
            
        elif has_info:
            info_btn = ctk.CTkButton(self, text="INFO", width=46, height=24, corner_radius=6, fg_color="#333333", text_color="white", hover_color="#555555", font=ctk.CTkFont(weight="bold", size=11), command=self.toggle_flip)
            info_btn.place(relx=0.96, rely=0.96, anchor="se")
        
    def update_ping(self, ping_ms, is_fastest):
        if not hasattr(self, 'ping_lbl'): return
        ping_text = "..." if ping_ms is None else f"{ping_ms} ms"
        ping_color = "gray50"
        if ping_ms is not None:
            if is_fastest:
                ping_text = f"⚡ {ping_ms} ms"
                ping_color = "#00FF00"
            elif ping_ms < 50:
                ping_color = "#00CC00"
            elif ping_ms < 100:
                ping_color = "#CCCC00"
            else:
                ping_color = "#CC0000"
        self.ping_lbl.configure(text=ping_text, text_color=ping_color)

    def update_state(self, is_selected, is_active):
        bg_color = ("#F2DEDE", "#1A1313") if is_selected else ("gray85", "#121212")
        border_color = ("#D9534F", "#D9534F") if is_selected else ("gray70", "#222222")
        bw = 2 if is_selected else 2
        self.configure(fg_color=bg_color, border_color=border_color, border_width=bw)
        
        if is_active:
            if not hasattr(self, 'badge_frame'):
                self.badge_frame = ctk.CTkFrame(self, fg_color="#C9302C", corner_radius=9, width=40, height=20)
                self.badge_frame.place(relx=0.96, rely=0.04, anchor="ne")
                self.badge_frame.pack_propagate(False)
                
                badge_lbl = ctk.CTkLabel(self.badge_frame, text="SET", font=ctk.CTkFont(size=10, weight="bold"), text_color="white")
                badge_lbl.place(relx=0.5, rely=0.5, anchor="center")
                
                badge_lbl.bind("<Button-1>", self.on_click)
                self.badge_frame.bind("<Button-1>", self.on_click)
        else:
            if hasattr(self, 'badge_frame'):
                self.badge_frame.destroy()
                del self.badge_frame

    def toggle_flip(self):
        if self.is_flipped:
            self.flip_to_front()
        else:
            self.flip_to_back()

    def flip_to_back(self):
        if self.is_flipped: return
        self.is_flipped = True
        self.animate_slide(97.5, -97.5, 292.5, 97.5)
        
    def flip_to_front(self):
        if not self.is_flipped: return
        self.is_flipped = False
        self.animate_slide(-97.5, 97.5, 97.5, 292.5)
        
    def animate_slide(self, front_start, front_end, back_start, back_end):
        steps = 15
        delay = 10
        front_step = (front_end - front_start) / steps
        back_step = (back_end - back_start) / steps
        
        def step(current_step):
            if current_step <= steps:
                f_x = front_start + (front_step * current_step)
                b_x = back_start + (back_step * current_step)
                self.front_frame.place_configure(x=f_x)
                self.back_frame.place_configure(x=b_x)
                self.after(delay, step, current_step + 1)
            else:
                self.front_frame.place_configure(x=front_end)
                self.back_frame.place_configure(x=back_end)
                
        step(1)

    def on_click(self, event):
        if self.is_flipped:
            self.flip_to_front()
        else:
            self.command(self.profile['id'])


class CipherDNSApp(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=("#F5F5F5", "#080808")) 

        self.title("CipherDNS")
        self.geometry("900x680") 
        self.resizable(False, False)

        self.base_profiles = load_profiles()
        self.app_settings = load_settings()
        self.adapters = get_network_adapters()
        
        self.profiles = self.get_all_profiles()
        
        self.selected_profile_id = self.profiles[0]['id']
        self.active_profile_id = None 
        
        self.pings = {p['id']: None for p in self.profiles}
        self.fastest_profile_id = None
        
        self.last_seen_network = None
        self.monitoring = True
        
        self.load_images()
        self.build_ui()
        
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.setup_tray()
        
        self.after(100, self.startup_tasks)
        
        threading.Thread(target=self._network_monitor_loop, daemon=True).start()

    def get_all_profiles(self):
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
            "is_configured": is_configured
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
        self.tray_icon.notify("CipherDNS is still protecting you in the background.", "CipherDNS Minimized")

    def setup_tray(self):
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        app_icon_png = os.path.join(assets_dir, "app_icon.png")
        
        try:
            image = Image.open(app_icon_png)
        except Exception:
            image = Image.new('RGB', (64, 64), color='red')
            
        def on_show(icon, item):
            self.after(0, self.deiconify)
            self.after(0, self.lift)
            
        def on_quit(icon, item):
            self.monitoring = False
            icon.stop()
            self.after(0, self.destroy)
            
        def on_set_profile(icon, clicked_item):
            profile = next((p for p in self.profiles if p['name'] == clicked_item.text), None)
            if profile:
                self.after(0, lambda: self._apply_dns_from_tray(profile))

        menu_items = [
            item("Show CipherDNS", on_show, default=True),
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
        if not hasattr(self, 'tray_icon'): return
        
        def on_show(icon, item):
            self.after(0, self.deiconify)
            self.after(0, self.lift)
            
        def on_quit(icon, item):
            self.monitoring = False
            icon.stop()
            self.after(0, self.destroy)
            
        def on_set_profile(icon, clicked_item):
            profile = next((p for p in self.profiles if p['name'] == clicked_item.text), None)
            if profile:
                self.after(0, lambda: self._apply_dns_from_tray(profile))

        menu_items = [
            item("Show CipherDNS", on_show, default=True),
            pystray.Menu.SEPARATOR
        ]
        
        for p in self.profiles:
            menu_items.append(item(p['name'], on_set_profile))
            
        menu_items.extend([
            pystray.Menu.SEPARATOR,
            item("Quit", on_quit)
        ])
        
        self.tray_icon.menu = pystray.Menu(*menu_items)

    def _apply_dns_from_tray(self, profile):
        if profile['id'] == 'nextdns' and not profile.get('is_configured'):
            self.tray_icon.notify("NextDNS is not configured. Please open the app.", "CipherDNS Error")
            return
            
        adapter = self.adapter_var.get()
        if adapter == "No active adapter":
            self.tray_icon.notify("Error: No network adapter selected!", "CipherDNS Error")
            return
            
        strict = self.fallback_var.get()
        success, msg = apply_dns(adapter, profile, strict_doh=strict)
        
        if success:
            self.tray_icon.notify(f"Successfully applied: {profile['name']}", "CipherDNS")
            self.selected_profile_id = profile['id']
            self.update_active_profile()
            self._save_network_memory(profile['id'])
        else:
            self.tray_icon.notify(f"Failed to apply: {profile['name']}", "CipherDNS Error")

    def startup_tasks(self):
        self.update_active_profile()
        self.start_speed_test()

    def start_speed_test(self):
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
        self.status_label.configure(text="Ready.", text_color="gray")
        self.render_cards()

    def load_images(self):
        self.icons = {}
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        
        app_icon_ico = os.path.join(assets_dir, "app_icon.ico")
        app_icon_png = os.path.join(assets_dir, "app_icon.png")
        
        if not os.path.exists(app_icon_ico) and os.path.exists(app_icon_png):
            try:
                img = Image.open(app_icon_png)
                img.save(app_icon_ico, format="ICO", sizes=[(72, 72)])
            except Exception:
                pass
                
        if os.path.exists(app_icon_ico):
            self.iconbitmap(app_icon_ico)

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
        self.header = ctk.CTkLabel(self, text="🛡️ CipherDNS", font=ctk.CTkFont(size=28, weight="bold"), text_color="#D9534F")
        self.header.pack(pady=(20, 0))

        self.subtitle = ctk.CTkLabel(self, text="Modern DNS over HTTPS (DoH) Manager", font=ctk.CTkFont(size=14), text_color="gray")
        self.subtitle.pack(pady=(0, 15))

        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=10)
        
        self.left_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.left_frame.pack(side="left", anchor="n")
        
        ctk.CTkLabel(self.left_frame, text="Network Adapter:", font=ctk.CTkFont(weight="bold", size=13)).pack(anchor="w", pady=(0, 5))
        self.adapter_var = ctk.StringVar(value=self.adapters[0] if self.adapters else "No active adapter")
        self.adapter_menu = ctk.CTkOptionMenu(self.left_frame, values=self.adapters, variable=self.adapter_var, width=200, 
                                              fg_color="#1A1A1A", button_color="#C9302C", button_hover_color="#AC2925", command=self.on_adapter_change)
        self.adapter_menu.pack(anchor="w")

        self.right_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.right_frame.pack(side="right", anchor="n")
        
        self.fallback_var = ctk.BooleanVar(value=False)
        self.fallback_switch = ctk.CTkSwitch(self.right_frame, text="Strict DoH ", variable=self.fallback_var, progress_color="#C9302C")
        self.fallback_switch.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.info_btn = ctk.CTkButton(self.right_frame, text="?", width=26, height=26, corner_radius=13, 
                                      fg_color="#333333", hover_color="#C9302C", font=ctk.CTkFont(weight="bold"), command=self.show_doh_info)
        self.info_btn.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=(0, 10))

        self.auto_switch_var = ctk.BooleanVar(value=self.app_settings.get("auto_switch", False))
        self.auto_switch_chk = ctk.CTkSwitch(self.right_frame, text="Auto-Switch (Smart Memory)", variable=self.auto_switch_var, progress_color="#00CC00", command=self.on_autoswitch_toggle)
        self.auto_switch_chk.grid(row=1, column=0, columnspan=2, sticky="w")
        
        self.cards_title = ctk.CTkLabel(self, text="Available DNS Providers", font=ctk.CTkFont(weight="bold", size=15))
        self.cards_title.pack(anchor="w", padx=25, pady=(10, 0))

        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="both", expand=True, padx=20, pady=0)

        self.card_widgets = []
        
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.pack(fill="x", padx=20, pady=10)
        self.status_label = ctk.CTkLabel(self.bottom_frame, text="Loading...", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_label.pack(side="left", padx=10)
        self.apply_btn = ctk.CTkButton(self.bottom_frame, text="Apply", command=self.apply_dns_action, height=45, width=140, 
                                       font=ctk.CTkFont(weight="bold", size=15), fg_color="#C9302C", hover_color="#AC2925")
        self.apply_btn.pack(side="right")
        
        self.security_btn = ctk.CTkButton(self.bottom_frame, text="🛡️ Security Check", command=self.open_security_check, height=45, width=160, 
                                       font=ctk.CTkFont(weight="bold", size=14), fg_color="#333333", hover_color="#555555")
        self.security_btn.pack(side="right", padx=(0, 10))

        self.render_cards()

    def _save_network_memory(self, profile_id):
        net_name = get_current_network_name()
        if net_name:
            if "network_memory" not in self.app_settings:
                self.app_settings["network_memory"] = {}
            self.app_settings["network_memory"][net_name] = profile_id
            save_settings(self.app_settings)

    def _network_monitor_loop(self):
        while self.monitoring:
            if self.app_settings.get("auto_switch", False):
                current_net = get_current_network_name()
                if current_net and current_net != self.last_seen_network:
                    self.last_seen_network = current_net
                    memory = self.app_settings.get("network_memory", {})
                    
                    if current_net in memory:
                        target_id = memory[current_net]
                        if self.active_profile_id != target_id:
                            self.after(0, lambda tid=target_id, net=current_net: self._auto_apply_dns(tid, net))
            time.sleep(10)

    def _auto_apply_dns(self, target_id, network_name):
        adapter = self.adapter_var.get()
        if adapter == "No active adapter": return
        
        profile = next((p for p in self.profiles if p['id'] == target_id), None)
        if not profile: return
        
        if profile['id'] == 'nextdns' and not profile.get('is_configured'):
            return
            
        success, msg = apply_dns(adapter, profile, strict_doh=self.fallback_var.get())
        if success:
            self.tray_icon.notify(f"Auto-switched to {profile['name']} for network '{network_name}'", "CipherDNS Auto-Switch")
            self.selected_profile_id = profile['id']
            self.update_active_profile()

    def update_active_profile(self):
        adapter = self.adapter_var.get()
        if adapter and adapter != "No active adapter":
            self.active_profile_id = get_active_profile(adapter, self.profiles)
        else:
            self.active_profile_id = None
            
        if "tests" not in self.status_label.cget("text"):
            self.status_label.configure(text="Ready.", text_color="gray")
        self.render_cards()

    def on_adapter_change(self, value):
        self.update_active_profile()

    def render_cards(self, force_rebuild=False):
        if not force_rebuild and len(self.card_widgets) == len(self.profiles) + 1:
            for card in self.card_widgets:
                if getattr(card, 'is_add_card', False): continue
                
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
            
            card = ProfileCard(self.cards_frame, profile, icon, self.select_profile, is_selected, is_active, ping_val, is_fastest, on_configure=on_configure, on_delete=on_delete, has_info=has_info)
            
            card.grid(row=row, column=col, padx=8, pady=8)
            self.card_widgets.append(card)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
                
        # Saját DNS hozzáadása gomb (+)
        add_card = ctk.CTkFrame(self.cards_frame, corner_radius=10, width=195, height=175, fg_color="transparent", border_width=2, border_color="gray30")
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
        
        add_card.grid(row=row, column=col, padx=8, pady=8)
        self.card_widgets.append(add_card)
            
    def select_profile(self, profile_id):
        self.selected_profile_id = profile_id
        self.render_cards()

    def configure_nextdns(self, profile_id):
        win = ctk.CTkToplevel(self)
        win.title("Configure NextDNS")
        win.geometry("350x220")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
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
        
        def save():
            val = id_entry.get().strip()
            if val:
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
        
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
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
        
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            info_win.after(200, lambda: info_win.iconbitmap(app_icon_path))
            
        info_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 440) // 2
        y = self.winfo_y() + (self.winfo_height() - 310) // 2
        info_win.geometry(f"+{x}+{y}")
        
        title = ctk.CTkLabel(info_win, text="Strict DoH (Encrypted Only)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#D9534F")
        title.pack(pady=(20, 10))
        
        intro = ctk.CTkLabel(info_win, text="Strict DoH ensures that your computer communicates with the DNS server EXCLUSIVELY over an encrypted (HTTPS) connection.", justify="left", wraplength=400, text_color=("gray20", "gray80"), font=ctk.CTkFont(size=12))
        intro.pack(padx=20, pady=(0, 15))
        
        strict_title = ctk.CTkLabel(info_win, text="ENABLED (Strict Mode):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00FF00")
        strict_title.pack(padx=20, anchor="w")
        strict_desc = ctk.CTkLabel(info_win, text="Maximum security. No compromises. If the network doesn't support it, you lose internet access.", justify="left", wraplength=400, text_color=("gray20", "gray80"), font=ctk.CTkFont(size=12))
        strict_desc.pack(padx=20, anchor="w", pady=(0, 15))

        fallback_title = ctk.CTkLabel(info_win, text="DISABLED (Fallback / Default):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF9900")
        fallback_title.pack(padx=20, anchor="w")
        fallback_desc = ctk.CTkLabel(info_win, text="More flexible. Falls back to standard, unencrypted DNS in case of connection failure.", justify="left", wraplength=400, text_color=("gray20", "gray80"), font=ctk.CTkFont(size=12))
        fallback_desc.pack(padx=20, anchor="w")
        
        btn = ctk.CTkButton(info_win, text="Got it", command=info_win.destroy, width=100, fg_color="#C9302C", hover_color="#AC2925")
        btn.pack(pady=15)

    def open_security_check(self):
        import webbrowser
        
        win = ctk.CTkToplevel(self)
        win.title("Security Check")
        win.geometry("520x350")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        app_icon_path = os.path.join(assets_dir, "app_icon.ico")
        if os.path.exists(app_icon_path):
            win.after(200, lambda: win.iconbitmap(app_icon_path))
            
        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 350) // 2
        win.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(win, text="DNS Security Check", font=ctk.CTkFont(size=18, weight="bold"), text_color="#D9534F").pack(pady=(20, 10))
        
        status_frame = ctk.CTkFrame(win, fg_color="#121212", corner_radius=10)
        status_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        adapter = self.adapter_var.get()
        active_prof = None
        if adapter and adapter != "No active adapter":
            prof_id = get_active_profile(adapter, self.profiles)
            active_prof = next((p for p in self.profiles if p['id'] == prof_id), None)
            
        if not active_prof or active_prof['id'] == 'clear':
            status_text = "INSECURE (Standard DNS)"
            status_color = "#D9534F"
            desc = "Your DNS queries are currently unencrypted and visible to your ISP. Anyone on your local network can see which websites you visit."
        else:
            status_text = "SECURE (Encrypted DoH)"
            status_color = "#00FF00"
            desc = f"Your DNS queries are encrypted using {active_prof['name']}. Your ISP cannot intercept or read your DNS traffic."
            
        ctk.CTkLabel(status_frame, text="Local OS Configuration:", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray70").pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(status_frame, text=status_text, font=ctk.CTkFont(size=18, weight="bold"), text_color=status_color).pack(anchor="w", padx=20, pady=0)
        ctk.CTkLabel(status_frame, text=desc, font=ctk.CTkFont(size=12), text_color="gray80", wraplength=440, justify="left").pack(anchor="w", padx=20, pady=(5, 20))
        
        ctk.CTkLabel(win, text="To perform a deep diagnostic test of your network routing and verify there are no hidden leaks, please run an external web test.", 
                     font=ctk.CTkFont(size=12), text_color="gray50", wraplength=480).pack(pady=(0, 15))
                     
        btn = ctk.CTkButton(win, text="Run Advanced Leak Test", command=lambda: webbrowser.open("https://dnsleaktest.com"), 
                            height=40, width=220, fg_color="#C9302C", hover_color="#AC2925", font=ctk.CTkFont(weight="bold"))
        btn.pack(pady=(0, 20))

    def apply_dns_action(self):
        adapter = self.adapter_var.get()
        if adapter == "No active adapter":
            self.status_label.configure(text="Error: No adapter selected!", text_color="#D9534F")
            return

        profile = next((p for p in self.profiles if p['id'] == self.selected_profile_id), None)
        if not profile: return
        
        if profile['id'] == 'nextdns' and not profile.get('is_configured'):
            self.status_label.configure(text="NextDNS ID not configured!", text_color="#D9534F")
            self.configure_nextdns(profile['id'])
            return
            
        strict = self.fallback_var.get()

        self.status_label.configure(text=f"Applying: {profile['name']}...", text_color="yellow")
        self.apply_btn.configure(state="disabled")
        self.update()

        success, msg = apply_dns(adapter, profile, strict_doh=strict)
        
        self.apply_btn.configure(state="normal")
        if success:
            self.status_label.configure(text=f"✅ Successfully applied: {profile['name']}", text_color="#00FF00")
            self.update_active_profile()
            self._save_network_memory(profile['id'])
        else:
            self.status_label.configure(text=f"❌ An error occurred!", text_color="#D9534F")
            print(msg)

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
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if not is_admin():
        run_as_admin()
        
    app = CipherDNSApp()
    app.mainloop()

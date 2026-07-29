import customtkinter as ctk

class ProfileCard(ctk.CTkFrame):
    def __init__(self, master, profile, icon_img, command, is_selected=False, is_active=False, ping_ms=None, is_fastest=False, on_configure=None, on_delete=None, has_info=False):
        bg_color = ("#F2DEDE", "#1A1313") if is_selected else ("gray85", "#121212")
        border_color = ("#D9534F", "#D9534F") if is_selected else ("gray70", "#222222")
        bw = 2 if is_selected else 2
        
        super().__init__(master, corner_radius=10, 
                         width=215, height=180, 
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
        self.front_frame = ctk.CTkFrame(self, fg_color="transparent", width=207, height=172)
        self.front_frame.place(x=107.5, y=90, anchor="center")
        self.front_frame.pack_propagate(False)
        self.front_frame.bind("<Button-1>", self.on_click)
        
        if icon_img:
            self.icon = ctk.CTkLabel(self.front_frame, text="", image=icon_img)
        else:
            letter = profile['name'][0].upper() if profile.get('name') else "?"
            self.icon = ctk.CTkLabel(self.front_frame, text=letter, font=ctk.CTkFont(size=36, weight="bold"), text_color="gray50")
        
        self.icon.pack(pady=(10, 4))
        self.icon.bind("<Button-1>", self.on_click)
            
        self.name_label = ctk.CTkLabel(self.front_frame, text=profile['name'], font=ctk.CTkFont(size=13, weight="bold"), justify="center", wraplength=198)
        self.name_label.pack(padx=4, fill="x")
        self.name_label.bind("<Button-1>", self.on_click)
        
        # Description text constrained so it never overflows into bottom icons
        self.desc_label = ctk.CTkLabel(self.front_frame, text=profile['description'], font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"), justify="center", wraplength=198, height=42)
        self.desc_label.pack(padx=4, pady=(2, 0), fill="x", expand=False)
        self.desc_label.bind("<Button-1>", self.on_click)

        # --- HÁTSÓ LAP (BACK) ---
        self.back_frame = ctk.CTkFrame(self, fg_color="transparent", width=207, height=172)
        # Rejtve (jobbra kitolva) indul
        self.back_frame.place(x=322.5, y=90, anchor="center")
        self.back_frame.pack_propagate(False)
        self.back_frame.bind("<Button-1>", self.on_click)
        
        ipv4_list = profile.get('ipv4', [])
        ipv4_str = ipv4_list[0] if ipv4_list else "None"
        
        ipv6_list = profile.get('ipv6', [])
        ipv6_str = ipv6_list[0] if ipv6_list else "None"
        
        raw_doh = profile.get('doh') or profile.get('doh_template') or "None"
        doh_str = raw_doh.replace("https://", "").split("/")[0] if raw_doh != "None" else "None"
        
        inner_back = ctk.CTkFrame(self.back_frame, fg_color="transparent")
        inner_back.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.94)
        

        ctk.CTkLabel(inner_back, text="IPv4", font=ctk.CTkFont(size=10, weight="bold"), text_color="#D9534F", height=14, anchor="w").pack(anchor="w", padx=8)
        lbl_v4 = ctk.CTkLabel(inner_back, text=ipv4_str, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray90", height=16, anchor="w")
        lbl_v4.pack(anchor="w", padx=8, pady=(0, 4))
        
        ctk.CTkLabel(inner_back, text="IPv6", font=ctk.CTkFont(size=10, weight="bold"), text_color="#D9534F", height=14, anchor="w").pack(anchor="w", padx=8)
        lbl_v6 = ctk.CTkLabel(inner_back, text=ipv6_str, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray90", height=16, anchor="w")
        lbl_v6.pack(anchor="w", padx=8, pady=(0, 4))
        
        ctk.CTkLabel(inner_back, text="DoH Hostname", font=ctk.CTkFont(size=10, weight="bold"), text_color="#D9534F", height=14, anchor="w").pack(anchor="w", padx=8)
        lbl_doh = ctk.CTkLabel(inner_back, text=doh_str, font=ctk.CTkFont(size=11), text_color="gray80", height=16, anchor="w")
        lbl_doh.pack(anchor="w", padx=8)
        
        for w in inner_back.winfo_children():
            w.bind("<Button-1>", self.on_click)
        inner_back.bind("<Button-1>", self.on_click)

        # --- FELÜLRÉTEGEZETT ELEMEK (Gombok, Badgek) ---
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
            self.ping_lbl.place(relx=0.04, rely=0.04, anchor="nw")
            self.ping_lbl.bind("<Button-1>", self.on_click)
            
        features = profile.get('features', [])
        if features:
            self.feat_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.feat_frame.place(x=10, y=150)
            
            for feat in features:
                if feat == "malware": emoji, color = "⛨", "#FF6B6B"
                elif feat == "ads": emoji, color = "⊘", "#FDCB6E"
                elif feat == "trackers": emoji, color = "◉", "#74B9FF"
                elif feat == "family": emoji, color = "♥", "#55EFC4"
                else: continue
                
                lbl = ctk.CTkLabel(self.feat_frame, text=emoji, font=ctk.CTkFont(size=13, weight="bold"), text_color=color)
                lbl.pack(side="left", padx=(0, 2))
                lbl.bind("<Button-1>", self.on_click)
                
            self.feat_frame.bind("<Button-1>", self.on_click)

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
        self.animate_slide(107.5, -107.5, 322.5, 107.5)
        
    def flip_to_front(self):
        if not self.is_flipped: return
        self.is_flipped = False
        self.animate_slide(-107.5, 107.5, 107.5, 322.5)
        
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

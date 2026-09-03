import tkinter as tk
import customtkinter as ctk
import math
from sim_model import MyModel

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SimulationApp(ctk.CTk):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.is_running = False
        self.steps_remaining = 0
        self.selected_nodes = []
        self.selected_cell_coords = None

        self.title("Simulación de Red Móvil de Nodos Distribuidos")
        self.geometry("1100x640")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._crear_panel_izquierdo()
        self._crear_panel_derecho()
        self.actualizar_interfaz()

    def _crear_panel_izquierdo(self):
        self.panel_izq = ctk.CTkScrollableFrame(self, width=380, corner_radius=10)
        self.panel_izq.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        lbl_titulo = ctk.CTkLabel(self.panel_izq, text="Red Móvil ", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(padx=15, pady=(12, 4))
        lbl_sub = ctk.CTkLabel(self.panel_izq, text="Ejecución por Ticks (1 Acción por Tick)", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        lbl_sub.pack(padx=15, pady=(0, 10))

        frame_ctrl = ctk.CTkFrame(self.panel_izq, corner_radius=8)
        frame_ctrl.pack(fill="x", padx=15, pady=5)
        lbl_sec_ctrl = ctk.CTkLabel(frame_ctrl, text="Controles", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_sec_ctrl.pack(pady=(8, 4))

        self.btn_step_1 = ctk.CTkButton(frame_ctrl, text="Paso a Paso (+1 Tick)", fg_color="#2563EB", hover_color="#1D4ED8", command=self.ejecutar_paso_unico)
        self.btn_step_1.pack(fill="x", padx=12, pady=4)

        frame_until = ctk.CTkFrame(frame_ctrl, fg_color="transparent")
        frame_until.pack(fill="x", padx=12, pady=4)
        lbl_pasos = ctk.CTkLabel(frame_until, text="Pasos (X):", font=ctk.CTkFont(size=12))
        lbl_pasos.pack(side="left", padx=(0, 4))
        self.entry_pasos = ctk.CTkEntry(frame_until, width=65)
        self.entry_pasos.insert(0, "10")
        self.entry_pasos.pack(side="left", padx=4)

        self.btn_until_x = ctk.CTkButton(frame_until, text="Ejecutar x pasos", fg_color="#059669", hover_color="#047857", command=self.ejecutar_hasta_x_pasos)
        self.btn_until_x.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.btn_play_pause = ctk.CTkButton(frame_ctrl, text="Continuo", fg_color="#D97706", hover_color="#B45309", command=self.toggle_play_pause)
        self.btn_play_pause.pack(fill="x", padx=12, pady=4)
        self.btn_reset = ctk.CTkButton(frame_ctrl, text="Reiniciar", fg_color="#4B5563", hover_color="#374151", command=self.reiniciar_simulacion)
        self.btn_reset.pack(fill="x", padx=12, pady=(4, 8))

        # PARÁMETROS Y CONFIGURACIÓN INICIAL
        frame_param = ctk.CTkFrame(self.panel_izq, corner_radius=8)
        frame_param.pack(fill="x", padx=15, pady=5)
        
        lbl_sec_params = ctk.CTkLabel(frame_param, text="Configuración (Aplicar al Reiniciar)", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_sec_params.pack(pady=(6, 4))

        frame_nodos = ctk.CTkFrame(frame_param, fg_color="transparent")
        frame_nodos.pack(fill="x", padx=12, pady=1)
        ctk.CTkLabel(frame_nodos, text="Cant. Nodos:").pack(side="left")
        self.entry_nodos = ctk.CTkEntry(frame_nodos, width=60, height=24)
        self.entry_nodos.insert(0, str(self.model.n_agents))
        self.entry_nodos.pack(side="right")

        frame_grilla = ctk.CTkFrame(frame_param, fg_color="transparent")
        frame_grilla.pack(fill="x", padx=12, pady=1)
        ctk.CTkLabel(frame_grilla, text="Grilla (L x L):").pack(side="left")
        self.entry_grilla = ctk.CTkEntry(frame_grilla, width=60, height=24)
        self.entry_grilla.insert(0, str(self.model.grid.width))
        self.entry_grilla.pack(side="right")

        frame_radio = ctk.CTkFrame(frame_param, fg_color="transparent")
        frame_radio.pack(fill="x", padx=12, pady=1)
        ctk.CTkLabel(frame_radio, text="Radio Vecinos:").pack(side="left")
        self.entry_radio = ctk.CTkEntry(frame_radio, width=60, height=24)
        self.entry_radio.insert(0, str(self.model.radio_vecinos))
        self.entry_radio.pack(side="right")

        self.lbl_tasa_val = ctk.CTkLabel(frame_param, text=f"Tasa de Generación: {int(self.model.tasa_generacion * 100)}%", font=ctk.CTkFont(size=12))
        self.lbl_tasa_val.pack(pady=(6, 2))
        self.slider_tasa = ctk.CTkSlider(frame_param, from_=0.01, to=0.5, number_of_steps=50, command=self.cambiar_tasa_generacion)
        self.slider_tasa.set(self.model.tasa_generacion)
        self.slider_tasa.pack(fill="x", padx=12, pady=(0, 8))

        # ESTADÍSTICAS
        frame_stats = ctk.CTkFrame(self.panel_izq, corner_radius=8)
        frame_stats.pack(fill="x", padx=15, pady=5)
        lbl_sec_stats = ctk.CTkLabel(frame_stats, text="Métricas Generales", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_sec_stats.pack(pady=(6, 4))
        self.lbl_stat_step = ctk.CTkLabel(frame_stats, text="Paso (Tick): 0", anchor="w")
        self.lbl_stat_step.pack(fill="x", padx=12, pady=1)
        self.lbl_stat_gen = ctk.CTkLabel(frame_stats, text="Paquetes Generados: 0", anchor="w")
        self.lbl_stat_gen.pack(fill="x", padx=12, pady=1)
        self.lbl_stat_ent = ctk.CTkLabel(frame_stats, text="Paquetes Entregados: 0", anchor="w", text_color="#10B981")
        self.lbl_stat_ent.pack(fill="x", padx=12, pady=1)
        self.lbl_stat_perd = ctk.CTkLabel(frame_stats, text="Paquetes Perdidos: 0", anchor="w", text_color="#EF4444")
        self.lbl_stat_perd.pack(fill="x", padx=12, pady=1)
        self.lbl_stat_cong = ctk.CTkLabel(frame_stats, text="Nodos Congestionados: 0", anchor="w", text_color="#F59E0B")
        self.lbl_stat_cong.pack(fill="x", padx=12, pady=(1, 6))

        # INSPECTOR
        self.frame_inspect = ctk.CTkFrame(self.panel_izq, corner_radius=8, fg_color="#1E293B")
        self.frame_inspect.pack(fill="x", padx=15, pady=5)
        lbl_insp_title = ctk.CTkLabel(self.frame_inspect, text="🔍 Inspector de Nodo", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_insp_title.pack(pady=(6, 2))
        self.lbl_inspect_info = ctk.CTkLabel(self.frame_inspect, text="Ningún nodo seleccionado.", font=ctk.CTkFont(size=11), justify="left", anchor="w")
        self.lbl_inspect_info.pack(fill="x", padx=10, pady=(0, 6))
        self.lbl_node_log_title = ctk.CTkLabel(self.frame_inspect, text="Historial de Acciones", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_node_log_title.pack(anchor="w", padx=10, pady=(5, 0))
        self.txt_node_log = ctk.CTkTextbox(self.frame_inspect, height=80, font=ctk.CTkFont(family="Consolas", size=10), fg_color="#0F172A")
        self.txt_node_log.pack(fill="x", padx=10, pady=(2, 10))

        # CONSOLA LOG
        self.txt_log = ctk.CTkTextbox(self.panel_izq, height=110, font=ctk.CTkFont(family="Consolas", size=10))
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(5, 12))

    def _crear_panel_derecho(self):
        self.panel_der = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.panel_der.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        self.lbl_grid_title = ctk.CTkLabel(
            self.panel_der, 
            text=f"Grilla Dinámica de Nodos Móviles ({self.model.grid.width}x{self.model.grid.height} - {self.model.n_agents} Nodos)", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_grid_title.pack(pady=8)

        self.canvas_size = 700
        self.canvas = tk.Canvas(self.panel_der, width=self.canvas_size, height=self.canvas_size, bg="#0F172A", highlightthickness=0)
        self.canvas.pack(padx=15, pady=5)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        frame_leyenda = ctk.CTkFrame(self.panel_der, fg_color="transparent")
        frame_leyenda.pack(fill="x", padx=15, pady=(5, 8))
        items_leyenda = [
            ("🔵 Normal", "#2563EB"),
            ("🟣 Generando", "#9333EA"),
            ("🟢 Enrutando", "#059669"),
            ("🟠 Cola 50%", "#D97706"),
            ("🔴 Congestionado", "#DC2626"),
            ("⚡ Enlace Activo", "#F59E0B")
        ]
        for texto, color in items_leyenda:
            lbl = ctk.CTkLabel(frame_leyenda, text=texto, text_color=color, font=ctk.CTkFont(size=11, weight="bold"))
            lbl.pack(side="left", expand=True)

    def ejecutar_paso_unico(self):
        self.model.step()
        self.actualizar_interfaz()

    def ejecutar_hasta_x_pasos(self):
        try:
            val = int(self.entry_pasos.get())
            if val > 0:
                self.steps_remaining = val
                self.ejecutar_bucle_pasos()
        except ValueError:
            self.model.registrar_log("Error: Ingrese un número entero en Pasos (X).")
            self.actualizar_interfaz()

    def ejecutar_bucle_pasos(self):
        if self.steps_remaining > 0:
            self.model.step()
            self.steps_remaining -= 1
            self.actualizar_interfaz()
            self.after(600, self.ejecutar_bucle_pasos)

    def toggle_play_pause(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_play_pause.configure(text="⏸ Pausar Simulación", fg_color="#DC2626")
            self.ejecutar_continuo()
        else:
            self.btn_play_pause.configure(text="🔄 Continuo (Play/Pause)", fg_color="#D97706")

    def ejecutar_continuo(self):
        if self.is_running:
            self.model.step()
            self.actualizar_interfaz()
            self.after(600, self.ejecutar_continuo)

    def cambiar_tasa_generacion(self, value):
        self.model.tasa_generacion = float(value)
        self.lbl_tasa_val.configure(text=f"Tasa de Generación: {int(self.model.tasa_generacion * 100)}%")

    def reiniciar_simulacion(self):
        self.is_running = False
        self.steps_remaining = 0
        self.selected_nodes = []
        self.selected_cell_coords = None
        self.btn_play_pause.configure(text="🔄 Continuo (Play/Pause)", fg_color="#D97706")
        
        try:
            n_agents = int(self.entry_nodos.get())
            grid_size = int(self.entry_grilla.get())
            radio = int(self.entry_radio.get())
        except ValueError:
            n_agents = 50
            grid_size = 20
            radio = 1
            
        self.model = MyModel(n_agents=n_agents, width=grid_size, height=grid_size, queue_max=5, tasa_generacion=self.slider_tasa.get(), radio_vecinos=radio)
        self.lbl_grid_title.configure(text=f"Grilla Dinámica de Nodos Móviles ({grid_size}x{grid_size} - {n_agents} Nodos)")
        self.actualizar_interfaz()

    def on_canvas_click(self, event):
        grid_w = self.model.grid.width
        cell_size = self.canvas_size / grid_w
        gx = int(event.x // cell_size)
        gy = int(event.y // cell_size)

        if gx < 0 or gx >= grid_w or gy < 0 or gy >= self.model.grid.height:
            return

        agentes_en_celda = [a for a in self.model.agents if a.cell.coordinate == (gx, gy)]
        if agentes_en_celda:
            self.selected_nodes = agentes_en_celda
            self.selected_cell_coords = (gx, gy)
        else:
            self.selected_nodes = []
            self.selected_cell_coords = None
        self.actualizar_interfaz()

    def actualizar_interfaz(self):
        self.lbl_stat_step.configure(text=f"Paso (Tick): {self.model.current_step}")
        self.lbl_stat_gen.configure(text=f"Paquetes Generados: {self.model.total_generados}")
        self.lbl_stat_ent.configure(text=f"Paquetes Entregados: {self.model.total_entregados}")
        self.lbl_stat_perd.configure(text=f"Paquetes Perdidos: {self.model.total_perdidos}")

        num_cong = sum(1 for a in self.model.agents if len(a.queue) >= a.queue_max)
        self.lbl_stat_cong.configure(text=f"Nodos Congestionados: {num_cong}")

        if self.selected_nodes and self.selected_cell_coords:
            gx, gy = self.selected_cell_coords
            info = f"📌 Celda ({gx}, {gy}) - {len(self.selected_nodes)} Nodo(s) en esta casilla:\n"
            for sn in self.selected_nodes:
                info += f"───────────────\n"
                info += f"🔹 Nodo N{sn.unique_id}\n"
                info += f"  • Estado: {sn.state} | Cola: {len(sn.queue)}/{sn.queue_max}\n"
                info += f"  • Vecinos: {[f'N{v.unique_id}' for v in sn.vecinos]}\n"
                info += f"  • Paquetes enviados: {sn.packets_sent} | Perdidos: {sn.packets_lost}\n"
            self.lbl_inspect_info.configure(text=info, text_color="#38BDF8")

            self.txt_node_log.delete("1.0", "end")
            for sn in self.selected_nodes:
                self.txt_node_log.insert("end", f"--- Log N{sn.unique_id} ---\n")
                for accion in sn.historial_acciones:
                    self.txt_node_log.insert("end", accion + "\n")
            self.txt_node_log.see("end")
        else:
            self.lbl_inspect_info.configure(text="Haz clic en cualquier celda para inspeccionar los nodos.", text_color="gray")
            self.txt_node_log.delete("1.0", "end")

        self.txt_log.delete("1.0", "end")
        for log in self.model.logs[-15:]:
            self.txt_log.insert("end", log + "\n")
        self.txt_log.see("end")
        self.dibujar_grilla()

    def dibujar_grilla(self):
        self.canvas.delete("all")
        grid_w = self.model.grid.width
        grid_h = self.model.grid.height
        cell_size = self.canvas_size / grid_w

        for i in range(grid_w):
            for j in range(grid_h):
                x1, y1 = i * cell_size, j * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                bg_color = "#1E293B" if (i + j) % 2 == 0 else "#0F172A"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="#334155", width=1)

        if self.selected_cell_coords:
            sx, sy = self.selected_cell_coords
            self.canvas.create_rectangle(sx * cell_size, sy * cell_size, (sx + 1) * cell_size, (sy + 1) * cell_size, outline="#38BDF8", width=3)

        cell_agents = {}
        for agent in self.model.agents:
            pos = agent.cell.coordinate
            if pos not in cell_agents:
                cell_agents[pos] = []
            cell_agents[pos].append(agent)

        agent_screen_pos = {}
        for pos, ag_list in cell_agents.items():
            count = len(ag_list)
            cell_cx = (pos[0] + 0.5) * cell_size
            cell_cy = (pos[1] + 0.5) * cell_size
            for idx, agent in enumerate(ag_list):
                if count == 1:
                    ax, ay, radius = cell_cx, cell_cy, 15
                elif count == 2:
                    offset = 14
                    ax = cell_cx - offset if idx == 0 else cell_cx + offset
                    ay, radius = cell_cy, 10
                elif count == 3:
                    offsets = [(-14, -12), (14, -12), (0, 14)]
                    ax = cell_cx + offsets[idx][0]
                    ay = cell_cy + offsets[idx][1]
                    radius = 8
                else:
                    offsets = [(-14, -14), (14, -14), (-14, 14), (14, 14)]
                    o = offsets[idx % 4]
                    ax, ay = cell_cx + o[0], cell_cy + o[1]
                    radius = 5
                agent_screen_pos[agent] = (ax, ay, radius)

        for agent, (ax, ay, radius) in agent_screen_pos.items():
            q_ratio = len(agent.queue) / agent.queue_max
            if q_ratio >= 1.0:
                color = "#DC2626"
            elif agent.state == "Generando":
                color = "#9333EA"
            elif q_ratio >= 0.5:
                color = "#D97706"
            elif agent.state == "Enrutando":
                color = "#059669"
            else:
                color = "#2563EB"

            outline_color = "#38BDF8" if agent in self.selected_nodes else "#FFFFFF"
            outline_width = 3 if agent in self.selected_nodes else 1.5
            self.canvas.create_oval(ax - radius, ay - radius, ax + radius, ay + radius, fill=color, outline=outline_color, width=outline_width)

            font_size = 9 if radius >= 16 else 7
            lbl_text = f"N{agent.unique_id}\n[{len(agent.queue)}]"
            self.canvas.create_text(ax, ay, text=lbl_text, fill="#FFFFFF", font=("Helvetica", font_size, "bold"))

        for ag_origen, ag_destino in self.model.transmisiones_actuales:
            if ag_origen in agent_screen_pos and ag_destino in agent_screen_pos:
                xa, ya, ra = agent_screen_pos[ag_origen]
                xb, yb, rb = agent_screen_pos[ag_destino]
                pos_a = ag_origen.cell.coordinate
                pos_b = ag_destino.cell.coordinate

                # Dibujar enlace si no cruza el borde del torus
                if abs(pos_a[0] - pos_b[0]) <= self.model.radio_vecinos and abs(pos_a[1] - pos_b[1]) <= self.model.radio_vecinos:
                    dx, dy = xb - xa, yb - ya
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 0:
                        start_x, start_y = xa + (dx / dist) * (ra + 2), ya + (dy / dist) * (ra + 2)
                        end_x, end_y = xb - (dx / dist) * (rb + 5), yb - (dy / dist) * (rb + 5)
                        self.canvas.create_line(start_x, start_y, end_x, end_y, fill="#F59E0B", width=4, arrow=tk.LAST, arrowshape=(16, 20, 8))

if __name__ == "__main__":
    model = MyModel(n_agents=50, width=20, height=20, queue_max=5, tasa_generacion=0.15)
    app = SimulationApp(model=model)
    app.mainloop()

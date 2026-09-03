import mesa
import numpy as np
from mesa.discrete_space import CellAgent, OrthogonalMooreGrid
from collections import deque
import math
import random
import customtkinter as ctk
import tkinter as tk

from capacidad_max import obtener_max

# Configuración de tema visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MyAgent(CellAgent):
    def __init__(self, model, queue_max=5):
        super().__init__(model)
        self.queue = deque()
        self.queue_max = queue_max
        self.vecinos = []
        self.state = "Buscando"  # Estados: Buscando, Enrutando, Congestionado, Entregado
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_lost = 0

    def mover(self):
        """Fase 1: Mueve el agente a una celda vecina en la rejilla."""
        neighborhood = self.cell.get_neighborhood(radius=1, include_center=False)
        celdas_posibles = list(neighborhood.cells)
        if celdas_posibles:
            self.cell = self.model.random.choice(celdas_posibles)

    def detectar_vecinos(self):
        """Fase 2: Actualiza la lista de vecinos locales una vez que TODOS los nodos se han movido."""
        neighborhood = self.cell.get_neighborhood(radius=2, include_center=False)
        self.vecinos = [agent for agent in neighborhood.agents if isinstance(agent, MyAgent)]

    def generar_paquete(self, destino_agent):
        """Crea un nuevo paquete de datos con origen este nodo y destino el nodo indicado."""
        if len(self.queue) < self.queue_max:
            packet = {
                'id': f"P_{self.unique_id}_{self.model.total_generados + 1}",
                'origen_id': self.unique_id,
                'origen_pos': self.cell.coordinate,
                'destino_id': destino_agent.unique_id,
                'destino_pos': destino_agent.cell.coordinate,
                'saltos': 0
            }
            self.queue.append(packet)
            self.model.total_generados += 1
            self.state = "Generando"
            return True
        else:
            self.packets_lost += 1
            self.model.total_perdidos += 1
            return False

    def calcular_distancia_torus(self, pos_origen, pos_destino):
        """Calcula distancia euclidiana considerando grilla toroidal."""
        x1, y1 = pos_origen
        x2, y2 = pos_destino
        w, h = self.model.grid.width, self.model.grid.height
        dx = min(abs(x1 - x2), w - abs(x1 - x2))
        dy = min(abs(y1 - y2), h - abs(y1 - y2))
        return math.sqrt(dx**2 + dy**2)

    def enrutar_paquete(self):
        """Fase 3: Regla local de enrutamiento goloso sobre posiciones sincronizadas."""
        if not self.queue:
            self.state = "Buscando"
            return

        packet = self.queue[0]
        pos_actual = self.cell.coordinate
        destino_pos = packet['destino_pos']

        # CASO 1: Paquete llegó a destino final
        if pos_actual == destino_pos:
            self.queue.popleft()
            self.model.total_entregados += 1
            self.packets_received += 1
            self.state = "Entregado"
            self.model.registrar_log(f"Nodo N{self.unique_id}: Paquete {packet['id']} LLEGÓ a destino.")
            return

        # CASO 2: Enrutamiento Goloso hacia el vecino más cercano al destino
        dist_actual = self.calcular_distancia_torus(pos_actual, destino_pos)
        candidatos = []

        for vecino in self.vecinos:
            dist_vecino = self.calcular_distancia_torus(vecino.cell.coordinate, destino_pos)
            candidatos.append({
                'agente': vecino,
                'distancia': dist_vecino,
                'cola_llena': len(vecino.queue) >= vecino.queue_max,
            })

        candidatos.sort(key=lambda c: c['distancia'])
        candidatos_validos = [c for c in candidatos if c['distancia'] < dist_actual]

        siguiente_salto = None
        if candidatos_validos:
            # Control de congestión: elegir el más cercano que NO esté lleno
            no_congestionados = [c for c in candidatos_validos if not c['cola_llena']]
            if no_congestionados:
                siguiente_salto = no_congestionados[0]['agente']
            else:
                self.state = "Congestionado"
                self.model.registrar_log(f"Nodo N{self.unique_id}: Vecinos más cercanos congestionados para {packet['id']}.")

        if siguiente_salto is not None:
            if len(siguiente_salto.queue) < siguiente_salto.queue_max:
                p = self.queue.popleft()
                p['saltos'] += 1
                siguiente_salto.queue.append(p)
                self.packets_sent += 1
                self.state = "Enrutando"
                # Registrar referencia a los agentes (origen y destino) para consultar sus posiciones finales sincronizadas
                self.model.transmisiones_actuales.append((self, siguiente_salto))
            else:
                self.state = "Congestionado"
        else:
            if len(self.queue) >= self.queue_max:
                p_lost = self.queue.popleft()
                self.packets_lost += 1
                self.model.total_perdidos += 1
                self.state = "Congestionado"
                self.model.registrar_log(f"Nodo N{self.unique_id}: Paquete {p_lost['id']} PERDIDO por cola llena.")

    def procesar_trafico_y_enrutamiento(self):
        """Generación y enrutamiento en la fase de comunicación."""
        if self.model.random.random() < self.model.tasa_generacion:
            otros = [a for a in self.model.agents if a != self]
            if otros:
                destino = self.model.random.choice(otros)
                self.generar_paquete(destino)

        self.enrutar_paquete()


class MyModel(mesa.Model):
    def __init__(self, n_agents=50, width=20, height=20, queue_max=5, tasa_generacion=0.15):
        super().__init__()
        self.grid = OrthogonalMooreGrid((width, height), torus=True)
        self.n_agents = n_agents
        self.queue_max = queue_max
        self.tasa_generacion = tasa_generacion

        self.current_step = 0
        self.total_generados = 0
        self.total_entregados = 0
        self.total_perdidos = 0
        self.transmisiones_actuales = []
        self.logs = []

        # Asignar celdas iniciales ÚNICAS
        todas_las_celdas = list(self.grid.all_cells)
        celdas_seleccionadas = self.random.sample(todas_las_celdas, n_agents)

        agents = MyAgent.create_agents(self, n_agents, queue_max=queue_max)
        for agent, cell in zip(agents, celdas_seleccionadas):
            agent.cell = cell

        for agent in self.agents:
            agent.detectar_vecinos()

    def registrar_log(self, mensaje):
        log_entry = f"[Step {self.current_step}] {mensaje}"
        self.logs.append(log_entry)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def step(self):
        self.current_step += 1
        self.transmisiones_actuales.clear()

        # FASE 1: Todos los nodos se mueven a sus nuevas celdas
        self.agents.shuffle_do("mover")

        # FASE 2: Todos los nodos detectan a sus nuevos vecinos con las posiciones ya actualizadas
        self.agents.do("detectar_vecinos")

        # FASE 3: Se genera y enruta tráfico entre nodos que comparten las posiciones actuales
        self.agents.shuffle_do("procesar_trafico_y_enrutamiento")


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

        lbl_titulo = ctk.CTkLabel(
            self.panel_izq, 
            text="Red Móvil ", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_titulo.pack(padx=15, pady=(12, 4))

        lbl_sub = ctk.CTkLabel(
            self.panel_izq, 
            text="Fases Sincronizadas: Movimiento ➔ Enrutamiento",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray"
        )
        lbl_sub.pack(padx=15, pady=(0, 10))

        # CONTROLES
        frame_ctrl = ctk.CTkFrame(self.panel_izq, corner_radius=8)
        frame_ctrl.pack(fill="x", padx=15, pady=5)

        lbl_sec_ctrl = ctk.CTkLabel(frame_ctrl, text="Controles", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_sec_ctrl.pack(pady=(8, 4))

        self.btn_step_1 = ctk.CTkButton(
            frame_ctrl, 
            text="Paso a Paso (+1 Tick)", 
            fg_color="#2563EB", 
            hover_color="#1D4ED8",
            command=self.ejecutar_paso_unico
        )
        self.btn_step_1.pack(fill="x", padx=12, pady=4)

        frame_until = ctk.CTkFrame(frame_ctrl, fg_color="transparent")
        frame_until.pack(fill="x", padx=12, pady=4)

        lbl_pasos = ctk.CTkLabel(frame_until, text="Pasos (X):", font=ctk.CTkFont(size=12))
        lbl_pasos.pack(side="left", padx=(0, 4))

        self.entry_pasos = ctk.CTkEntry(frame_until, width=65)
        self.entry_pasos.insert(0, "10")
        self.entry_pasos.pack(side="left", padx=4)

        self.btn_until_x = ctk.CTkButton(
            frame_until, 
            text="Ejecutar x pasos", 
            fg_color="#059669", 
            hover_color="#047857",
            command=self.ejecutar_hasta_x_pasos
        )
        self.btn_until_x.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.btn_play_pause = ctk.CTkButton(
            frame_ctrl, 
            text="Continuo", 
            fg_color="#D97706", 
            hover_color="#B45309",
            command=self.toggle_play_pause
        )
        self.btn_play_pause.pack(fill="x", padx=12, pady=4)

        self.btn_reset = ctk.CTkButton(
            frame_ctrl, 
            text="Reiniciar", 
            fg_color="#4B5563", 
            hover_color="#374151",
            command=self.reiniciar_simulacion
        )
        self.btn_reset.pack(fill="x", padx=12, pady=(4, 8))

        # PARÁMETROS
        frame_param = ctk.CTkFrame(self.panel_izq, corner_radius=8)
        frame_param.pack(fill="x", padx=15, pady=5)

        self.lbl_tasa_val = ctk.CTkLabel(frame_param, text=f"Tasa de Generación: {int(self.model.tasa_generacion * 100)}%", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_tasa_val.pack(pady=(6, 2))

        self.slider_tasa = ctk.CTkSlider(
            frame_param, 
            from_=0.01, 
            to=0.5, 
            number_of_steps=50,
            command=self.cambiar_tasa_generacion
        )
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

        self.lbl_inspect_info = ctk.CTkLabel(
            self.frame_inspect, 
            text="Ningún nodo seleccionado.", 
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w"
        )
        self.lbl_inspect_info.pack(fill="x", padx=10, pady=(0, 6))

        # CONSOLA LOG
        self.txt_log = ctk.CTkTextbox(self.panel_izq, height=110, font=ctk.CTkFont(family="Consolas", size=10))
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(5, 12))

    def _crear_panel_derecho(self):
        self.panel_der = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.panel_der.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        lbl_grid_title = ctk.CTkLabel(
            self.panel_der, 
            text="Grilla Dinámica de Nodos Móviles (20x20 - 50 Nodos)", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_grid_title.pack(pady=8)

        self.canvas_size = 700
        self.canvas = tk.Canvas(
            self.panel_der, 
            width=self.canvas_size, 
            height=self.canvas_size, 
            bg="#0F172A", 
            highlightthickness=0
        )
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
        self.model = MyModel(n_agents=50, width=20, height=20, queue_max=5, tasa_generacion=self.slider_tasa.get())
        self.actualizar_interfaz()

    def on_canvas_click(self, event):
        grid_w = self.model.grid.width
        cell_size = self.canvas_size / grid_w
        gx = int(event.x // cell_size)
        gy = int(event.y // cell_size)

        # Si el usuario hace clic fuera del rango de la grilla
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

        # Mostrar la información de TODOS los nodos presentes en la celda seleccionada
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
        else:
            self.lbl_inspect_info.configure(text="Haz clic en cualquier celda para inspeccionar los nodos.", text_color="gray")

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

        # 1. Dibujar celdas del tablero
        for i in range(grid_w):
            for j in range(grid_h):
                x1, y1 = i * cell_size, j * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                bg_color = "#1E293B" if (i + j) % 2 == 0 else "#0F172A"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="#334155", width=1)

        # Resaltar celda seleccionada
        if self.selected_cell_coords:
            sx, sy = self.selected_cell_coords
            self.canvas.create_rectangle(
                sx * cell_size, sy * cell_size,
                (sx + 1) * cell_size, (sy + 1) * cell_size,
                outline="#38BDF8", width=3
            )

        # Pre-calcular posiciones exactas renderizadas de cada agente en la pantalla
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
                    ax, ay = cell_cx, cell_cy
                    radius = 15
                elif count == 2:
                    offset = 14
                    ax = cell_cx - offset if idx == 0 else cell_cx + offset
                    ay = cell_cy
                    radius = 10
                elif count == 3:
                    offsets = [(-14, -12), (14, -12), (0, 14)]
                    ax = cell_cx + offsets[idx][0]
                    ay = cell_cy + offsets[idx][1]
                    radius = 8
                else:
                    offsets = [(-14, -14), (14, -14), (-14, 14), (14, 14)]
                    o = offsets[idx % 4]
                    ax = cell_cx + o[0]
                    ay = cell_cy + o[1]
                    radius = 5

                agent_screen_pos[agent] = (ax, ay, radius)

        # 2. Dibujar Agentes (Nodos)
        for agent, (ax, ay, radius) in agent_screen_pos.items():
            q_ratio = len(agent.queue) / agent.queue_max
            if q_ratio >= 1.0:
                color = "#DC2626"  # Rojo: Congestionado
            elif agent.state == "Generando":
                color = "#9333EA"  # Morado: Generador de paquete
            elif q_ratio >= 0.5:
                color = "#D97706"  # Naranja: Semi-lleno
            elif agent.state == "Enrutando":
                color = "#059669"  # Verde: Enrutando
            else:
                color = "#2563EB"  # Azul: Normal

            outline_color = "#38BDF8" if agent in self.selected_nodes else "#FFFFFF"
            outline_width = 3 if agent in self.selected_nodes else 1.5

            self.canvas.create_oval(
                ax - radius, ay - radius,
                ax + radius, ay + radius,
                fill=color, outline=outline_color, width=outline_width
            )

            font_size = 9 if radius >= 16 else 7
            lbl_text = f"N{agent.unique_id}\n[{len(agent.queue)}]"
            self.canvas.create_text(
                ax, ay, 
                text=lbl_text, 
                fill="#FFFFFF", 
                font=("Helvetica", font_size, "bold")
            )

        # 3. Dibujar enlaces de transmisión CON FLECHAS VISIBLES apuntando al nodo destino
        for ag_origen, ag_destino in self.model.transmisiones_actuales:
            if ag_origen in agent_screen_pos and ag_destino in agent_screen_pos:
                xa, ya, ra = agent_screen_pos[ag_origen]
                xb, yb, rb = agent_screen_pos[ag_destino]

                pos_a = ag_origen.cell.coordinate
                pos_b = ag_destino.cell.coordinate

                # Dibujar enlace si no cruza el borde del torus discontinuo
                if abs(pos_a[0] - pos_b[0]) <= 1 and abs(pos_a[1] - pos_b[1]) <= 1:
                    dx = xb - xa
                    dy = yb - ya
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 0:
                        # Recortar coordenadas para que la punta de la flecha descanse exactamente en el borde del nodo destino
                        start_x = xa + (dx / dist) * (ra + 2)
                        start_y = ya + (dy / dist) * (ra + 2)
                        end_x = xb - (dx / dist) * (rb + 5)
                        end_y = yb - (dy / dist) * (rb + 5)

                        self.canvas.create_line(
                            start_x, start_y, end_x, end_y,
                            fill="#F59E0B", width=4,
                            arrow=tk.LAST, arrowshape=(16, 20, 8)
                        )


if __name__ == "__main__":
    model = MyModel(n_agents=50, width=20, height=20, queue_max=5, tasa_generacion=0.15)
    app = SimulationApp(model=model)
    app.mainloop()
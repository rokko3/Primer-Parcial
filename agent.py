from collections import deque
import math
from mesa.discrete_space import CellAgent

class MyAgent(CellAgent):
    def __init__(self, model, queue_max=5):
        super().__init__(model)
        self.queue = deque()
        self.queue_max = queue_max
        self.vecinos = []
        self.state = "Buscando"  # Estados: Buscando, Generando, Enrutando, Congestionado, Entregado
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_lost = 0
        self.historial_acciones = deque(maxlen=10)

    def registrar_accion(self, accion):
        self.historial_acciones.append(f"[Tick {self.model.current_step}] {accion}")

    def mover(self):
        neighborhood = self.cell.get_neighborhood(radius=1, include_center=False)
        celdas_posibles = list(neighborhood.cells)
        if celdas_posibles:
            self.cell = self.model.random.choice(celdas_posibles)

    def detectar_vecinos(self):
        self.registrar_accion("Limpiar Vecinos")
        self.registrar_accion("Enviando PACKET SEND HELLO")
        neighborhood = self.cell.get_neighborhood(radius=self.model.radio_vecinos, include_center=True)
        self.vecinos = [agent for agent in neighborhood.agents if isinstance(agent, MyAgent) and agent.unique_id != self.unique_id]
        if self.vecinos:
            self.registrar_accion(f"Registrar {len(self.vecinos)} vecino(s) (PACKET CONFIRMATION)")

    def generar_paquete(self, destino_agent):
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
            self.registrar_accion(f"Generando paquete {packet['id']} hacia N{destino_agent.unique_id}")
            return True
        else:
            self.packets_lost += 1
            self.model.total_perdidos += 1
            return False

    def calcular_distancia_euclidiana(self, pos_origen, pos_destino):
        x1, y1 = pos_origen
        x2, y2 = pos_destino
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def enrutar_paquete(self):
        if not self.queue:
            return None

        packet = self.queue[0]
        destino_pos = packet['destino_pos']
        pos_actual = self.cell.coordinate

        if pos_actual == destino_pos:
            p = self.queue.popleft()
            self.model.total_entregados += 1
            self.packets_received += 1
            self.registrar_accion(f"Procesar último paquete: {p['id']} LLEGÓ a destino")
            self.model.registrar_log(f"Nodo N{self.unique_id}: Paquete {p['id']} LLEGÓ a destino.")
            return

        dist_actual = self.calcular_distancia_euclidiana(pos_actual, destino_pos)
        candidatos = []
        for vecino in self.vecinos:
            dist_vecino = self.calcular_distancia_euclidiana(vecino.cell.coordinate, destino_pos)
            candidatos.append({
                'agente': vecino,
                'distancia': dist_vecino,
                'cola_llena': len(vecino.queue) >= vecino.queue_max,
            })

        candidatos.sort(key=lambda c: c['distancia'])
        candidatos_validos = [c for c in candidatos if c['distancia'] < dist_actual]

        siguiente_salto = None
        if candidatos_validos:
            no_congestionados = [c for c in candidatos_validos if not c['cola_llena']]
            if no_congestionados:
                siguiente_salto = no_congestionados[0]['agente']
            else:
                self.registrar_accion(f"Descartando {packet['id']} por congestión (Buscar Mejor Vecino)")
                self.model.registrar_log(f"Nodo N{self.unique_id}: Vecinos más cercanos congestionados para {packet['id']}.")

        if siguiente_salto is not None:
            if len(siguiente_salto.queue) < siguiente_salto.queue_max:
                p = self.queue.popleft()
                p['saltos'] += 1
                siguiente_salto.queue.append(p)
                self.packets_sent += 1
                self.registrar_accion(f"Enrutar (PACKET DISTRIBUTION): {p['id']} a N{siguiente_salto.unique_id}")
                self.model.transmisiones_actuales.append((self, siguiente_salto))
                return True
            else:
                pass
        else:
            if len(self.queue) >= self.queue_max:
                p_lost = self.queue.popleft()
                self.packets_lost += 1
                self.model.total_perdidos += 1
                self.registrar_accion(f"Descartando {p_lost['id']} localmente por cola llena")
                self.model.registrar_log(f"Nodo N{self.unique_id}: Paquete {p_lost['id']} PERDIDO por cola llena.")
        return False

    def step(self):
        """Máquina de estados donde cada acción toma un tick."""
        if self.state == "Generando":
            # Ejecuta la generación
            otros = [a for a in self.model.agents if a.unique_id != self.unique_id and a.cell.coordinate != self.cell.coordinate]
            if otros:
                destino = self.model.random.choice(otros)
                self.generar_paquete(destino)
            
            # Cambia de estado para el próximo tick
            if self.queue:
                self.state = "Enrutando"
            else:
                self.state = "Buscando"

        elif self.state == "Enrutando":
            # Ejecuta el enrutamiento
            self.enrutar_paquete()
            
            # Si se quedó sin paquetes, pasa a buscar
            if not self.queue:
                self.state = "Buscando"
            elif len(self.queue) >= self.queue_max * 0.8:
                self.state = "Congestionado"

        elif self.state == "Congestionado":
            self.enrutar_paquete()
            if len(self.queue) < self.queue_max * 0.8:
                self.state = "Enrutando" if self.queue else "Buscando"

        else: # Buscando o Entregado
            # Limpia estado si era entregado
            self.state = "Buscando"
            
            # Ejecuta movimiento y detección (cuenta como 1 tick de escaneo de red)
            self.mover()
            self.detectar_vecinos()
            
            # Transición para el PRÓXIMO tick
            if self.model.random.random() < self.model.tasa_generacion:
                self.state = "Generando"
            elif self.queue:
                self.state = "Enrutando"


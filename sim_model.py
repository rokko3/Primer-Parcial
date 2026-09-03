import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from agent import MyAgent

class MyModel(mesa.Model):
    def __init__(self, n_agents=50, width=20, height=20, queue_max=5, tasa_generacion=0.15, radio_vecinos=1):
        super().__init__()
        self.grid = OrthogonalMooreGrid((width, height), torus=False)
        self.n_agents = n_agents
        self.queue_max = queue_max
        self.tasa_generacion = tasa_generacion
        self.radio_vecinos = radio_vecinos

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

    def registrar_log(self, mensaje):
        log_entry = f"[Step {self.current_step}] {mensaje}"
        self.logs.append(log_entry)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def step(self):
        self.current_step += 1
        self.transmisiones_actuales.clear()
        
        # FASE 1: Movimiento sincronizado de todos los nodos
        for a in self.agents:
            a.mover()
                
        # FASE 2: Actualización sincronizada de vecinos (todos a la vez, garantizando simetría)
        for a in self.agents:
            a.detectar_vecinos()
            
        # FASE 3: Generación y enrutamiento
        for a in self.agents:
            a.procesar_trafico_y_enrutamiento()

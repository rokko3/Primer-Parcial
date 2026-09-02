import mesa
import numpy as np
from mesa.discrete_space import CellAgent, OrthogonalMooreGrid
from collections import deque
from capacidad_max import obtener_max
import customtkinter as ctk

from mesa.time import Priority, Schedule

class grafica(ctk.CTk):
    def __init__(self, master, model):
        super().__init__()
        self.title=("Simulation Info")
        self.model = model
        self.label = ctk.CTkLabel(self, text="Model Information")
        self.label.pack(pady=10)
        self.geometry("1400x850")
        self.step_button=ctk.CTkButton(self,text="Step",command=self.step_model)
        self.step_button.pack(pady=10)

    def step_model(self):
        self.model.step()
class MyAgent(CellAgent):
    def __init__(self, model, age):
        super().__init__(model)
        self.age = age
        self.packets=deque()
        self.vecinos=[]
        self.capacidad_max=obtener_max(ancho_banda_canal=20,snr=10)
        self.gridx=None
        self.gridy=None # This will be set when the agent is placed on the grid

    def step(self):
        self.age += 1
        print(f"Agent {self.unique_id} now is {self.age} years old")
        self.gridx, self.gridy = self.cell.coordinate
        print(f"Agent {self.unique_id} is at position ({self.gridx}, {self.gridy})")
        print("####"*5)
        if self.model.time%5==0:
            print(f"Agent {self.unique_id} is generating a packet")
    def detectar_vecinos(self):
        
        # Get the neighboring cells using the Moore neighborhood
        print(f"Posicion actual: {self.gridx}, {self.gridy}")
        neighbors = self.cell.get_neighborhood(radius=1, include_center=False)
        print(neighbors.cells[1])
        # Store the neighboring agents in the vecinos list
        self.vecinos = [agent for agent in neighbors.agents if isinstance(agent, MyAgent)]
        print(f"Agent {self.unique_id} has neighbors: {[neighbor.unique_id for neighbor in self.vecinos]}")
    def generate_packet(self,type,size,origen,destino):
        packet ={
            'type':type,
            'size':size,
            'origen':origen,
            'destino':destino,  
        }
        pass
class MyModel(mesa.Model):
    def __init__(self, n_agents):
        super().__init__()
        self.grid = mesa.discrete_space.OrthogonalMooreGrid((10, 10), torus=True)
        initial_ages = self.rng.integers(0, 80, size=n_agents)
        agents = MyAgent.create_agents(self, n_agents, initial_ages)
        for agent in agents:
            agent.cell = self.grid.all_cells.select_random_cell()

        self.packet_hello=self.schedule_recurring(
            self.packet_hello_func,Schedule(interval=5.0),
        )
    
    def step(self):
        print(model.time)
        self.agents.shuffle_do("step")
            #self.agents.do('generate_packet',type='data',size=100,origen='A',destino='B')
        for agent in self.agents:
            agent.cell=self.grid.all_cells.select_random_cell()
    def packet_hello_func(self):
        #avg_age=self.agents.agg('age',np.mean)
        #for agent in self.agents:
        #    agent.age+=avg_age
        self.agents.do('detectar_vecinos')
        pass

model=MyModel(n_agents=3)
model
print(len(model.agents)   )

for agen in model.agents:
    print(f"Agent {agen.unique_id}")

app=grafica(master=None,model=model)
app.mainloop()
import numpy as np

class Particle(np.ndarray):
    def __init__(self, **kwargs):
        mass = kwargs.get("mass")
        rad = kwargs.get("rad")
        position = kwargs.get("position")
        velocity = kwargs.get("velocity")
        acceleration = kwargs.get("acceleration")

        super().__init__([rad, position, velocity, acceleration], 
                         dtype=[("rad", "float32"), 
                                ("position", "float32"), 
                                ("velocity", "float32"), 
                                ("acceleration", "float32")])
        
        self.mass = kwargs.get("mass", mass)
        self.density = mass / (4/3 * np.pi * rad**3)

    def force_x(self, **kwargs):
        # Placeholder for force function in x direction
        v_air = kwargs.get("v_air", 0.0)
        v = self["velocity"].norm()

        
        return 0.0

    def force_y(self, **kwargs):
        # Placeholder for force function in y direction
        return 0.0

    def acceleration_x(self, **kwargs):
        return self.force_x(**kwargs) / self["mass"]
    
    def acceleration_y(self, **kwargs):
        return self.force_y(**kwargs) / self["mass"]
    
    def update_particle(self, function = None, dt: float = 1.0):
        # Update the velocity based on the provided function
        self["position"][0] += self["velocity"][0] * dt + 0.5 * self.acceleration_x(**function) * dt**2
        self["position"][1] += self["velocity"][1] * dt + 0.5 * self.acceleration_y(**function) * dt**2
        self["velocity"][0] += self.acceleration_x(**function) * dt
        self["velocity"][1] += self.acceleration_y(**function) * dt
        self["acceleration"][0] = self.acceleration_x(**function)
        self["acceleration"][1] = self.acceleration_y(**function)
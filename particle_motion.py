import numpy as np

class Particle(np.ndarray):
    def __init__(self, mass, rad, position, velocity, acceleration):
        super().__init__([mass, rad, position, velocity, acceleration], 
                         dtype=[("mass", "float32"), 
                                ("rad", "float32"), 
                                ("position", "float32"), 
                                ("velocity", "float32"), 
                                ("acceleration", "float32")])
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
    
    @staticmethod
    def update_particle(particle: np.ndarray, function = None, dt: float = 1.0):
        # Update the velocity based on the provided function
        if function is not None:
            particle["position", "velocity", "acceleration"] = function(particle["position"], particle["velocity"], particle["acceleration"], dt)
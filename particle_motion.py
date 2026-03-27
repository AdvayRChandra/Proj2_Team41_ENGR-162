import numpy as np

class Particle(np.ndarray):
    def __init__(self, mass, rad, position, velocity, acceleration):
        super().__init__([mass, rad, position, velocity, acceleration], 
                         dtype=[("mass", "float32"), 
                                ("rad", "float32"), 
                                ("position", "float32"), 
                                ("velocity", "float32"), 
                                ("acceleration", "float32")])

    @staticmethod
    def update_particle(particle: np.ndarray, function = None, dt: float = 1.0):
        # Update the velocity based on the provided function
        if function is not None:
            particle["position", "velocity", "acceleration"] = function(particle["position"], particle["velocity"], particle["acceleration"], dt)
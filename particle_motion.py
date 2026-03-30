import math

g = 9.81  # m/s^2, acceleration due to gravity
viscosity_air = 1.81e-5  # kg/(m·s), dynamic viscosity of air at room temperature

class Air:
    def __init__(self, **kwargs):
        self.velocity = [float(v) for v in kwargs.get("velocity", [0.0, 0.0])]  # m/s
        self.density = float(kwargs.get("density", 1.225))  # kg/m^3 at sea level

class Particle:
    def __init__(self, **kwargs):
        self.mass = float(kwargs.get("mass", 1.0))
        self.charge = float(kwargs.get("charge", 0.0))

        # Prefer explicit diameter (plus inferred volume), else fall back to volume.
        if "diameter" in kwargs and kwargs["diameter"] is not None:
            self.diameter = float(kwargs["diameter"])
            self.radius = self.diameter / 2.0
            self.volume = 4.0 / 3.0 * math.pi * self.radius ** 3
        else:
            self.volume = float(kwargs.get("volume", 1.0))
            self.radius = (3.0 * self.volume / (4.0 * math.pi)) ** (1.0 / 3.0)
            self.diameter = 2.0 * self.radius

        pos = kwargs.get("position", (0.0, 0.0))
        vel = kwargs.get("velocity", (0.0, 0.0))
        acc = kwargs.get("acceleration", (0.0, 0.0))

        self.position = [float(pos[0]), float(pos[1])]
        self.velocity = [float(vel[0]), float(vel[1])]
        self.acceleration = [float(acc[0]), float(acc[1])]

        self.density = self.mass / self.volume

    def magnitude_velocity(velocity):
        return math.sqrt(velocity[0]**2 + velocity[1]**2)

    def renolds_number(self, air: Air):
        return 24 / (air.density * self.magnitude_velocity(self.v_apparent) * self.diameter / viscosity_air)

    def stokes(self, air: Air, dimension: int):
        # Stokes' drag in x direction
        self.v_apparent = self.velocity[0] - air.velocity[0]
        stokes_x = 0.5 * air.density * 24 / self.reynolds_number(air)
        stokes_x *= math.pi / 8 * self.diameter**2 * self.magnitude_velocity(self.v_apparent) * self.v_apparent[dimension]
        return stokes_x

    def buoyancy(self, air: Air):
        return g * (self.density - air.density) * self.mass  # Buoyant force minus weight

    def force_x(self, air: Air):
        return self.stokes(air, 0)  # Drag in x direction

    def force_y(self, air: Air):
        return self.buoyancy(air) - self.stokes(air, 1)  # Buoyancy minus drag in y direction

    def update_particle(self, air: Air, dt: float = 1.0):
        self.v_apparent = [self.velocity[0] - air.velocity[0], self.velocity[1] - air.velocity[1]]

        ax = self.force_x(air) / self.mass
        ay = self.force_y(air) / self.mass

        self.position[0] += self.velocity[0] * dt + 0.5 * ax * dt ** 2
        self.position[1] += self.velocity[1] * dt + 0.5 * ay * dt ** 2

        self.velocity[0] += ax * dt
        self.velocity[1] += ay * dt

        self.acceleration[0] = ax
        self.acceleration[1] = ay

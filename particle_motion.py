import math
import random

g = 9.81  # m/s^2, acceleration due to gravity
viscosity_air = 1.81e-5  # kg/(m·s), dynamic viscosity of air at room temperature
e0 = 8.854e-12  # F/m, vacuum permittivity

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

    @staticmethod
    def magnitude_velocity(velocity):
        return math.sqrt(velocity[0]**2 + velocity[1]**2)

    def reynolds_number(self, air: Air):
        vmag = self.magnitude_velocity(self.v_apparent)
        if vmag <= 1e-12:
            return 1e-12
        return air.density * vmag * self.diameter / viscosity_air

    def stokes(self, air: Air, dimension: int):
        # Stokes drag force component for low Reynolds number flow
        self.v_apparent = [self.velocity[0] - air.velocity[0], self.velocity[1] - air.velocity[1]]
        return -6.0 * math.pi * viscosity_air * self.radius * self.v_apparent[dimension]
    
    def electrostatic_force(self, surface_charge_density: float, concentration: float, collector_plate_x: float, max_distance: float):
        # Electrostatic force due to surface charge density
        collector_plate_distance = self.position[0] - collector_plate_x
        ambient_factor = collector_plate_distance - max_distance if collector_plate_distance > max_distance else 0

        return ((self.charge ** 2 * concentration) * ambient_factor - self.charge * surface_charge_density) / (2 * e0)

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


def spawn_random_smog_particle(spawn_x_min=-20.0, spawn_x_max=20.0, spawn_y_min=40.0, spawn_y_max=80.0):
    # Small particle ranges (meters, mg-scale here for demonstration)
    diameter = random.uniform(1e-6, 2e-5)
    density = random.uniform(1000, 2000)  # kg/m^3 (solid/soot material)
    volume = math.pi / 6 * diameter ** 3
    mass = density * volume

    return Particle(
        mass=mass,
        diameter=diameter,
        position=(random.uniform(spawn_x_min, spawn_x_max), random.uniform(spawn_y_min, spawn_y_max)),
        velocity=(random.uniform(-0.5, 0.5), random.uniform(-0.1, 0.1)),
    )


def simulate_smog_tower(
    num_particles=100,
    dt=0.1,
    max_time=300.0,
    tower_x=0.0,
    tower_height=60.0,
    catch_distance=0.01,
    spawn_x_min=-20.0,
    spawn_x_max=20.0,
    spawn_y_min=40.0,
    spawn_y_max=80.0,
    boundary_x_min=-40.0,
    boundary_x_max=40.0,
    boundary_y_min=0.0,
    boundary_y_max=100.0,
    air_kwargs=None,
    particle_type="pm2_5",
    wind_x_range=(-2.0,2.0),
):
    air_kwargs = air_kwargs or {}
    air = Air(**air_kwargs)

    # Particle type presets
    particle_presets = {
        "pm2_5": {
            "mass": 1.8e-14,
            "diameter": 2.5e-6,
            "density": 2.20e3,
        },
        "pm10": {
            "mass": 1.0e-12,
            "diameter": 10e-6,
            "density": 1.91e3,
        },
    }

    preset = particle_presets.get(particle_type.lower())
    if not preset:
        raise ValueError("particle_type must be 'pm2_5' or 'pm10'")

    collisions = []

    # random wind speed for each simulation run (horizontal only)
    wind_speed = [random.uniform(*wind_x_range), 0.0]
    air.velocity = wind_speed

    particles = []
    for i in range(num_particles):
        p = spawn_random_smog_particle(spawn_x_min=spawn_x_min, spawn_x_max=spawn_x_max, spawn_y_min=spawn_y_min, spawn_y_max=spawn_y_max)
        p.mass = preset["mass"]
        p.diameter = preset["diameter"]
        p.radius = p.diameter / 2.0
        p.volume = 4.0 / 3.0 * math.pi * p.radius ** 3
        p.density = preset["density"]
        particles.append({"id": i, "particle": p, "status": None, "time": 0.0})

    current_time = 0.0
    while current_time < max_time and any(p["status"] is None for p in particles):
        for entry in particles:
            if entry["status"] is not None:
                continue

            p = entry["particle"]
            p.update_particle(air, dt=dt)
            entry["time"] += dt
            current_time = entry["time"] if entry["time"] > current_time else current_time

            # caught if within 1cm of vertical fin in x and in vertical profile [0, tower_height]
            if 0.0 <= p.position[1] <= tower_height and abs(p.position[0] - tower_x) <= catch_distance:
                entry["status"] = "caught"
                continue

            # escaped if it leaves the bounding area
            if (p.position[0] < boundary_x_min or p.position[0] > boundary_x_max or p.position[1] < boundary_y_min or p.position[1] > boundary_y_max):
                entry["status"] = "escaped"
                continue

            # also escape if it falls below ground
            if p.position[1] < 0.0:
                entry["status"] = "escaped"
                continue

    # mark any remaining unresolved as escaped once max_time reached
    for entry in particles:
        if entry["status"] is None:
            entry["status"] = "escaped"

    for entry in particles:
        collisions.append({
            "particle": entry["id"],
            "status": entry["status"],
            "time": entry["time"],
            "position": tuple(entry["particle"].position),
            "diameter": entry["particle"].diameter,
            "mass": entry["particle"].mass,
        })

    return collisions


def plot_smog_tower_collisions(collisions, num_particles=100):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting, install with: pip install matplotlib")

    if not collisions:
        print("No collisions to plot.")
        return

    times = [c["time"] for c in collisions]
    distances = [math.hypot(c["position"][0], c["position"][1]) for c in collisions]
    diameters = [c["diameter"] for c in collisions]

    plt.figure(figsize=(10, 6))

    plt.subplot(2, 1, 1)
    plt.scatter(times, distances, c=diameters, cmap="viridis", s=50)
    plt.colorbar(label="Particle diameter (m)")
    plt.xlabel("Collision time (s)")
    plt.ylabel("Distance from tower base (m)")
    plt.title(f"Smog tower collision events (out of {num_particles} particles)")

    plt.subplot(2, 1, 2)
    # basic python histogram for collision time from direct data
    num_bins = 10
    t_min, t_max = min(times), max(times)
    bin_width = (t_max - t_min) / num_bins if t_max > t_min else 1.0
    bins = [t_min + i * bin_width for i in range(num_bins + 1)]
    rates = [0] * num_bins

    for t in times:
        bin_index = min(int((t - t_min) / bin_width), num_bins - 1)
        rates[bin_index] += 1

    bin_centers = [(bins[i] + bins[i + 1]) / 2 for i in range(num_bins)]
    plt.bar(bin_centers, rates, width=bin_width * 0.9)
    plt.xlabel("Collision time (s)")
    plt.ylabel("Number of collisions")

    plt.tight_layout()
    plt.show()


def plot_percent_caught(monthly_results, save_path='percent_caught.png'):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting, install with: pip install matplotlib")

    months = list(monthly_results.keys())
    pm25_percent = [monthly_results[m]["pm2_5"]["caught"] / (monthly_results[m]["pm2_5"]["caught"] + monthly_results[m]["pm2_5"]["escaped"] + 1e-12) * 100 for m in months]
    pm10_percent = [monthly_results[m]["pm10"]["caught"] / (monthly_results[m]["pm10"]["caught"] + monthly_results[m]["pm10"]["escaped"] + 1e-12) * 100 for m in months]

    x = range(len(months))
    width = 0.35

    plt.figure(figsize=(12, 6))
    plt.bar([i - width / 2 for i in x], pm25_percent, width=width, label='PM2.5')
    plt.bar([i + width / 2 for i in x], pm10_percent, width=width, label='PM10')
    plt.xticks(x, months, rotation=45)
    plt.ylabel('Percent caught (%)')
    plt.title('Monthly percent of particles caught by smog tower fin')
    plt.legend()
    plt.tight_layout()

    plt.savefig(save_path)
    print(f"Saved percent caught plot to {save_path}")
    try:
        plt.show()
    except Exception:
        print("plt.show() failed in this environment; saved figure instead.")


def simulate_monthly_smog_tower(
    num_particles=200,
    dt=0.05,
    max_time=180.0,
    tower_x=0.0,
    tower_height=60.0,
    catch_distance=0.01,
    spawn_x_min=-20.0,
    spawn_x_max=20.0,
    spawn_y_min=40.0,
    spawn_y_max=80.0,
    boundary_x_min=-40.0,
    boundary_x_max=40.0,
    boundary_y_min=0.0,
    boundary_y_max=120.0,
    wind_x_range=(-2.0, 2.0),
    wind_y_range=(-1.0, 1.0),
):
    monthly_air_density = {
        "January": 1.224194,
        "February": 1.221314,
        "March": 1.207616,
        "April": 1.188565,
        "May": 1.168943,
        "June": 1.157643,
        "July": 1.154780,
        "August": 1.154780,
        "September": 1.161332,
        "October": 1.175456,
        "November": 1.197880,
        "December": 1.216797,
    }

    monthly_results = {}
    for month, density in monthly_air_density.items():
        results = {}
        for particle_type in ["pm2_5", "pm10"]:
            hits = simulate_smog_tower(
                num_particles=num_particles,
                dt=dt,
                max_time=max_time,
                tower_x=tower_x,
                tower_height=tower_height,
                catch_distance=catch_distance,
                spawn_x_min=spawn_x_min,
                spawn_x_max=spawn_x_max,
                spawn_y_min=spawn_y_min,
                spawn_y_max=spawn_y_max,
                boundary_x_min=boundary_x_min,
                boundary_x_max=boundary_x_max,
                boundary_y_min=boundary_y_min,
                boundary_y_max=boundary_y_max,
                air_kwargs={"density": density},
                particle_type=particle_type,
                wind_x_range=wind_x_range,
            )
            caught = sum(1 for p in hits if p["status"] == "caught")
            escaped = sum(1 for p in hits if p["status"] == "escaped")
            results[particle_type] = {"caught": caught, "escaped": escaped}
        monthly_results[month] = results

    return monthly_results


if __name__ == "__main__":
    results = simulate_monthly_smog_tower()
    for month, data in results.items():
        print(f"{month}: PM2.5 caught={data['pm2_5']['caught']}, escaped={data['pm2_5']['escaped']}; "
              f"PM10 caught={data['pm10']['caught']}, escaped={data['pm10']['escaped']}")

    try:
        plot_percent_caught(results)
    except ImportError:
        print("matplotlib not available; skip percent-caught plotting.")




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
    num_particles=5000,
    dt=0.01,
    max_time=100.0,
    tower_x=0.0,
    tower_height=60.0,
    catch_distance=0.01,
    spawn_x_min=-20.0,
    spawn_x_max=20.0,
    spawn_y_min=40.0,
    spawn_y_max=80.0,
    boundary_x_min=None,
    boundary_x_max=None,
    boundary_y_min=None,
    boundary_y_max=None,
    air_kwargs=None,
    particle_type="pm2_5",
    sampling_distribution=None,
    wind_x_range=(-2.0,2.0),
):
    air_kwargs = air_kwargs or {}
    air = Air(**air_kwargs)

    # Escape boundary defaults to spawn boundary if not passed
    if boundary_x_min is None:
        boundary_x_min = spawn_x_min
    if boundary_x_max is None:
        boundary_x_max = spawn_x_max
    if boundary_y_min is None:
        boundary_y_min = spawn_y_min
    if boundary_y_max is None:
        boundary_y_max = spawn_y_max

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

    collisions = []

    # Determine per-particle sampling distribution
    if sampling_distribution is None:
        sampling_distribution = {"pm2_5": 0.5, "pm10": 0.5}

    keys = list(sampling_distribution.keys())
    weights = [sampling_distribution[k] for k in keys]
    weight_sum = sum(weights)
    if weight_sum <= 0:
        raise ValueError("sampling_distribution weights must be positive")
    weights = [w / weight_sum for w in weights]

    # random wind speed for each simulation run (horizontal only)
    wind_speed = [random.uniform(*wind_x_range), 0.0]
    air.velocity = wind_speed

    particles = []
    for i in range(num_particles):
        p = spawn_random_smog_particle(spawn_x_min=spawn_x_min, spawn_x_max=spawn_x_max, spawn_y_min=spawn_y_min, spawn_y_max=spawn_y_max)

        chosen = random.choices(keys, weights=weights, k=1)[0]
        if chosen not in particle_presets:
            raise ValueError(f"Invalid particle type in sampling_distribution: {chosen}")
        preset = particle_presets[chosen]

        p.mass = preset["mass"]
        p.diameter = preset["diameter"]
        p.radius = p.diameter / 2.0
        p.volume = 4.0 / 3.0 * math.pi * p.radius ** 3
        p.density = preset["density"]
        particles.append({"id": i, "particle": p, "status": None, "time": 0.0, "type": chosen})

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
            "type": entry.get("type", particle_type),
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
        import matplotlib
        matplotlib.use('Agg')
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

    if matplotlib.get_backend().lower() != 'agg':
        try:
            plt.show()
        except Exception:
            print("plt.show() did not work, but figure is saved to file.")
    else:
        print("Headless backend used (Agg); cannot display interactive window, view saved file.")


def plot_monthly_caught_histograms(monthly_results, out_dir='monthly_caught_hists', csv_path='monthly_caught.csv', show_plots=True):
    import os
    import csv
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting, install with: pip install matplotlib")

    os.makedirs(out_dir, exist_ok=True)

    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = [
            'month', 'pm2_5_caught', 'pm2_5_escaped', 'pm10_caught', 'pm10_escaped',
            'pm2_5_percent_caught', 'pm10_percent_caught'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for month, samples in monthly_results.items():
            pm2_5_caught = sum(sample['pm2_5_caught'] for sample in samples)
            pm2_5_total = sum(sample['pm2_5_total'] for sample in samples)
            pm10_caught = sum(sample['pm10_caught'] for sample in samples)
            pm10_total = sum(sample['pm10_total'] for sample in samples)

            pm25_perc = 100.0 * pm2_5_caught / (pm2_5_total + 1e-12)
            pm10_perc = 100.0 * pm10_caught / (pm10_total + 1e-12)

            writer.writerow({
                'month': month,
                'pm2_5_caught': pm2_5_caught,
                'pm2_5_escaped': pm2_5_total - pm2_5_caught,
                'pm10_caught': pm10_caught,
                'pm10_escaped': pm10_total - pm10_caught,
                'pm2_5_percent_caught': pm25_perc,
                'pm10_percent_caught': pm10_perc,
            })

            percent_samples_pm25 = [sample['pm2_5_percent_caught'] for sample in samples]
            percent_samples_pm10 = [sample['pm10_percent_caught'] for sample in samples]

            plt.figure(figsize=(8, 4))
            plt.hist(percent_samples_pm25, bins=10, alpha=0.6, label='PM2.5')
            plt.hist(percent_samples_pm10, bins=10, alpha=0.6, label='PM10')
            plt.xlabel('Percent caught (%)')
            plt.ylabel('Frequency')
            plt.title(f'{month} sampling distribution ({len(samples)} samples)')
            plt.legend()
            plt.tight_layout()

            filename_sampling = os.path.join(out_dir, f'{month.lower()}_sampling_hist.png')
            plt.savefig(filename_sampling)
            if show_plots:
                plt.show()
            plt.close()
            print(f"Saved sampling histogram for {month} to {filename_sampling}")

    print(f"Saved monthly aggregated CSV data to {csv_path}")


def sampling_histograms_by_month(monthly_results, samples=100, out_dir='monthly_sampling_hists'):
    import os
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting, install with: pip install matplotlib")

    os.makedirs(out_dir, exist_ok=True)

    for month, stats_list in monthly_results.items():
        # stats_list is a list of dicts with pm values
        pm25_percentages = [s['pm2_5_percent_caught'] for s in stats_list]
        pm10_percentages = [s['pm10_percent_caught'] for s in stats_list]

        plt.figure(figsize=(8, 4))
        plt.hist(pm25_percentages, bins=10, alpha=0.6, label='PM2.5')
        plt.hist(pm10_percentages, bins=10, alpha=0.6, label='PM10')
        plt.xlabel('Percent caught (%)')
        plt.ylabel('Frequency')
        plt.title(f'{month} sampling distribution ({samples} samples)')
        plt.legend()
        plt.tight_layout()

        sample_file = os.path.join(out_dir, f'{month.lower()}_sampling_hist.png')
        plt.savefig(sample_file)
        plt.show()
        plt.close()
        print(f"Saved sampling histogram for {month} to {sample_file}")



def simulate_monthly_smog_tower(
    num_particles=1000,
    dt=0.01,
    max_time=180.0,
    tower_x=0.0,
    tower_height=60.0,
    catch_distance=0.01,
    spawn_x_min=-20.0,
    spawn_x_max=20.0,
    spawn_y_min=40.0,
    spawn_y_max=80.0,
    boundary_x_min=None,
    boundary_x_max=None,
    boundary_y_min=None,
    boundary_y_max=None,
    sampling_distribution=None,
    wind_x_range=(-2.0, 2.0),
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
            sampling_distribution=sampling_distribution,
            wind_x_range=wind_x_range,
        )

        pm2_5_caught = sum(1 for p in hits if p["type"] == "pm2_5" and p["status"] == "caught")
        pm2_5_escaped = sum(1 for p in hits if p["type"] == "pm2_5" and p["status"] == "escaped")
        pm10_caught = sum(1 for p in hits if p["type"] == "pm10" and p["status"] == "caught")
        pm10_escaped = sum(1 for p in hits if p["type"] == "pm10" and p["status"] == "escaped")

        monthly_results[month] = {
            "pm2_5": {"caught": pm2_5_caught, "escaped": pm2_5_escaped},
            "pm10": {"caught": pm10_caught, "escaped": pm10_escaped},
        }

    return monthly_results


def simulate_monthly_sampling(
    samples=100,
    num_particles=10000,
    dt=0.01,
    max_time=180.0,
    tower_x=0.0,
    tower_height=60.0,
    catch_distance=0.01,
    spawn_x_min=-10.0,
    spawn_x_max=10.0,
    spawn_y_min=30.0,
    spawn_y_max=70.0,
    boundary_x_min=-10.0,
    boundary_x_max=10.0,
    boundary_y_min=30.0,
    boundary_y_max=70.0,
    sampling_distribution=None,
    wind_x_range=(-1.0, 1.0),
):
    monthly_density = {
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

    monthly_samples = {}
    for month, density in monthly_density.items():
        monthly_samples[month] = []
        for s in range(samples):
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
                sampling_distribution=sampling_distribution,
                wind_x_range=wind_x_range,
            )
            pm2_5_caught = sum(1 for p in hits if p["type"] == "pm2_5" and p["status"] == "caught")
            pm2_5_total = sum(1 for p in hits if p["type"] == "pm2_5")
            pm10_caught = sum(1 for p in hits if p["type"] == "pm10" and p["status"] == "caught")
            pm10_total = sum(1 for p in hits if p["type"] == "pm10")

            pm2_5_percent = 100.0 * pm2_5_caught / (pm2_5_total + 1e-12)
            pm10_percent = 100.0 * pm10_caught / (pm10_total + 1e-12)

            monthly_samples[month].append({
                "pm2_5_percent_caught": pm2_5_percent,
                "pm10_percent_caught": pm10_percent,
                "pm2_5_caught": pm2_5_caught,
                "pm2_5_total": pm2_5_total,
                "pm10_caught": pm10_caught,
                "pm10_total": pm10_total,
            })

    return monthly_samples


if __name__ == "__main__":
    monthly_samples = simulate_monthly_sampling(
        samples=100,
        num_particles=10000,
        dt=0.01,
        max_time=180.0,
        spawn_x_min=-10.0,
        spawn_x_max=10.0,
        spawn_y_min=30.0,
        spawn_y_max=70.0,
        boundary_x_min=-10.0,
        boundary_x_max=10.0,
        boundary_y_min=30.0,
        boundary_y_max=70.0,
        sampling_distribution={"pm2_5": 0.7, "pm10": 0.3},
        wind_x_range=(-1.0, 1.0),
    )

    for month, sample_list in monthly_samples.items():
        pm2_5_caught = sum(s['pm2_5_caught'] for s in sample_list)
        pm2_5_total = sum(s['pm2_5_total'] for s in sample_list)
        pm10_caught = sum(s['pm10_caught'] for s in sample_list)
        pm10_total = sum(s['pm10_total'] for s in sample_list)

        print(f"{month}: PM2.5 avg caught %={(100*pm2_5_caught/(pm2_5_total+1e-12)):.3f}, "
              f"PM10 avg caught %={(100*pm10_caught/(pm10_total+1e-12)):.3f}")

    try:
        plot_monthly_caught_histograms(monthly_samples, out_dir='monthly_sampling_hists', csv_path='monthly_sampling.csv', show_plots=False)
    except ImportError:
        print("matplotlib not available; skip plotting.")





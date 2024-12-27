import traci
import pandas as pd

# Metrics for tracking simulation performance
vehicle_travel_times = {}  # Tracks travel times for each vehicle
vehicle_departure_times = {}  # Tracks departure times for each vehicle
queue_lengths = {}  # Queue lengths at traffic lights
green_phase_durations = {}  # Tracks green light durations for each traffic light
red_phase_durations = {}  # Tracks red light durations for each traffic light

# Global variables
output_file = "Logs/performance_data.csv"
metrics_file = "Logs/baseline_metrics.txt"
total_waiting_time = 0  # Total waiting time for all vehicles
throughput = 0  # Total number of vehicles that have arrived
num_cars_entered = 0  # Number of cars that entered the network
tls_ids = []  # List of traffic light IDs


# Initializes metrics before simulation begins
def initialize_metrics():
    """
    Initializes traffic light IDs and metrics for the adaptive traffic control system.
    """
    global tls_ids, total_waiting_time, throughput, num_cars_entered
    try:
        # Retrieve traffic light IDs dynamically from the simulation
        tls_ids = traci.trafficlight.getIDList()
        # Reset metrics
        total_waiting_time = 0
        throughput = 0
        num_cars_entered = 0
        # print("Metrics initialized successfully.")
    except Exception as e:
        print(f"Error initializing metrics: {e}")


# Gathers and processes performance data during each simulation step
def gather_performance_data():
    """
    Collects performance metrics dynamically based on adaptive traffic control inputs.
    Also writes results to CSV and log files.
    """
    global tls_ids, total_waiting_time, throughput, num_cars_entered
    try:
        # Count vehicles entered dynamically
        num_cars_entered += len(traci.simulation.getDepartedIDList())

        # Determine traffic demand dynamically
        if num_cars_entered <= 300:
            traffic_demand = "low"
        elif num_cars_entered <= 600:
            traffic_demand = "mid"
        else:
            traffic_demand = "high"

        # Track data for each traffic light system
        for tls_id in tls_ids:
            # Get the current phase index and state dynamically
            current_phase_index = traci.trafficlight.getPhase(tls_id)
            current_phase = traci.trafficlight.getAllProgramLogics(tls_id)[0].phases[ 
                current_phase_index
            ]

            # Track Green Phase Durations
            if "G" in current_phase.state:
                if tls_id not in green_phase_durations:
                    green_phase_durations[tls_id] = 0
                green_phase_durations[tls_id] += traci.trafficlight.getPhaseDuration(
                    tls_id
                )

            # Track Red Phase Durations
            if "r" in current_phase.state:
                if tls_id not in red_phase_durations:
                    red_phase_durations[tls_id] = 0
                red_phase_durations[tls_id] += traci.trafficlight.getPhaseDuration(
                    tls_id
                )

            # Track Queue Lengths dynamically
            if tls_id not in queue_lengths:
                queue_lengths[tls_id] = 0
            queue_lengths[tls_id] = max(
                queue_lengths[tls_id],
                sum(
                    traci.lane.getLastStepHaltingNumber(lane)
                    for lane in traci.trafficlight.getControlledLanes(tls_id)
                ),
            )

        # Vehicle Metrics
        for vehicle_id in traci.simulation.getDepartedIDList():
            vehicle_departure_times[vehicle_id] = traci.simulation.getTime()

        for vehicle_id in traci.simulation.getArrivedIDList():
            throughput += 1  # Increment throughput for each vehicle that arrives
            if vehicle_id in vehicle_departure_times:
                travel_time = (
                    traci.simulation.getTime() - vehicle_departure_times[vehicle_id]
                )
                vehicle_travel_times[vehicle_id] = travel_time

        for vehicle_id in traci.vehicle.getIDList():
            try:
                total_waiting_time += traci.vehicle.getWaitingTime(vehicle_id)
            except traci.exceptions.TraCIException as e:
                print(
                    f"Warning: Failed to get waiting time for vehicle {vehicle_id}. {e}"
                )

        # Write metrics to CSV file dynamically
        data = []
        for tls_id in tls_ids:
            avg_travel_time = (
                sum(vehicle_travel_times.values()) / len(vehicle_travel_times)
                if vehicle_travel_times
                else 0
            )
            data.append(
                [
                    tls_id,
                    traffic_demand,
                    green_phase_durations.get(tls_id, 0),
                    red_phase_durations.get(tls_id, 0),
                    total_waiting_time,
                    avg_travel_time,
                    throughput,  # Ensure throughput is correctly included
                    queue_lengths.get(tls_id, 0),
                ]
            )

        # Save to CSV file
        try:
            df = pd.DataFrame(
                data,
                columns=[
                    "id",
                    "traffic_demand",
                    "green_phase_duration",
                    "red_phase_duration",
                    "total_waiting_time",
                    "avg_travel_time",
                    "throughput",
                    "queue_length",
                ],
            )
            df.to_csv(output_file, index=False)
        except Exception as e:
            print(f"Error writing CSV file: {e}")

        # Write metrics log file
        with open(metrics_file, "w") as file:
            file.write("Adaptive Traffic Control Metrics\n")
            file.write("=" * 40 + "\n")
            file.write(f"-Average Vehicle Travel Time: {avg_travel_time:.2f} seconds\n")
            file.write(f"-Total Waiting Time: {total_waiting_time:.2f} seconds\n")
            file.write(f"-Queue Lengths at Traffic Lights:\n")
            for tls_id, queue_length in queue_lengths.items():
                file.write(f" {tls_id}: {queue_length} vehicles\n")

        # print(f"Metrics successfully written to {output_file}")

    except Exception as e:
        print(f"Error in performance testing: {e}")

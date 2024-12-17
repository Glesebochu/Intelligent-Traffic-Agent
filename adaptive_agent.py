import traci  
import os
from traci._trafficlight import Logic, Phase

sumoBinary = "sumo-gui"
sumoConfig = "basemap/basemap.sumocfg"  # Your configuration file

log_file = "adaptive_tl_log.txt"
metrics_file = "adaptive_metrics.txt"

# Performance metrics
vehicle_travel_times = {}
vehicle_departure_times = {}
total_waiting_time = 0
queue_lengths = {}

# Adaptive logic configuration
MIN_GREEN_TIME = 5
MAX_GREEN_TIME = 30
YELLOW_TIME = 3

def set_adaptive_timing(tls_id):
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    green_time = calculate_green_time(controlled_lanes)

    phases = [
        Phase(green_time, "G"),  # Green phase
        Phase(YELLOW_TIME, "y"),  # Yellow phase
        Phase(green_time, "rG"),  # Reverse green phase
        Phase(YELLOW_TIME, "ry"),  # Reverse yellow phase
    ]

    logic = Logic("adaptive_program", 0, 0, phases)
    traci.trafficlight.setProgramLogic(tls_id, logic)

def calculate_green_time(controlled_lanes):
    total_queue = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in controlled_lanes)
    green_time = max(MIN_GREEN_TIME, min(MAX_GREEN_TIME, total_queue * 2))
    return green_time

def collect_metrics():
    global total_waiting_time

    for vehicle_id in traci.simulation.getDepartedIDList():
        vehicle_departure_times[vehicle_id] = traci.simulation.getTime()

    for vehicle_id in traci.simulation.getArrivedIDList():
        if vehicle_id in vehicle_departure_times:
            travel_time = traci.simulation.getTime() - vehicle_departure_times[vehicle_id]
            vehicle_travel_times[vehicle_id] = travel_time

    for vehicle_id in traci.vehicle.getIDList():
        try:
            waiting_time = traci.vehicle.getWaitingTime(vehicle_id)
            total_waiting_time += waiting_time
        except traci.exceptions.TraCIException as e:
            print(f"Warning: Failed to get waiting time for vehicle {vehicle_id}. {e}")

    for tls_id in traci.trafficlight.getIDList():
        queue_lengths[tls_id] = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in traci.trafficlight.getControlledLanes(tls_id))

def calculate_avg_travel_time(): 
    if len(vehicle_travel_times) > 0:
        return sum(vehicle_travel_times.values()) / len(vehicle_travel_times)
    return 0

def write_metrics_to_file():
    try:
        with open(metrics_file, "w") as file:
            file.write("Adaptive Traffic Control Metrics\n")
            file.write("=" * 40 + "\n")
            average_travel_time = calculate_avg_travel_time()
            file.write(f"- Average Vehicle Travel Time: {average_travel_time:.2f} seconds\n")
            file.write(f"- Total Waiting Time: {total_waiting_time:.2f} seconds\n")
            file.write(f"- Queue Lengths at Traffic Lights:\n")
            for tls_id, queue_length in queue_lengths.items():
                file.write(f"  {tls_id}: {queue_length} vehicles\n")

        print(f"Metrics successfully written to {metrics_file}")
    except Exception as e:
        print(f"Error writing metrics: {e}")

def run_adaptive():
    try:
        with open(log_file, "w") as log_handle:
            traci.start([sumoBinary, "-c", sumoConfig])

            log_handle.write("Adaptive Traffic Light Phase Log\n")
            log_handle.write("=" * 40 + "\n")

            tls_ids = traci.trafficlight.getIDList()
            log_handle.write(f"Detected Traffic Lights: {tls_ids}\n")

            simulation_end_time = 700

            while (traci.simulation.getTime() < simulation_end_time and 
                   traci.simulation.getMinExpectedNumber() > 0):
                traci.simulationStep()
                for tls_id in tls_ids:
                    set_adaptive_timing(tls_id)
                collect_metrics()

            log_handle.write("Simulation ended.\n")
            print(f"Adaptive traffic light operations logged to {log_file}")

    finally:
        write_metrics_to_file()
        traci.close()

if __name__ == "__main__":
    try:
        run_adaptive()
    except Exception as e:
        print(f"Error: {e}")
        traci.close()

import traci
import logging

# Configure logging
logging.basicConfig(
    filename="Logs/simulation_log.txt",  # Log file for storing simulation outputs
    level=logging.INFO,             # Log level (INFO for standard outputs)
    format="%(asctime)s - %(message)s",  # Log format with timestamps
    filemode="w",                    # Overwrite log file every time the script runs
)

# Global variables to store cumulative metrics across runs
total_travel_time = 0
total_waiting_time = 0
total_throughput = 0
total_queue_length = 0
runs = 5  # Number of simulation runs

# Define logging functions (already provided in your script)
def log_traffic_light_phases():
    traffic_light_ids = traci.trafficlight.getIDList()
    for tls_id in traffic_light_ids:
        controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
        phases = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0].phases
        logging.info(f"Traffic Light ID: {tls_id}")
        logging.info(f"Controlled Lanes: {controlled_lanes}")
        for i, phase in enumerate(phases):
            logging.info(f"Phase {i}: Duration = {phase.duration}s, State = {phase.state}")
        logging.info("-" * 40)

def log_average_travel_time():
    global total_travel_time
    try:
        travel_times = []
        vehicle_ids = traci.vehicle.getIDList()
        for veh_id in vehicle_ids:
            travel_times.append(traci.vehicle.getAccumulatedTravelTime(veh_id))
        if travel_times:
            avg_travel_time = sum(travel_times) / len(travel_times)
            total_travel_time += avg_travel_time  # Accumulate for average calculation
            logging.info(f"Average Travel Time (Run): {avg_travel_time:.2f} seconds")
        else:
            logging.info("No vehicles to calculate average travel time.")
    except Exception as e:
        logging.error(f"Error while calculating average travel time: {e}")

def log_total_waiting_time():
    global total_waiting_time
    try:
        total_waiting = 0
        vehicle_ids = traci.vehicle.getIDList()
        for veh_id in vehicle_ids:
            total_waiting += traci.vehicle.getWaitingTime(veh_id)
        total_waiting_time += total_waiting  # Accumulate for average calculation
        logging.info(f"Total Waiting Time (Run): {total_waiting:.2f} seconds")
    except Exception as e:
        logging.error(f"Error while calculating total waiting time: {e}")

def log_queue_lengths():
    global total_queue_length
    try:
        traffic_light_ids = traci.trafficlight.getIDList()
        run_queue_length = 0
        for tls_id in traffic_light_ids:
            controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
            for lane in controlled_lanes:
                run_queue_length += traci.lane.getLastStepHaltingNumber(lane)
        total_queue_length += run_queue_length  # Accumulate for average calculation
        logging.info(f"Total Queue Length (Run): {run_queue_length} vehicles")
    except Exception as e:
        logging.error(f"Error while calculating queue lengths: {e}")

def log_throughput():
    global total_throughput
    try:
        throughput = traci.simulation.getArrivedNumber()
        total_throughput += throughput  # Accumulate for average calculation
        logging.info(f"Throughput (Run): {throughput} vehicles exited the network")
    except Exception as e:
        logging.error(f"Error while calculating throughput: {e}")

# Function to run the simulation
def run_simulation():
    logging.info("Starting Simulation Run")
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        run_all_tests()
    logging.info("Simulation Run Completed")

# Run the simulations multiple times and compute averages
def main():
    global total_travel_time, total_waiting_time, total_throughput, total_queue_length
    for run in range(1, runs + 1):
        logging.info(f"--- Starting Run {run} ---")
        traci.start(["sumo-gui", "-c", "path/to/your_config.sumocfg"])  # Replace with your config path
        run_simulation()
        traci.close()
        logging.info(f"--- Ended Run {run} ---")

    # Calculate averages after all runs
    avg_travel_time = total_travel_time / runs
    avg_waiting_time = total_waiting_time / runs
    avg_throughput = total_throughput / runs
    avg_queue_length = total_queue_length / runs

    # Log the averages
    logging.info("=== Final Averages Across All Runs ===")
    logging.info(f"Average Travel Time: {avg_travel_time:.2f} seconds")
    logging.info(f"Average Waiting Time: {avg_waiting_time:.2f} seconds")
    logging.info(f"Average Throughput: {avg_throughput:.2f} vehicles")
    logging.info(f"Average Queue Length: {avg_queue_length:.2f} vehicles")

if __name__ == "__main__":
    main()

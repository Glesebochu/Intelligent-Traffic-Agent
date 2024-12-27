import traci
import os
from traci._trafficlight import Logic, Phase
import pandas as pd

# SUMO configuration
sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"
output_file = "baseline_performance_metrics.csv"
log_file = "Logs/fixed_tl_log.txt"
metrics_file = "Logs/baseline_metrics.txt"

# Traffic light phase definitions for intersections
fixed_phases_dict = {
    1: [Phase(40, "G"), Phase(4, "y"), Phase(40, "r"), Phase(4, "r")],
    2: [Phase(40, "Gr"), Phase(4, "yr"), Phase(40, "rG"), Phase(4, "ry")],
    3: [Phase(40, "Grr"), Phase(4, "yrr"), Phase(40, "rGr"), Phase(4, "ryr")],
    4: [Phase(40, "Grrr"), Phase(5, "yrrr"), Phase(40, "rGGG"), Phase(5, "rrrr")],
    5: [Phase(40, "Grrrr"), Phase(5, "yrrrr"), Phase(40, "rGGGG"), Phase(5, "rrrrr")],
    6: [
        Phase(40, "GGGrrr"),
        Phase(6, "yyyrrr"),
        Phase(40, "rrrGGG"),
        Phase(6, "rrryyy"),
    ],
    7: [
        Phase(40, "GGGrrrr"),
        Phase(6, "yyyrrrr"),
        Phase(40, "rrrGGGG"),
        Phase(6, "rrryyyy"),
    ],
    8: [
        Phase(40, "GGGGrrrr"),
        Phase(7, "yyyyrrrr"),
        Phase(40, "rrrrGGGG"),
        Phase(7, "rrrryyyy"),
    ],
    9: [
        Phase(40, "GGGGGrrrrr"),
        Phase(7, "yyyyyrrrrr"),
        Phase(40, "rrrrrGGGGG"),
        Phase(7, "rrrrryyyyy"),
    ],
    10: [
        Phase(40, "GGGGGGrrrrrr"),
        Phase(8, "yyyyyyrrrrrr"),
        Phase(40, "rrrrrrGGGGGG"),
        Phase(8, "rrrrrryyyyyy"),
    ],
    11: [
        Phase(40, "GGGGGGGrrrrrrr"),
        Phase(8, "yyyyyyyrrrrrrr"),
        Phase(40, "rrrrrrrGGGGGGG"),
        Phase(8, "rrrrrrryyyyyyy"),
    ],
    12: [
        Phase(40, "GGGGGGGGrrrrrrrr"),
        Phase(8, "yyyyyyyyrrrrrrrr"),
        Phase(40, "rrrrrrrrGGGGGGGG"),
        Phase(8, "rrrrrrrryyyyyyyy"),
    ],
    13: [
        Phase(40, "GGGGGGGGGrrrrrrrrr"),
        Phase(9, "yyyyyyyyyrrrrrrrrr"),
        Phase(40, "rrrrrrrrrGGGGGGGGG"),
        Phase(9, "rrrrrrrrryyyyyyyyy"),
    ],
    14: [
        Phase(40, "GGGGGGGGGGrrrrrrrrrr"),
        Phase(9, "yyyyyyyyyyrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrGGGGGGGGGG"),
        Phase(9, "rrrrrrrrrryyyyyyyyyy"),
    ],
    15: [
        Phase(40, "GGGGGGGGGGGrrrrrrrrrrr"),
        Phase(10, "yyyyyyyyyyyrrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrrGGGGGGGGGGG"),
        Phase(10, "rrrrrrrrrrryyyyyyyyyyy"),
    ],
    16: [
        Phase(40, "GGGGGGGGGGGGrrrrrrrrrrrr"),
        Phase(10, "yyyyyyyyyyyyrrrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrrrGGGGGGGGGGGG"),
        Phase(10, "rrrrrrrrrrrryyyyyyyyyyyy"),
    ],
    17: [
        Phase(40, "GGGGGGGGGGGGGrrrrrrrrrrrrr"),
        Phase(10, "yyyyyyyyyyyyyrrrrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrrrrGGGGGGGGGGGGG"),
        Phase(10, "rrrrrrrrrrrrryyyyyyyyyyyyy"),
    ],
    18: [
        Phase(40, "GGGGGGGGGGGGGGrrrrrrrrrrrrrr"),
        Phase(11, "yyyyyyyyyyyyyyrrrrrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrrrrrGGGGGGGGGGGGGG"),
        Phase(11, "rrrrrrrrrrrrrryyyyyyyyyyyyyy"),
    ],
    19: [
        Phase(40, "GGGGGGGGGGGGGGGrrrrrrrrrrrrrrr"),
        Phase(11, "yyyyyyyyyyyyyyyrrrrrrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrrrrrrGGGGGGGGGGGGGGG"),
        Phase(11, "rrrrrrrrrrrrrrryyyyyyyyyyyyyyy"),
    ],
    20: [
        Phase(40, "GGGGGGGGGGGGGGGGrrrrrrrrrrrrrrrr"),
        Phase(12, "yyyyyyyyyyyyyyyyrrrrrrrrrrrrrrrr"),
        Phase(40, "rrrrrrrrrrrrrrrrGGGGGGGGGGGGGGGG"),
        Phase(12, "rrrrrrrrrrrrrrrryyyyyyyyyyyyyyyy"),
    ],
}
# Metrics
vehicle_travel_times = {}
vehicle_departure_times = {}
total_waiting_time = 0
queue_lengths = {}
throughput = 0
traffic_demand = "low"

# Store metrics
green_phase_durations = {}  # {tls_id: duration}
red_phase_durations = {}  # {tls_id: duration}
num_cars_entered = 0


def track_phase_durations(tls_id):
    # Get the current phase index and state
    current_phase_index = traci.trafficlight.getPhase(tls_id)
    current_phase = traci.trafficlight.getAllProgramLogics(tls_id)[0].phases[
        current_phase_index
    ]

    # Track green phase durations
    if "G" in current_phase.state:
        if tls_id not in green_phase_durations:
            green_phase_durations[tls_id] = 0
        green_phase_durations[tls_id] += traci.trafficlight.getPhaseDuration(tls_id)

    # Track red phase durations
    if "r" in current_phase.state:
        if tls_id not in red_phase_durations:
            red_phase_durations[tls_id] = 0
        red_phase_durations[tls_id] += traci.trafficlight.getPhaseDuration(tls_id)


def set_fixed_timing(tls_id):
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    num_lanes = len(controlled_lanes)

    if num_lanes in fixed_phases_dict:
        # Retrieve phases from the dictionary based on lane count
        phases = fixed_phases_dict[num_lanes]
        # print(f"TLS {tls_id} Total Green Phase Duration: {total_green_duration}s")
        logic = Logic("fixed_program", 0, 0, phases)
        traci.trafficlight.setProgramLogic(tls_id, logic)
    else:
        print(f"Unsupported lane count {num_lanes} at traffic light {tls_id}")


def run_baseline():
    global num_cars_entered, total_waiting_time, throughput
    # Open a log file to record traffic light operations
    try:
        with open(log_file, "w") as log_handle:
            traci.start([sumoBinary, "-c", sumoConfig])
            # Count cars dynamically as they enter
            num_cars_entered = 0

            log_handle.write("Traffic Light Phase Log\n")
            log_handle.write("=" * 40 + "\n")

            tls_ids = traci.trafficlight.getIDList()
            log_handle.write(f"Detected Traffic Lights: {tls_ids}\n")

            for tls_id in tls_ids:
                set_fixed_timing(tls_id)
                log_handle.write(
                    f"Dynamic fixed timing set for traffic light: {tls_id}\n"
                )

            # Run the simulation
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()  # Advance the simulation
                # Count cars as they enter dynamically
                num_cars_entered += len(traci.simulation.getDepartedIDList())
                # Metrics collection
                for tls_id in traci.trafficlight.getIDList():
                    track_phase_durations(tls_id)

                for vehicle_id in traci.simulation.getDepartedIDList():
                    vehicle_departure_times[vehicle_id] = traci.simulation.getTime()
                # Get throughput
                for vehicle_id in traci.simulation.getArrivedIDList():
                    throughput += 1
                    if vehicle_id in vehicle_departure_times:
                        travel_time = (
                            traci.simulation.getTime()
                            - vehicle_departure_times[vehicle_id]
                        )
                    vehicle_travel_times[vehicle_id] = travel_time
                # Get total waiting time
                for vehicle_id in traci.vehicle.getIDList():
                    try:
                        total_waiting_time += traci.vehicle.getWaitingTime(vehicle_id)
                    except traci.exceptions.TraCIException as e:
                        print(
                            f"Warning: Failed to get waiting time for vehicle {vehicle_id}. {e}"
                        )
                # Get queue length
                # print(
                #     f"Number of traffic light IDs: {len(traci.trafficlight.getIDList())}"
                # )
                # print(f"COntrolled lanes: {len(traci.trafficlight.getControlledLanes())}")
                for tls_id in traci.trafficlight.getIDList():
                    # print(f"Number of controlled lanes for traffic light {tls_id}: {len(traci.trafficlight.getControlledLanes(tls_id))}")
                    # print(f"T")
                    # queue_lengths[tls_id] = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in traci.trafficlight.getControlledLanes(tls_id))
                    if tls_id not in queue_lengths:
                        queue_lengths[tls_id] = 0  # Initialize
                    queue_lengths[tls_id] = max(
                        queue_lengths[tls_id],  # Keep the max value so far
                        sum(
                            traci.lane.getLastStepHaltingNumber(lane)
                            for lane in traci.trafficlight.getControlledLanes(tls_id)
                        ),
                    )
            # print(f"Queue length: {queue_lengths}")
            # print(f"num of cars: {num_cars_entered}")
            for tls_id in traci.trafficlight.getIDList():
                print(
                    f"TLS {tls_id} - Green Phase Duration: {green_phase_durations.get(tls_id, 0)}s, Red Phase Duration: {red_phase_durations.get(tls_id, 0)}s"
                )
            # Determine traffic demand
            if num_cars_entered <= 300:
                traffic_demand = "low"
            elif num_cars_entered <= 600:
                traffic_demand = "mid"
            else:
                traffic_demand = "high"

            avg_travel_time = (
                sum(vehicle_travel_times.values()) / len(vehicle_travel_times)
                if vehicle_travel_times
                else 0
            )
            # total_queue_length = sum(queue_lengths.values())

            # Write metrics to CSV
            data = []
            for tls_id in traci.trafficlight.getIDList():
                data.append(
                    [
                        tls_id,
                        traffic_demand,
                        green_phase_durations.get(tls_id, 0),
                        red_phase_durations.get(tls_id, 0),
                        total_waiting_time,
                        avg_travel_time,
                        throughput,
                        queue_lengths.get(tls_id, 0),  # Include queue length
                    ]
                )
                # print(data)
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

            try:
                with open(metrics_file, "w") as file:
                    file.write("Baseline Traffic Control Metrics\n")
                    file.write("=" * 40 + "\n")
                    file.write(
                        f"-Average Vehicle Travel Time: {avg_travel_time:.2f} seconds\n"
                    )
                    file.write(
                        f"-Total Waiting Time: {total_waiting_time:.2f} seconds\n"
                    )
                    file.write(f"-Queue Lengths at Traffic Lights:\n")
                    for tls_id, queue_length in queue_lengths.items():
                        file.write(f" {tls_id}: {queue_length} vehicles\n")

                print(f"Metrics successfully written to {metrics_file}")
            except Exception as e:
                print(f"Error writing metrics: {e}")

            # End the simulation
            log_handle.write("Simulation ended.\n")
            print(f"Traffic light operations logged to {log_file}")

            traci.close()

    except Exception as e:
        print(f"Error: {e}")
        traci.close()


# Main execution
if __name__ == "__main__":
    try:
        run_baseline()
    except Exception as e:
        print(f"Error: {e}")
        traci.close()

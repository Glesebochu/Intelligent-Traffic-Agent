# import traci
# import os
# import json
# from traci._trafficlight import Logic, Phase

# # Configuration
# sumoBinary = "sumo-gui"
# sumoConfig = "CustomNetworks/oneLaneMap.sumocfg"
# adaptive_phases_file = "adaptive_fixed_phases.json"

# # Adaptive control parameters
# MIN_GREEN = 10
# MAX_GREEN = 50
# QUEUE_THRESHOLD = 3  # Below this, revert to fixed-time schedule
# STEP_INTERVAL = 3  # Frequency of adapting phases (in simulation steps)

# def get_dynamic_phases(tls_id, fixed_phases, queue_lengths):
#     """Adjust phase durations dynamically based on queue lengths."""
#     dynamic_phases = []
#     total_queue = sum(queue_lengths.values())

#     # Access phases directly from the fixed_phases dictionary
#     for phase in fixed_phases[tls_id]:  # List of phases for this TLS ID
#         phase_state = phase["state"]
#         phase_duration = phase["duration"]

#         if "G" in phase_state:  # Adjust green phases dynamically
#             # Calculate the total queue for the lanes with green signals
#             green_queue = sum(
#                 queue_lengths.get(road_id, 0)
#                 for road_id in queue_lengths.keys()
#                 if any(phase_state[i] == "G" for i, road_id in enumerate(queue_lengths.keys()))
#             )
#             # Adjust green duration proportionally
#             if total_queue > 0 and green_queue > 0:
#                 adjusted_duration = max(
#                     MIN_GREEN,
#                     min(MAX_GREEN, (green_queue / total_queue) * MAX_GREEN),
#                 )
#                 dynamic_phases.append(Phase(int(adjusted_duration), phase_state))
#             else:
#                 dynamic_phases.append(Phase(phase_duration, phase_state))
#         else:  # Keep yellow/red phases fixed
#             dynamic_phases.append(Phase(phase_duration, phase_state))

#     return dynamic_phases

# def set_adaptive_timing(tls_id, fixed_phases, queue_lengths):
#     """Set adaptive traffic light timing."""
#     dynamic_phases = get_dynamic_phases(tls_id, fixed_phases, queue_lengths)
#     logic = Logic("adaptive_program", 0, 0, dynamic_phases)
#     traci.trafficlight.setProgramLogic(tls_id, logic)

# def run_adaptive_agent():
#     """Main function to run the adaptive traffic control agent."""
#     traci.start([sumoBinary, "-c", sumoConfig])

#     # Load fixed phase data
#     fixed_phases = load_adaptive_phases(adaptive_phases_file)

#     # Get all traffic lights
#     tls_ids = traci.trafficlight.getIDList()

#     simulation_end_time = 1000
#     step = 0
#     while traci.simulation.getTime() < simulation_end_time:
#         traci.simulationStep()
#         step += 1

#         # Every STEP_INTERVAL steps, adapt the timing
#         if step % STEP_INTERVAL == 0:
#             for tls_id in tls_ids:
#                 # Dynamically update queue lengths
#                 queue_lengths = {}
#                 controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
#                 for lane in controlled_lanes:
#                     road_id = lane.split("_")[0]  # Extract road ID from lane
#                     queue_lengths[road_id] = queue_lengths.get(road_id, 0) + traci.lane.getLastStepHaltingNumber(lane)

#                 # Check if total queue exceeds threshold
#                 total_queue = sum(queue_lengths.values())
#                 if total_queue > QUEUE_THRESHOLD:
#                     # Adjust timing adaptively
#                     # set_adaptive_timing(tls_id, fixed_phases, queue_lengths)
#                     fixed_phases_data = [
#                         Phase(phase["duration"], phase["state"])
#                         for phase in fixed_phases[tls_id]
#                     ]
#                     logic = Logic("fixed_program", 0, 0, fixed_phases_data)
#                     traci.trafficlight.setProgramLogic(tls_id, logic)

#                 else:
#                     # Revert to fixed-time schedule
#                     fixed_phases_data = [
#                         Phase(phase["duration"], phase["state"])
#                         for phase in fixed_phases[tls_id]
#                     ]
#                     logic = Logic("fixed_program", 0, 0, fixed_phases_data)
#                     traci.trafficlight.setProgramLogic(tls_id, logic)

#     traci.close()

# def load_adaptive_phases(file_path):
#     """Load traffic light phases directly from JSON."""
#     with open(file_path, "r") as f:
#         return json.load(f)

# if __name__ == "__main__":
#     try:
#         run_adaptive_agent()
#     except Exception as e:
#         print(f"Error: {e}")
#         if traci.isLoaded():
#             traci.close()


import traci
import os
import json
import sumolib
import pandas as pd
from traci._trafficlight import Logic, Phase
import copy

# Configuration
import os

# Ensure file paths are absolute and robust
script_dir = os.path.dirname(os.path.abspath(__file__))
sumoBinary = "sumo-gui"
sumoConfig = os.path.join(script_dir, "CustomNetworks", "twoLaneMap.sumocfg")
adaptive_phases_file = os.path.join(script_dir, "adaptive_fixed_phases.json")

# Ensure adaptive phases file exists
if not os.path.exists(adaptive_phases_file):
    raise FileNotFoundError(f"Adaptive phases file not found: {adaptive_phases_file}")

# Adaptive control parameters
MIN_GREEN = 15
MAX_GREEN = 45
QUEUE_THRESHOLD = 3
STEP_INTERVAL = 3
rt_traffic_data = {"avg_speed": [], "queue_length": []}

#A function that calculates average speed
def get_average_speed(edge_id):
    
    try:
        # Retrieve the average speed of vehicles on the edge
        avg_speed = traci.edge.getLastStepMeanSpeed(edge_id)
        return avg_speed if avg_speed is not None else 0
    except traci.TraCIException as e:
        # Handle TraCI exceptions gracefully
        print(f"Error retrieving average speed for edge {edge_id}: {e}")
        return 0
    except Exception as e:
        # Handle any unexpected errors
        print(f"Unexpected error in get_average_speed for edge {edge_id}: {e}")
        return 0

#A function that collects average queue length
def get_road_queues(tls_id, step):
    
    queue_lengths = {}
    seen_lanes = set()  # Avoid duplicate lane processing

    try:
        # Get the lanes controlled by the traffic light system
        tl_lanes = traci.trafficlight.getControlledLanes(tls_id)
        print(f"Step {step} - Traffic light {tls_id} controls lanes: {tl_lanes}")

        for lane in tl_lanes:
            if lane in seen_lanes:
                continue  # Skip duplicate lanes
            seen_lanes.add(lane)

            # Extract road ID from the lane name
            road_id = lane.split("_")[0]

            # Retrieve the number of halting vehicles in the lane
            try:
                halting_vehicles = traci.lane.getLastStepHaltingNumber(lane)
            except traci.TraCIException as e:
                print(f"Error retrieving halting number for lane {lane}: {e}")
                halting_vehicles = 0  # Default to 0 if retrieval fails

            # Aggregate by road ID
            if road_id not in queue_lengths:
                queue_lengths[road_id] = 0
            queue_lengths[road_id] += halting_vehicles

            # Debug: Print lane-specific queue information
            print(
                f"  Lane {lane} (road {road_id}): {halting_vehicles} vehicles halting."
            )

        # Debug: Print aggregated queue lengths by road
        print(f"Aggregated queue lengths at {tls_id}: {queue_lengths}\n")

    except traci.TraCIException as e:
        print(f"Error retrieving controlled lanes for TLS {tls_id} at step {step}: {e}")
    except Exception as e:
        print(
            f"Unexpected error in get_road_queues for TLS {tls_id} at step {step}: {e}"
        )

    return queue_lengths


def get_green_roads(state, tls_id):
    """Identify which roads have green signal in current state."""
    green_roads = set()
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)

    for i, signal in enumerate(state):
        if signal in ["G", "g"]:
            road_id = controlled_lanes[i].split("_")[0]
            green_roads.add(road_id)

    return green_roads


def calculate_adaptive_duration(base_duration, green_roads, queue_lengths):
    """Calculate adaptive duration based on queue ratios."""
    total_queue = sum(queue_lengths.values())
    if total_queue == 0:
        return base_duration

    # Ensure all roads in green_roads exist in queue_lengths
    green_queue = sum(
        queue_lengths[road] for road in green_roads if road in queue_lengths
    )

    if green_queue == 0:
        return MIN_GREEN

    queue_ratio = green_queue / total_queue
    adapted_duration = base_duration * (1 + queue_ratio)

    return max(MIN_GREEN, min(MAX_GREEN, int(adapted_duration)))

#Main function that runs the adaptive agent
def run_adaptive_agent():
    import traceback  # For detailed error reporting

    try:
        traci.start([sumoBinary, "-c", sumoConfig])

        # Load fixed phase data
        with open(adaptive_phases_file, "r") as f:
            fixed_phases = json.load(f)

        # Initialize phase programs for each intersection
        tls_ids = traci.trafficlight.getIDList()
        current_phases = {}
        for tls_id in tls_ids:
            if tls_id in fixed_phases:
                current_phases[tls_id] = copy.deepcopy(fixed_phases[tls_id])
            else:
                print(f"Warning: No fixed phases found for {tls_id}. Skipping.")



        step = 0
        while step < 20:
            try:
                traci.simulationStep()
                step += 1

                # Data collection for each simulation step
                step_queue_data = {"step": step, "data": []}
                step_speed_data = {"step": step, "data": []}

                # Collect queue lengths
                for tls_id in tls_ids:
                    if tls_id not in fixed_phases:
                        continue

                    try:
                        queue_lengths = get_road_queues(tls_id, step)
                        for road_id, queue_length in queue_lengths.items():
                            step_queue_data["data"].append({
                                "tls_id": tls_id,
                                "road_id": road_id,
                                "queue_length": queue_length,
                            })
                    except Exception as e:
                        print(f"Error collecting queue lengths for TLS {tls_id} at step {step}: {e}")
                        traceback.print_exc()

                # Collect average speed for edges
                try:
                    edge_ids = traci.edge.getIDList()
                    for edge_id in edge_ids:
                        step_speed_data["data"].append({
                            "edge_id": edge_id,
                            "avg_speed": get_average_speed(edge_id),
                        })
                except Exception as e:
                    print(f"Error collecting average speed at step {step}: {e}")
                    traceback.print_exc()

                # Append step data to traffic data dictionaries
                rt_traffic_data["queue_length"].append(step_queue_data)
                rt_traffic_data["avg_speed"].append(step_speed_data)

                # Debug: Print to confirm data is appended
                print(f"Appended to rt_traffic_data['queue_length']: {step_queue_data}")
                print(f"Appended to rt_traffic_data['avg_speed']: {step_speed_data}")

            except Exception as e:
                print(f"Error during simulation step {step}: {e}")
                traceback.print_exc()

        # Debug: Final rt_traffic_data
        print(f"Final RT Traffic Data: {rt_traffic_data}")

        traci.close()
        return rt_traffic_data

    except Exception as e:
        print(f"Critical error in run_adaptive_agent: {e}")
        traceback.print_exc()
        traci.close()
        return None

#Writes the traffic data to csv files
def write_data_to_csv(rt_traffic_data):
    try:
        # Prepare queue length data for CSV
        queue_data = []
        for entry in rt_traffic_data["queue_length"]:
            for data_point in entry["data"]:  # Correctly iterate over the list
                queue_data.append({
                    "Step": entry["step"],  # Add the step value for context
                    "TLS ID": data_point["tls_id"],
                    "Road ID": data_point["road_id"],
                    "Queue Length": data_point["queue_length"]
                })

        # Debug: Print queue data before writing
        print(f"Queue Data for CSV: {queue_data}")

        # Prepare average speed data for CSV
        speed_data = []
        for entry in rt_traffic_data["avg_speed"]:
            for data_point in entry["data"]:  # Correctly iterate over the list
                speed_data.append({
                    "Step": entry["step"],  # Add the step value for context
                    "Edge ID": data_point["edge_id"],
                    "Avg Speed (m/s)": data_point["avg_speed"]
                })

        # Debug: Print speed data before writing
        print(f"Speed Data for CSV: {speed_data}")

        # Export to CSV
        if queue_data:
            pd.DataFrame(queue_data).to_csv("road_queue_lengths.csv", index=False)
            print("road_queue_lengths.csv successfully written.")
        else:
            print("Queue data is empty. No CSV file was written.")

        if speed_data:
            pd.DataFrame(speed_data).to_csv("edge_avg_speeds.csv", index=False)
            print("edge_avg_speeds.csv successfully written.")
        else:
            print("Speed data is empty. No CSV file was written.")

    except Exception as e:
        print(f"Critical error in write_data_to_csv: {e}")



if __name__ == "__main__":
    try:
        run_adaptive_agent()
        write_data_to_csv(rt_traffic_data)
    except Exception as e:
        print(f"Error: {e}")
        if traci.isLoaded():
            traci.close()

# import traci
# import os
# import json
# from traci._trafficlight import Logic, Phase

# # Configuration
# sumoBinary = "sumo-gui"
# sumoConfig = "CustomNetworks/oneLaneMap.sumocfg"
# adaptive_phases_file = "adaptive_fixed_phases.json"
# traffic_light_data_file = "traffic_light_data2c.json"  # For controlled lanes and roads

# # Constants
# EXTRA_GREEN_TIME = 10
# QUEUE_THRESHOLD = 3
# STEP_INTERVAL = 3
# RESET_INTERVAL = 2  # Reset to fixed timing every 2 iterations

# def get_road_queue(road_id, lanes):
#     """Get total queue for a road by summing up its lanes."""
#     return sum(traci.lane.getLastStepHaltingNumber(lane) for lane in lanes)

# def get_dynamic_phases(tls_id, fixed_phases, road_queues, total_queue):
#     """Adjust phase durations dynamically based on queue lengths."""
#     dynamic_phases = []

#     for phase in fixed_phases:
#         state = phase["state"]
#         duration = phase["duration"]

#         if "G" in state:  # Adjust green phases dynamically
#             green_roads = [
#                 road_id
#                 for road_id, lanes in road_queues.items()
#                 if any(state[i] == "G" for i, lane in enumerate(lanes))
#             ]
#             green_queue = sum(road_queues[road_id] for road_id in green_roads)

#             if total_queue > 0:
#                 adjusted_duration = max(
#                     10, min(50, (green_queue / total_queue) * 50)
#                 )
#                 dynamic_phases.append(Phase(int(adjusted_duration), state))
#             else:
#                 dynamic_phases.append(Phase(duration, state))
#         else:
#             # Keep yellow and red phases fixed
#             dynamic_phases.append(Phase(duration, state))

#     return dynamic_phases

# def run_adaptive_agent():
#     traci.start([sumoBinary, "-c", sumoConfig])

#     # Load fixed phases and traffic light metadata
#     with open(adaptive_phases_file, "r") as f:
#         fixed_phases = json.load(f)
#     with open(traffic_light_data_file, "r") as f:
#         traffic_light_data = json.load(f)

#     tls_ids = traci.trafficlight.getIDList()
#     iteration_counter = {tls_id: 0 for tls_id in tls_ids}

#     step = 0
#     while step < 1000:
#         traci.simulationStep()
#         step += 1

#         if step % STEP_INTERVAL == 0:
#             for tls_id in tls_ids:
#                 # Get traffic light metadata
#                 tl_metadata = traffic_light_data[tls_id]
#                 roads = tl_metadata["roads"]

#                 # Update road queues
#                 road_queues = {
#                     road_id: get_road_queue(road_id, lanes)
#                     for road_id, lanes in roads.items()
#                 }
#                 total_queue = sum(road_queues.values())

#                 # Check if reset is due
#                 iteration_counter[tls_id] += 1
#                 if iteration_counter[tls_id] >= RESET_INTERVAL:
#                     # Reset to fixed timing
#                     phases = [
#                         Phase(phase["duration"], phase["state"])
#                         for phase in fixed_phases[tls_id]
#                     ]
#                     logic = Logic("fixed_program", 0, 0, phases)
#                     traci.trafficlight.setProgramLogic(tls_id, logic)
#                     iteration_counter[tls_id] = 0
#                 else:
#                     # Apply adaptive timing
#                     dynamic_phases = get_dynamic_phases(
#                         tls_id, fixed_phases[tls_id], road_queues, total_queue
#                     )
#                     logic = Logic("adaptive_program", 0, 0, dynamic_phases)
#                     traci.trafficlight.setProgramLogic(tls_id, logic)

#     traci.close()

# if __name__ == "__main__":
#     try:
#         run_adaptive_agent()
#     except Exception as e:
#         print(f"Error: {e}")
#         if traci.isLoaded():
#             traci.close()

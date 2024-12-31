import traci
import os
import json
import sumolib
import pandas as pd
from traci._trafficlight import Logic, Phase
import copy
from incident_handling import block_edge, detect_incidents, is_edge_blocked, random_block_edge  # Import the function
from Python_files.performance_testing_AD import gather_performance_data, initialize_metrics
from Python_files.random_scenarios import apply_random_scenarios


# Configuration
import os
import random

# Ensure file paths are absolute and robust
script_dir = os.path.dirname(os.path.abspath(__file__))
sumoBinary = "sumo-gui"
sumoConfig = os.path.join(script_dir, "CustomNetworks", "twoLaneMap.sumocfg")
adaptive_phases_file = os.path.join(script_dir, "adaptive_fixed_phases.json")

# Ensure adaptive phases file exists
if not os.path.exists(adaptive_phases_file):
    raise FileNotFoundError(f"Adaptive phases file not found: {adaptive_phases_file}")

# Adaptive control parameters
MIN_RED = 5
MIN_GREEN = 5
MAX_GREEN = 45
MAX_GREEN_ADDED = 30
MIN_GREEN_ADDED = 5
QUEUE_THRESHOLD = 5
STEP_INTERVAL = 3
# EXTRA_GREEN_TIME = 10
# LESS_RED_TIME = 0.7
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
        # print(f"Step {step} - Traffic light {tls_id} controls lanes: {tl_lanes}")

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
            # print(
            #     f"  Lane {lane} (road {road_id}): {halting_vehicles} vehicles halting."
            # )

        # Debug: Print aggregated queue lengths by road
        # print(f"Aggregated queue lengths at {tls_id}: {queue_lengths}\n")

    except traci.TraCIException as e:
        print(f"Error retrieving controlled lanes for TLS {tls_id} at step {step}: {e}")
    except Exception as e:
        print(
            f"Unexpected error in get_road_queues for TLS {tls_id} at step {step}: {e}"
        )

    return queue_lengths


def get_tls_avg_speed(tls_id):
    # Calculate the average speed for all roads controlled by the given traffic light system (TLS).
   
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    controlled_edges = {lane.split("_")[0] for lane in controlled_lanes}  # Get unique edges
    
    total_speed = 0
    total_vehicles = 0

    for edge_id in controlled_edges:
        try:
            # Retrieve vehicle count and mean speed on the edge
            vehicle_count = traci.edge.getLastStepVehicleNumber(edge_id)
            avg_speed = traci.edge.getLastStepMeanSpeed(edge_id)

            total_speed += avg_speed * vehicle_count  # Weighted sum of speeds
            total_vehicles += vehicle_count
        except traci.TraCIException as e:
            print(f"Error retrieving speed data for edge {edge_id}: {e}")
            continue

    # Calculate average speed for this TLS
    if total_vehicles > 0:
        return total_speed / total_vehicles
    else:
        return 0.0  # No vehicles on controlled edges

def should_optimize(tls_id, queue_lengths, total_vehicles, TLS_avg_speed, step):
    #Heuristic function to determine if there should be optimization
    
    # Parameters for biasing towards optimization
    MIN_VEHICLES_THRESHOLD = 50  # Minimum vehicles in the simulation to consider optimization
    TLS_QUEUE_THRESHOLD = 5  # High total queue threshold to trigger optimization
    MIN_AVG_SPEED = 15.0  # Minimum average speed in m/s to justify optimization

    total_queue = sum(queue_lengths.values())
    avg_queue_per_road = total_queue / len(queue_lengths) if queue_lengths else 0

    # print(f"Step {step}: Heuristic evaluation for TLS {tls_id}")
    # print(f"  Total vehicles: {total_vehicles} in network ")
    # print(f"  Total queue: {total_queue} for tls {tls_id} at sim step {step} ")
    # print(f"  Avg queue per road: {avg_queue_per_road}")
    # print(f"  Avg speed around TL{tls_id}: {TLS_avg_speed:.2f} m/s")

    # Biased towards allowing optimization
    if total_vehicles >= MIN_VEHICLES_THRESHOLD and (total_queue > TLS_QUEUE_THRESHOLD or TLS_avg_speed < MIN_AVG_SPEED):
        # print(f"  Decision: OPTIMIZE (TLS {tls_id})\n")
        return True
    else:
        # print(f"  Decision: DO NOT OPTIMIZE (TLS {tls_id})\n")
        return False

def calculate_dynamic_durations(queue_length, total_queue):
    # Calculate dynamic durations for green and red lights based on queue length.
    # Normalize queue length
    queue_factor = queue_length / max(total_queue, 1)

    # Scale extra green time based on queue factor
    extra_green_time = int(
        queue_factor * (MAX_GREEN_ADDED - MIN_GREEN_ADDED)
    )

    # Scale less red time based on queue factor
    less_red_time = max(0.7, 1 - queue_factor * 0.5)  # Between 70% and 100%

    return extra_green_time, less_red_time



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
        
        # Track which phases have been adjusted
        adjusted_phases = {tls_id: None for tls_id in tls_ids}

        step = 0
        while step < 1000: #change to "while traci.simulation.getMinExpectedNumber() > 0:  # Until simulation ends"
            try:
                
                traci.simulationStep()
                step += 1
                # apply_random_scenarios(step)
                # gather_performance_data()

                # Data collection for each simulation step
                step_queue_data = {"step": step, "data": []}
                step_speed_data = {"step": step, "data": []}

                total_vehicles = traci.vehicle.getIDCount() 
                
                # Collect queue lengths
                for tls_id in tls_ids:
                    if tls_id not in fixed_phases:
                        print(f"TLS {tls_id} not found in adaptivePhasesdata.json file.")
                        continue

                    try:
                        queue_lengths = get_road_queues(tls_id, step)
                        
                        total_queue = sum(queue_lengths.values())
                        # print (f"Total Queue for traffic light {tls_id} = {total_queue}")
                        
                        for road_id, queue_length in queue_lengths.items():
                            step_queue_data["data"].append({
                                "tls_id": tls_id,
                                "road_id": road_id,
                                "queue_length": queue_length,
                            })
                    except Exception as e:
                        print(f"Error collecting queue lengths for TLS {tls_id} at step {step}: {e}")
                        traceback.print_exc()

                    # Calculate average speed for this TLS
                    avg_speed_tls = get_tls_avg_speed(tls_id)
                        
                    
                    # Determine whether to optimize
                    if not should_optimize(tls_id, queue_lengths, total_vehicles, avg_speed_tls, step):
                    # if False:
                        continue
                    
                    # if total_queue > QUEUE_THRESHOLD:
                    current_phase_index = traci.trafficlight.getPhase(tls_id)
                    current_phase_state = fixed_phases[tls_id][current_phase_index]["state"]
                    
                    # Detect phase change and reset adjusted phase
                    if adjusted_phases[tls_id] != current_phase_index:
                        # Reset adjustment tracker if phase has changed
                        adjusted_phases[tls_id] = None
                        
                    # Skip if this phase was already adjusted    
                    if adjusted_phases[tls_id] == current_phase_index:
                        continue

                    # Identify green roads in the current phase
                    green_roads = [
                        road_id
                        for road_id, lanes in queue_lengths.items()
                        if any(
                            current_phase_state[i] == "G"
                            for i, lane in enumerate(traci.trafficlight.getControlledLanes(tls_id))
                            if lane.split("_")[0] == road_id
                        )
                    ]

                    # If the current green roads have the highest queue, extend the phase duration
                    highest_queue_road = max(queue_lengths, key=queue_lengths.get)
                    # print(f"Road with highest queue length: {highest_queue_road}\n")
                    
                    if highest_queue_road not in green_roads:  
                        #detract red time for the current phase 
                        extra_green_time, less_red_time = calculate_dynamic_durations(
                            queue_lengths[highest_queue_road],
                            total_queue
                        )
                        new_duration = max(
                            MIN_GREEN,
                            fixed_phases[tls_id][current_phase_index]["duration"] * less_red_time
                        )
                        detractedTime = fixed_phases[tls_id][current_phase_index]["duration"] - new_duration
                        if detractedTime > 0:
                            print(f"Detracting red phase for TLS {tls_id} by {detractedTime} seconds due to the highest queue road {highest_queue_road} at sim step {step}\n")
                            traci.trafficlight.setPhaseDuration(tls_id, new_duration)
                            adjusted_phases[tls_id] = current_phase_index

                    else:      
                        # Extend the green light for the current phase
                        extra_green_time, _ = calculate_dynamic_durations(
                            queue_lengths[highest_queue_road],
                            total_queue
                        )
                        new_duration = min(
                            MAX_GREEN,
                            fixed_phases[tls_id][current_phase_index]["duration"] + extra_green_time
                        )
                        if(extra_green_time > 3):
                            print(f"Extending green phase for TLS {tls_id} by {extra_green_time} seconds. for the highest queue road {highest_queue_road} at sim step {step}\n")
                            traci.trafficlight.setPhaseDuration(tls_id, new_duration)
                            adjusted_phases[tls_id] = current_phase_index

                 
                                
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
                # print(f"Appended to rt_traffic_data['queue_length']: {step_queue_data}")
                # print(f"Appended to rt_traffic_data['avg_speed']: {step_speed_data}")
                
                # ! Test: block an edge after removing all trips that start and end there
                test_edge_id = "59"
                random_block_edge(test_edge_id)
                    
                # Check if there are any incidents
                if(step % 2 == 10):
                    detect_incidents()
                


            except Exception as e:
                print(f"Error during simulation step {step}: {e}")
                traceback.print_exc()

        # Debug: Final rt_traffic_data
        # print(f"Final RT Traffic Data: {rt_traffic_data}")

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
        # print(f"Queue Data for CSV: {queue_data}")

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
        # print(f"Speed Data for CSV: {speed_data}")

        # Export to CSV
        if queue_data:
            pd.DataFrame(queue_data).to_csv("road_queue_lengths.csv", index=False)
            # print("road_queue_lengths.csv successfully written.")
        else:
            print("Queue data is empty. No CSV file was written.")

        if speed_data:
            pd.DataFrame(speed_data).to_csv("edge_avg_speeds.csv", index=False)
            # print("edge_avg_speeds.csv successfully written.")
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

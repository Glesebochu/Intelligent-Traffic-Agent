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
MIN_GREEN = 3
MAX_GREEN = 45
QUEUE_THRESHOLD = 5
STEP_INTERVAL = 3
EXTRA_GREEN_TIME = 10
LESS_RED_TIME = 0.7
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
        while step < 1000:
            try:
                traci.simulationStep()
                step += 1

                # Data collection for each simulation step
                step_queue_data = {"step": step, "data": []}
                step_speed_data = {"step": step, "data": []}

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
                    
                    
                    
                    if total_queue > QUEUE_THRESHOLD:
                        #get all the roads and their queues for the traffic light
                        #get the green roads
                        #if in the current simulation step, the current traffic light phase is green for the road with less queues, then do nothing
                        #if in the current simulation step, the current traffic light phase is green for the road with the highest queue length, then use setPhaseDuration to make it longer but bounded to a max
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
                            new_duration = max(
                                MIN_GREEN,
                                fixed_phases[tls_id][current_phase_index]["duration"] * LESS_RED_TIME
                            )
                            detractedTime = fixed_phases[tls_id][current_phase_index]["duration"] - new_duration
                            print(f"detracting red phase for TLS {tls_id} by {detractedTime} seconds. for the highest queue road {highest_queue_road} at sim step {step}\n")
                            traci.trafficlight.setPhaseDuration(tls_id, new_duration)
                            adjusted_phases[tls_id] = current_phase_index

                        else:      
                            # Extend the green light for the current phase
                            new_duration = min(
                                MAX_GREEN,
                                fixed_phases[tls_id][current_phase_index]["duration"] + EXTRA_GREEN_TIME
                            )
                            print(f"Extending green phase for TLS {tls_id} by {EXTRA_GREEN_TIME} seconds. for the highest queue road {highest_queue_road} at sim step {step}\n")
                            traci.trafficlight.setPhaseDuration(tls_id, new_duration)
                            adjusted_phases[tls_id] = current_phase_index
                            # continue

                    else:
                        continue
                 
                                
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

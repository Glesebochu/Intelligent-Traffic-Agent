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

def get_road_queues(tls_id, step):
    """Get queue lengths aggregated by road, and print debug information."""
    queue_lengths = {}
    tl_lanes = traci.trafficlight.getControlledLanes(tls_id)
    seen_lanes = set()  # Avoid duplicate lane processing

    #print(f"Step {step} - Traffic light {tls_id} controls lanes: {tl_lanes}")

    for lane in tl_lanes:
        if lane in seen_lanes:
            continue  # Skip duplicate lanes
        seen_lanes.add(lane)

        road_id = lane.split("_")[0]  # Extract road ID
        halting_vehicles = traci.lane.getLastStepHaltingNumber(lane)

        # Aggregate by road ID
        if road_id not in queue_lengths:
            queue_lengths[road_id] = 0
        queue_lengths[road_id] += halting_vehicles

        # Debug: Print lane-specific queue information
        #print(f"  Lane {lane} (road {road_id}): {halting_vehicles} vehicles halting.")

    # Debug: Print aggregated queue lengths by road
    print(f"Aggregated queue lengths at {tls_id}: {queue_lengths}\n")

    return queue_lengths


def get_green_roads(state, tls_id):
    """Identify which roads have green signal in current state."""
    green_roads = set()
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    
    for i, signal in enumerate(state):
        if signal in ['G', 'g']:
            road_id = controlled_lanes[i].split("_")[0]
            green_roads.add(road_id) #no effect if the road is already present.
    
    return green_roads #ids

def calculate_adaptive_duration(base_duration, green_roads, queue_lengths):
    """Calculate adaptive duration based on queue ratios."""
    total_queue = sum(queue_lengths.values())
    if total_queue == 0:
        return base_duration
    
    # Ensure all roads in green_roads exist in queue_lengths
    green_queue = sum(queue_lengths[road] for road in green_roads if road in queue_lengths)

    if green_queue == 0:
        return MIN_GREEN
    
    queue_ratio = green_queue / total_queue
    adapted_duration = base_duration * (1 + queue_ratio)
    
    return max(MIN_GREEN, min(MAX_GREEN, int(adapted_duration)))

def run_adaptive_agent():
    """Main function to run the adaptive traffic control agent."""
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
    while step < 1000:
        traci.simulationStep()
        step += 1
        
        # if step % STEP_INTERVAL == 0:
        for tls_id in tls_ids:
            if tls_id not in fixed_phases:
                continue  # Skip TLS IDs without fixed phases
            
            queue_lengths = get_road_queues(tls_id, step)
            total_queue = sum(queue_lengths.values())
            #print (f"Total Queue for traffic light {tls_id} = {total_queue}")
            
            if total_queue > QUEUE_THRESHOLD:
                # Create adaptive phases
                adaptive_phases = []
                for phase in fixed_phases[tls_id]:
                    state = phase["state"]
                    base_duration = phase["duration"]
                    
                    if 'y' in state:  # Yellow phase - keep original duration
                        adaptive_phases.append(Phase(base_duration, state))
                    else:
                        green_roads = get_green_roads(state, tls_id)
                        print(f"Green roads: {green_roads} at {tls_id} using base state {state}")
                        new_duration = calculate_adaptive_duration(
                            base_duration, green_roads, queue_lengths)
                        adaptive_phases.append(Phase(new_duration, state))
                
                # Apply adaptive timing
                logic = Logic("adaptive_program", 0, 0, adaptive_phases)
                traci.trafficlight.setProgramLogic(tls_id, logic)
            else:
                # Apply fixed timing from JSON
                fixed_phases_data = [
                    Phase(int(phase["duration"]), phase["state"])
                    for phase in fixed_phases[tls_id]
                ]
                logic = Logic("fixed_program", 0, 0, fixed_phases_data)
                traci.trafficlight.setProgramLogic(tls_id, logic)

    traci.close()

if __name__ == "__main__":
    try:
        run_adaptive_agent()
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

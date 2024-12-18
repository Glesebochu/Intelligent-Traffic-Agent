import traci
import os
import json
from traci._trafficlight import Logic, Phase

# Configuration
sumoBinary = "sumo-gui"
sumoConfig = "basemap/basemap.sumocfg"
traffic_light_data_file = "traffic_light_data2c.json"

# Adaptive control parameters
MIN_GREEN = 10
MAX_GREEN = 50
YELLOW_DURATION = 6  # Keeping your baseline yellow duration
QUEUE_THRESHOLD = 3

# Base phase patterns (same as your baseline)
fixed_phases_dict = {
    1: [("G", 20), ("y", 6), ("r", 20), ("r", 6)],
    2: [("Gr", 20), ("yr", 6), ("rG", 20), ("ry", 6)],
    3: [("Grr", 20), ("yrr", 6), ("rGr", 20), ("ryr", 6)],
    4: [("Grrr", 20), ("yrrr", 6), ("rGGG", 20), ("rrrr", 6)],
    5: [("Grrrr", 20), ("yrrrr", 6), ("rGGGG", 20), ("rrrrr", 6)],
    6: [("GGGrrr", 20), ("yyyrrr", 6), ("rrrGGG", 20), ("rrryyy", 6)],
    7: [("GGGrrrr", 20), ("yyyrrrr", 6), ("rrrGGGG", 20), ("rrryyyy", 6)]
}

def calculate_adaptive_duration(state, traffic_light_info):
    """Calculate adaptive duration for a green phase."""
    total_queue = sum(traffic_light_info["road_queues"].values())
    
    if total_queue < QUEUE_THRESHOLD:
        return 20  # Return default duration if queue is small
    
    # Calculate queue for lanes that have green in this phase
    controlled_lanes = traffic_light_info["controlled_lanes"]
    phase_queue = sum(
        traffic_light_info["lane_queues"][controlled_lanes[i]]
        for i, light in enumerate(state)
        if light == 'G'
    )
    
    if total_queue > 0 and phase_queue > 0:
        duration = max(
            MIN_GREEN,
            min(MAX_GREEN, (phase_queue / total_queue) * MAX_GREEN)
        )
    else:
        duration = MIN_GREEN
        
    return duration

def get_adaptive_phases(num_lanes, traffic_light_info):
    """Get adaptive phases based on number of lanes."""
    if num_lanes not in fixed_phases_dict:
        return None
    
    base_patterns = fixed_phases_dict[num_lanes]
    adaptive_phases = []
    
    for state, default_duration in base_patterns:
        if 'G' in state:  # If it's a green phase
            duration = calculate_adaptive_duration(state, traffic_light_info)
        else:  # Keep yellow and red phase durations fixed
            duration = default_duration
            
        adaptive_phases.append(Phase(duration, state))
    
    return adaptive_phases

def set_adaptive_timing(tls_id, traffic_light_info):
    """Set adaptive traffic light timing."""
    num_lanes = len(traffic_light_info["controlled_lanes"])
    phases = get_adaptive_phases(num_lanes, traffic_light_info)
    
    if phases:
        logic = Logic("adaptive_program", 0, 0, phases)
        traci.trafficlight.setProgramLogic(tls_id, logic)

def run_adaptive_agent():
    """Main function to run the adaptive traffic control agent."""
    traci.start([sumoBinary, "-c", sumoConfig])
    
    # Load traffic light data
    traffic_light_data = load_traffic_light_data(traffic_light_data_file)
    
    # Get all traffic lights
    tls_ids = traci.trafficlight.getIDList()
    
    simulation_end_time = 1000
    while traci.simulation.getTime() < simulation_end_time:
        traci.simulationStep()
        
        for tls_id in tls_ids:
            # Update queue lengths
            traffic_light_info = traffic_light_data[tls_id]
            
            # Update lane queues
            for lane in traffic_light_info["controlled_lanes"]:
                traffic_light_info["lane_queues"][lane] = \
                    traci.lane.getLastStepHaltingNumber(lane)
            
            # Update road queues
            for road_id, lanes in traffic_light_info["roads"].items():
                traffic_light_info["road_queues"][road_id] = \
                    sum(traffic_light_info["lane_queues"][lane] for lane in lanes)
            
            # Set adaptive timing
            set_adaptive_timing(tls_id, traffic_light_info)
    
    traci.close()

def load_traffic_light_data(file_path):
    """Load traffic light data from JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    try:
        run_adaptive_agent()
    except Exception as e:
        print(f"Error: {e}")
        if traci.isLoaded():
            traci.close()
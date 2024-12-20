import traci
import os
import json
from traci._trafficlight import Logic, Phase

# Configuration
sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"
adaptive_phases_file = "adaptive_fixed_phases.json"

# Adaptive control parameters
MIN_GREEN = 10
MAX_GREEN = 50
QUEUE_THRESHOLD = 3  # Below this, revert to fixed-time schedule
STEP_INTERVAL = 3  # Frequency of adapting phases (in simulation steps)

def get_dynamic_phases(tls_id, fixed_phases, queue_lengths):
    """Adjust phase durations dynamically based on queue lengths."""
    dynamic_phases = []
    total_queue = sum(queue_lengths.values())

    # Access phases directly from the fixed_phases dictionary
    for phase in fixed_phases[tls_id]:  # List of phases for this TLS ID
        phase_state = phase["state"]
        phase_duration = phase["duration"]

        if "G" in phase_state:  # Adjust green phases dynamically
            # Calculate the total queue for the lanes with green signals
            green_queue = sum(
                queue_lengths.get(road_id, 0)
                for road_id in queue_lengths.keys()
                if any(phase_state[i] == "G" for i, road_id in enumerate(queue_lengths.keys()))
            )
            # Adjust green duration proportionally
            if total_queue > 0 and green_queue > 0:
                adjusted_duration = max(
                    MIN_GREEN,
                    min(MAX_GREEN, (green_queue / total_queue) * MAX_GREEN),
                )
                dynamic_phases.append(Phase(int(adjusted_duration), phase_state))
            else:
                dynamic_phases.append(Phase(phase_duration, phase_state))
        else:  # Keep yellow/red phases fixed
            dynamic_phases.append(Phase(phase_duration, phase_state))
    
    return dynamic_phases

def set_adaptive_timing(tls_id, fixed_phases, queue_lengths):
    """Set adaptive traffic light timing."""
    dynamic_phases = get_dynamic_phases(tls_id, fixed_phases, queue_lengths)
    logic = Logic("adaptive_program", 0, 0, dynamic_phases)
    traci.trafficlight.setProgramLogic(tls_id, logic)

def run_adaptive_agent():
    """Main function to run the adaptive traffic control agent."""
    traci.start([sumoBinary, "-c", sumoConfig])

    # Load fixed phase data
    fixed_phases = load_adaptive_phases(adaptive_phases_file)

    # Get all traffic lights
    tls_ids = traci.trafficlight.getIDList()

    simulation_end_time = 1000
    step = 0
    while traci.simulation.getTime() < simulation_end_time:
        traci.simulationStep()
        step += 1

        # Every STEP_INTERVAL steps, adapt the timing
        if step % STEP_INTERVAL == 0:
            for tls_id in tls_ids:
                # Dynamically update queue lengths
                queue_lengths = {}
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
                for lane in controlled_lanes:
                    road_id = lane.split("_")[0]  # Extract road ID from lane
                    queue_lengths[road_id] = queue_lengths.get(road_id, 0) + traci.lane.getLastStepHaltingNumber(lane)

                # Check if total queue exceeds threshold
                total_queue = sum(queue_lengths.values())
                if total_queue > QUEUE_THRESHOLD:
                    # Adjust timing adaptively
                    set_adaptive_timing(tls_id, fixed_phases, queue_lengths)
                else:
                    # Revert to fixed-time schedule
                    fixed_phases_data = [
                        Phase(phase["duration"], phase["state"])
                        for phase in fixed_phases[tls_id]
                    ]
                    logic = Logic("fixed_program", 0, 0, fixed_phases_data)
                    traci.trafficlight.setProgramLogic(tls_id, logic)

    traci.close()

def load_adaptive_phases(file_path):
    """Load traffic light phases directly from JSON."""
    with open(file_path, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    try:
        run_adaptive_agent()
    except Exception as e:
        print(f"Error: {e}")
        if traci.isLoaded():
            traci.close()

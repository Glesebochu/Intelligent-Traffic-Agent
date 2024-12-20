import json
from traci._trafficlight import Phase

# Input and output files
input_file = "traffic_light_data2c.json"
output_file = "adaptive_fixed_phases.json"

# Constants for default phase durations
DEFAULT_GREEN = 20
DEFAULT_YELLOW = 6

def generate_fixed_phases(data):
    """Generate fixed phases for traffic lights based on lane groupings."""
    fixed_phases = {}

    for tls_id, tls_info in data.items():
        controlled_lanes = tls_info["controlled_lanes"]
        roads = tls_info["roads"]

        # Initialize phase states for the traffic light
        num_lanes = len(controlled_lanes)
        lane_to_road = {}
        for road_id, road_lanes in roads.items():
            for lane in road_lanes:
                lane_to_road[lane] = road_id

        # Generate phases
        green_phases = []
        for road_id, road_lanes in roads.items():
            green_state = "".join(
                "G" if lane in road_lanes else "r" for lane in controlled_lanes
            )
            yellow_state = "".join(
                "y" if lane in road_lanes else "r" for lane in controlled_lanes
            )
            green_phases.append((green_state, yellow_state))

        # Build the fixed phases for the traffic light
        phases = []
        for green_state, yellow_state in green_phases:
            phases.append(Phase(DEFAULT_GREEN, green_state))
            phases.append(Phase(DEFAULT_YELLOW, yellow_state))

        # Add an all-red phase at the end of the cycle
        all_red_state = "r" * num_lanes
        phases.append(Phase(DEFAULT_YELLOW, all_red_state))

        # Store in the fixed phases dictionary
        fixed_phases[tls_id] = phases

    return fixed_phases

def save_phases_to_json(fixed_phases, file_path):
    """Save the generated fixed phases to a JSON file."""
    # Convert Phase objects to a JSON-serializable format
    serializable_phases = {}
    for tls_id, phases in fixed_phases.items():
        serializable_phases[tls_id] = [
            {"duration": phase.duration, "state": phase.state} for phase in phases
        ]
    
    # Write to file
    with open(file_path, "w") as f:
        json.dump(serializable_phases, f, indent=4)

def main():
    """Main function to generate and save fixed phases."""
    with open(input_file, "r") as f:
        traffic_light_data = json.load(f)
    
    fixed_phases = generate_fixed_phases(traffic_light_data)
    save_phases_to_json(fixed_phases, output_file)
    print(f"Fixed phases saved to {output_file}")

if __name__ == "__main__":
    main()

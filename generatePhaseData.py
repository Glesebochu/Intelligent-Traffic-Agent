# import json
# from traci._trafficlight import Phase

# # Input and output files
# input_file = "traffic_light_data2c.json"
# output_file = "adaptive_fixed_phases.json"

# # Constants for default phase durations
# DEFAULT_GREEN = 20
# DEFAULT_YELLOW = 6

# def generate_fixed_phases(data):
#     """Generate fixed phases for traffic lights based on lane groupings."""
#     fixed_phases = {}

#     for tls_id, tls_info in data.items():
#         controlled_lanes = tls_info["controlled_lanes"]
#         roads = tls_info["roads"]

#         # Initialize phase states for the traffic light
#         num_lanes = len(controlled_lanes)
#         lane_to_road = {}
#         for road_id, road_lanes in roads.items():
#             for lane in road_lanes:
#                 lane_to_road[lane] = road_id

#         # Generate phases
#         green_phases = []
#         for road_id, road_lanes in roads.items():
#             green_state = "".join(
#                 "G" if lane in road_lanes else "r" for lane in controlled_lanes
#             )
#             yellow_state = "".join(
#                 "y" if lane in road_lanes else "r" for lane in controlled_lanes
#             )
#             green_phases.append((green_state, yellow_state))

#         # Build the fixed phases for the traffic light
#         phases = []
#         for green_state, yellow_state in green_phases:
#             phases.append(Phase(DEFAULT_GREEN, green_state))
#             phases.append(Phase(DEFAULT_YELLOW, yellow_state))

#         # Add an all-red phase at the end of the cycle
#         all_red_state = "r" * num_lanes
#         phases.append(Phase(DEFAULT_YELLOW, all_red_state))

#         # Store in the fixed phases dictionary
#         fixed_phases[tls_id] = phases

#     return fixed_phases

# def save_phases_to_json(fixed_phases, file_path):
#     """Save the generated fixed phases to a JSON file."""
#     # Convert Phase objects to a JSON-serializable format
#     serializable_phases = {}
#     for tls_id, phases in fixed_phases.items():
#         serializable_phases[tls_id] = [
#             {"duration": phase.duration, "state": phase.state} for phase in phases
#         ]
    
#     # Write to file
#     with open(file_path, "w") as f:
#         json.dump(serializable_phases, f, indent=4)

# def main():
#     """Main function to generate and save fixed phases."""
#     with open(input_file, "r") as f:
#         traffic_light_data = json.load(f)
    
#     fixed_phases = generate_fixed_phases(traffic_light_data)
#     save_phases_to_json(fixed_phases, output_file)
#     print(f"Fixed phases saved to {output_file}")

# if __name__ == "__main__":
#     main()






import json

def create_adaptive_phases_json():
    # Load the traffic light data
    with open('traffic_light_data2c.json', 'r') as f:
        tl_data = json.load(f)
    
    adaptive_phases = {}
    
    for tl_id, tl_info in tl_data.items():
        # Get the default program phases
        default_phases = tl_info['default_program']['phases']
        
        # Create adjusted phases maintaining the same state patterns
        # but with standardized durations for fairness
        adjusted_phases = []
        
        for phase in default_phases:
            state = phase['state']
            # Set standard durations: 30s for green, 3s for yellow
            if 'y' in state:
                duration = 3
            else:
                duration = 30
                
            adjusted_phases.append({
                "duration": duration,
                "state": state
            })
        
        adaptive_phases[tl_id] = adjusted_phases
    
    # Save to JSON file
    with open('adaptive_fixed_phases.json', 'w') as f:
        json.dump(adaptive_phases, f, indent=2)

if __name__ == "__main__":
    create_adaptive_phases_json()


# import json

# # Input file: traffic light data
# traffic_light_data_file = "traffic_light_data2c.json"

# # Output file: adaptive fixed phases
# adaptive_phases_file = "adaptive_fixed_phases.json"

# def create_adaptive_fixed_phases(input_file, output_file):
#     """Generate adaptive fixed phases JSON file based on traffic light data."""
#     # Load traffic light data
#     with open(input_file, "r") as f:
#         tl_data = json.load(f)
    
#     phases_dict = {}

#     # Process each traffic light
#     for tl_id, data in tl_data.items():
#         roads = list(data["roads"].keys())  # List of road IDs
#         phases = []

#         # Create one green phase and one yellow phase per road
#         for road in roads:
#             # Create the state string for green phase
#             green_state = ""
#             for r in roads:
#                 if r == road:
#                     green_state += "G" * len(data["roads"][r])
#                 else:
#                     green_state += "r" * len(data["roads"][r])
            
#             # Add green phase
#             phases.append({
#                 "duration": 30,  # Base green time
#                 "state": green_state
#             })
            
#             # Create the state string for yellow phase
#             yellow_state = green_state.replace("G", "y")
#             phases.append({
#                 "duration": 3,  # Yellow time
#                 "state": yellow_state
#             })
        
#         # Assign phases to traffic light ID
#         phases_dict[tl_id] = phases
    
#     # Save phases to the output file
#     with open(output_file, "w") as f:
#         json.dump(phases_dict, f, indent=2)
    
#     print(f"Adaptive fixed phases saved to {output_file}")

# if __name__ == "__main__":
#     # Generate the adaptive fixed phases JSON
#     create_adaptive_fixed_phases(traffic_light_data_file, adaptive_phases_file)


# import traci
# import json

# # Configuration
# sumoBinary = "sumo-gui"
# sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"  # Replace with your SUMO configuration file
# output_file = "traffic_light_data.json"

# # Default phase durations
# DEFAULT_GREEN = 20
# DEFAULT_YELLOW = 3
# DEFAULT_RED = 20

# def extract_traffic_light_data():
#     traci.start([sumoBinary, "-c", sumoConfig])
    
#     tls_ids = traci.trafficlight.getIDList()
#     traffic_light_data = {}

#     for tls_id in tls_ids:
#         controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
#         # Group lanes by road
#         road_lane_map = {}
#         for lane in controlled_lanes:
#             road_id = lane.split("_")[0]
#             if road_id not in road_lane_map:
#                 road_lane_map[road_id] = []
#             road_lane_map[road_id].append(lane)

#         # Generate default phases
#         roads = list(road_lane_map.keys())
#         phases = []
#         for road in roads:
#             # Create green phase for current road
#             state = ""
#             for r in roads:
#                 if r == road:
#                     state += "G" * len(road_lane_map[r])
#                 else:
#                     state += "r" * len(road_lane_map[r])
#             phases.append({"state": state, "duration": DEFAULT_GREEN})

#             # Create yellow phase for current road
#             yellow_state = state.replace("G", "y")
#             phases.append({"state": yellow_state, "duration": DEFAULT_YELLOW})

#         # Add an all-red phase to ensure safety
#         all_red_state = "r" * len(controlled_lanes)
#         phases.append({"state": all_red_state, "duration": DEFAULT_RED})

#         # Store data for the current traffic light
#         traffic_light_data[tls_id] = {
#             "controlled_lanes": controlled_lanes,
#             "roads": road_lane_map,
#             "default_phases": phases
#         }

#     traci.close()

#     # Write output to JSON file
#     with open(output_file, "w") as f:
#         json.dump(traffic_light_data, f, indent=2)
#     print(f"Traffic light data written to {output_file}")

# if __name__ == "__main__":
#     try:
#         extract_traffic_light_data()
#     except Exception as e:
#         print(f"Error: {e}")
#         if traci.isLoaded():
#             traci.close()

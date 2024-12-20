import traci
import os
import json

# Configuration
sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/oneLaneMap.sumocfg"
output_file = "traffic_light_data2c.json"

def get_traffic_light_info(tls_id):
    """Gather information about a traffic light."""
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    
    # Group lanes by their connecting road
    roads = {}
    for lane in controlled_lanes:
        road_id = lane.rsplit('_', 1)[0]
        if road_id not in roads:
            roads[road_id] = []
        roads[road_id].append(lane)
    
    # Get the default program logic
    logic = traci.trafficlight.getAllProgramLogics(tls_id)[0]
    default_phases = []
    for phase in logic.phases:
        default_phases.append({
            "duration": phase.duration,
            "state": phase.state
        })
    
    return {
        "controlled_lanes": controlled_lanes,
        "roads": roads,
        "default_program": {
            "phases": default_phases,
            "cycle_time": sum(phase.duration for phase in logic.phases)
        },
        "lane_queues": {lane: 0 for lane in controlled_lanes},
        "road_queues": {road_id: 0 for road_id in roads.keys()}
    }

def generate_traffic_light_data():
    """Generate traffic light data and save to JSON."""
    traci.start([sumoBinary, "-c", sumoConfig])
    
    # Collect data for all traffic lights
    tls_data = {}
    tls_ids = traci.trafficlight.getIDList()
    
    for tls_id in tls_ids:
        tls_data[tls_id] = get_traffic_light_info(tls_id)
    
    # Save to JSON file
    with open(output_file, 'w') as f:
        json.dump(tls_data, f, indent=2)
    
    traci.close()

if __name__ == "__main__":
    try:
        generate_traffic_light_data()
        print(f"Traffic light data saved to {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        if traci.isLoaded():
            traci.close()
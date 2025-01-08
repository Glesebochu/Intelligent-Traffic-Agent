import traci

# Configuration
sumoBinary = "sumo-gui"
sumoConfig = "basemap/basemap.sumocfg"
output_file = "Logs/lane_info.txt"

def extract_lane_info():
    try:
        traci.start([sumoBinary, "-c", sumoConfig])
        
        # Open a file to save the output
        with open(output_file, "w") as file:
            file.write("Lane Information for Traffic Lights\n")
            file.write("=" * 50 + "\n")
            
            # Get all traffic light IDs
            tls_ids = traci.trafficlight.getIDList()
            file.write(f"Detected Traffic Lights: {tls_ids}\n\n")
            
            for tls_id in tls_ids:
                file.write(f"Traffic Light: {tls_id}\n")
                file.write("-" * 50 + "\n")
                
                # Get controlled lanes
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
                file.write(f"Controlled Lanes ({len(controlled_lanes)}):\n")
                
                for lane in controlled_lanes:
                    # Gather additional details for each lane
                    lane_index = controlled_lanes.index(lane)
                    lane_length = traci.lane.getLength(lane)
                    vehicle_count = traci.lane.getLastStepVehicleNumber(lane)
                    
                    file.write(
                        f"  - Lane {lane_index}: ID={lane}, Length={lane_length:.2f}m, Vehicles={vehicle_count}\n"
                    )
                
                file.write("\n")
        
        print(f"Lane information successfully written to {output_file}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        traci.close()

if __name__ == "__main__":
    extract_lane_info()

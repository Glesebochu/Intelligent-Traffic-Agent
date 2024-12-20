import traci  
import os
from traci._trafficlight import Logic, Phase

sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"  # Your configuration file

log_file = "Logs/fixed_tl_log.txt"
metrics_file = "Logs/baseline_metrics.txt"

# Traffic light phase definitions for intersections
fixed_phases_dict = {
    1: [Phase(20, "G"),# North-South green, East-West red for 20 seconds
        Phase(6, "y"),# North-South yellow, East-West red for 6 seconds
        Phase(20, "r"),# East-West green, North-South red for 20 seconds
        Phase(6, "r")# East-West yellow, North-South red for 6 seconds
        ],
    2: [Phase(20, "Gr"),
        Phase(6, "yr"),
        Phase(20, "rG"),
        Phase(6, "ry")
        ],  
    3: [Phase(20, "Grr"),
        Phase(6, "yrr"),
        Phase(20, "rGr"),
        Phase(6, "ryr")
        ],   
    4: [Phase(20, "Grrr"),
        Phase(6, "yrrr"),
        Phase(20, "rGGG"),
        Phase(6, "rrrr")
        ], 
    5: [Phase(20, "Grrrr"),
        Phase(6, "yrrrr"),
        Phase(20, "rGGGG"),
        Phase(6, "rrrrr")
        ],   
    6: [Phase(20, "GGGrrr"),
        Phase(6, "yyyrrr"),
        Phase(20, "rrrGGG"),
        Phase(6, "rrryyy")
        ],
    7: [Phase(20, "GGGrrrr"),
        Phase(6, "yyyrrrr"),
        Phase(20, "rrrGGGG"),
        Phase(6, "rrryyyy")
        ],

}

#for performance metrics
vehicle_travel_times = {} #{id: travel_time}
vehicle_departure_times = {}  # {id: departure_time}
total_waiting_time = 0
queue_lengths = {} # {tls_id: total_queued_vehicles}
   
def set_fixed_timing(tls_id):  
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    num_lanes = len(controlled_lanes)

    print(f"Traffic light {tls_id} controls {num_lanes} lanes.")

    if num_lanes in fixed_phases_dict:
        phases = fixed_phases_dict[num_lanes]
    else:
            print(f"Traffic light {tls_id} has unsupported lane count, {num_lanes}.")
            return
    
    logic = Logic("fixed_program", 0, 0, phases)

    traci.trafficlight.setProgramLogic(tls_id, logic)

def collect_metrics():
    global total_waiting_time

    # Track vehicle departures
    for vehicle_id in traci.simulation.getDepartedIDList():
        vehicle_departure_times[vehicle_id] = traci.simulation.getTime()

    # Collect travel time for vehicles that have arrived
    for vehicle_id in traci.simulation.getArrivedIDList():
        # Check if vehicle is in departure times dict
        if vehicle_id in vehicle_departure_times:
            travel_time = traci.simulation.getTime() - vehicle_departure_times[vehicle_id]
            vehicle_travel_times[vehicle_id] = travel_time
    for vehicle_id in traci.vehicle.getIDList():
        #waiting time for each vehicle
        try:
            waiting_time = traci.vehicle.getWaitingTime(vehicle_id)
            total_waiting_time += waiting_time
        except traci.exceptions.TraCIException as e:
            print(f"Warning: Failed to get waiting time for vehicle {vehicle_id}. {e}")

    #collect queue lengths
    for tls_id in traci.trafficlight.getIDList():
        queue_lengths[tls_id] = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in traci.trafficlight.getControlledLanes(tls_id))    

def calculate_avg_travel_time(): 
    if len(vehicle_travel_times)>0:
        return sum(vehicle_travel_times.values())/len(vehicle_travel_times)
    return 0

def write_metrics_to_file():
    try:
        with open(metrics_file, "w") as file:
            file.write("Baseline Traffic Control Metrics\n")
            file.write("="*40 + "\n")
            average_travel_time = calculate_avg_travel_time()
            file.write(f"-Average Vehicle Travel Time: {average_travel_time:.2f}seconds\n")
            file.write(f"-Total Waiting Time: {total_waiting_time:.2f}seconds\n")
            file.write(f"-Queue Lengths at Traffic Lights:\n")
            for tls_id, queue_length in queue_lengths.items():
                file.write(f" {tls_id}: {queue_length} vehicles\n")

        print(f"Metrics successfully written to {metrics_file}")
    except Exception as e:
        print(f"Error writing metrics: {e}")


def run_baseline():
    # Open a log file to record traffic light operations
    try:     
        with open(log_file, "w") as log_handle:
            traci.start([sumoBinary, "-c", sumoConfig])

            log_handle.write("Traffic Light Phase Log\n")
            log_handle.write("=" * 40 + "\n")

            tls_ids = traci.trafficlight.getIDList()
            log_handle.write(f"Detected Traffic Lights: {tls_ids}\n")

            for tls_id in tls_ids:
                set_fixed_timing(tls_id)
                log_handle.write(f"Dynamic fixed timing set for traffic light: {tls_id}\n")

            simulation_end_time = 700

            # Run the simulation
            while (traci.simulation.getTime() < simulation_end_time and 
            traci.simulation.getMinExpectedNumber() > 0  # While vehicles are in the network
            ):
                traci.simulationStep()  # Advance the simulation
                collect_metrics()

            # End the simulation
            log_handle.write("Simulation ended.\n")
            print(f"Traffic light operations logged to {log_file}")

    finally:
        write_metrics_to_file()
        traci.close()


# Main execution
if __name__ == "__main__":
    try:
        run_baseline()
    except Exception as e:
        print(f"Error: {e}")
        traci.close()

import traci  
import os
from traci._trafficlight import Logic, Phase

# Specify the SUMO binary (use sumo-gui for visual interface)
sumoBinary = "sumo-gui"
sumoConfig = "basemap/basemap.sumocfg"  # Your configuration file

log_file = "fixed_tl_log.txt"

# Traffic light phase definitions for a simple intersection
fixed_phases_dict = {
    1: [Phase(10, "G"),# North-South green, East-West red for 10 seconds
        Phase(3, "y"),# North-South yellow, East-West red for 3 seconds
        Phase(10, "r"),# East-West green, North-South red for 10 seconds
        Phase(3, "r")# East-West yellow, North-South red for 3 seconds
        ],
    2: [Phase(10, "Gr"),
        Phase(3, "yr"),
        Phase(10, "rG"),
        Phase(3, "ry")
        ],  
    3: [Phase(10, "Grr"),
        Phase(3, "yrr"),
        Phase(10, "rGr"),
        Phase(3, "ryr")
        ],   
    4: [Phase(10, "Grrr"),
        Phase(3, "yrrr"),
        Phase(10, "rGGG"),
        Phase(3, "rrrr")
        ],   
    5: [Phase(10, "Grrrr"),
        Phase(3, "yrrrr"),
        Phase(10, "rGGGG"),
        Phase(3, "rrrrr")
        ],   
    6: [Phase(10, "GGGrrr"),
        Phase(3, "yyyrrr"),
        Phase(10, "rrrGGG"),
        Phase(3, "rrryyy")
        ],
    7: [Phase(10, "GGGrrrr"),
        Phase(3, "yyyrrrr"),
        Phase(10, "rrrGGGG"),
        Phase(3, "rrryyyy")
        ],

}

   
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


def run_baseline():
    """
    Runs the baseline agent with fixed traffic light timings.
    """
    # Open a log file to record traffic light operations
    with open(log_file, "w") as log_handle:
        # Connect to SUMO
        traci.start([sumoBinary, "-c", sumoConfig])

        log_handle.write("Traffic Light Phase Log\n")
        log_handle.write("=" * 40 + "\n")

        # Get all traffic light IDs in the network
        tls_ids = traci.trafficlight.getIDList()
        log_handle.write(f"Detected Traffic Lights: {tls_ids}\n")

        for tls_id in tls_ids:
            set_fixed_timing(tls_id)
            log_handle.write(f"Dynamic fixed timing set for traffic light: {tls_id}\n")


        # Run the simulation
        while traci.simulation.getMinExpectedNumber() > 0:  # While vehicles are in the network
            traci.simulationStep()  # Advance the simulation

        # End the simulation
        traci.close()
        log_handle.write("Simulation ended.\n")
    print(f"Traffic light operations logged to {log_file}")


# Main execution
if __name__ == "__main__":
    try:
        run_baseline()
    except Exception as e:
        print(f"Error: {e}")
        traci.close()

import traci
import os
from traci._trafficlight import Logic, Phase
from Python_files.performance_testing_Bl import initialize_metrics, gather_performance_data

# SUMO configuration
sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"
log_file = "Logs/fixed_tl_log.txt"

# Traffic light phase definitions for intersections
fixed_phases_dict = {
    1: [Phase(30, "G"), Phase(4, "y"), Phase(30, "r"), Phase(4, "r")],
    2: [Phase(30, "Gr"), Phase(4, "yr"), Phase(30, "rG"), Phase(4, "ry")],
    3: [Phase(30, "Grr"), Phase(4, "yrr"), Phase(30, "rGr"), Phase(4, "ryr")],
    4: [Phase(35, "Grrr"), Phase(5, "yrrr"), Phase(35, "rGGG"), Phase(5, "rrrr")],
    5: [Phase(35, "Grrrr"), Phase(5, "yrrrr"), Phase(35, "rGGGG"), Phase(5, "rrrrr")],
    6: [
        Phase(40, "GGGrrr"),
        Phase(6, "yyyrrr"),
        Phase(40, "rrrGGG"),
        Phase(6, "rrryyy"),
    ],
    7: [
        Phase(40, "GGGrrrr"),
        Phase(6, "yyyrrrr"),
        Phase(40, "rrrGGGG"),
        Phase(6, "rrryyyy"),
    ],
    8: [
        Phase(45, "GGGGrrrr"),
        Phase(7, "yyyyrrrr"),
        Phase(45, "rrrrGGGG"),
        Phase(7, "rrrryyyy"),
    ],
    9: [
        Phase(45, "GGGGGrrrrr"),
        Phase(7, "yyyyyrrrrr"),
        Phase(45, "rrrrrGGGGG"),
        Phase(7, "rrrrryyyyy"),
    ],
    10: [
        Phase(50, "GGGGGGrrrrrr"),
        Phase(8, "yyyyyyrrrrrr"),
        Phase(50, "rrrrrrGGGGGG"),
        Phase(8, "rrrrrryyyyyy"),
    ],
    11: [
        Phase(50, "GGGGGGGrrrrrrr"),
        Phase(8, "yyyyyyyrrrrrrr"),
        Phase(50, "rrrrrrrGGGGGGG"),
        Phase(8, "rrrrrrryyyyyyy"),
    ],
    12: [
        Phase(50, "GGGGGGGGrrrrrrrr"),
        Phase(8, "yyyyyyyyrrrrrrrr"),
        Phase(50, "rrrrrrrrGGGGGGGG"),
        Phase(8, "rrrrrrrryyyyyyyy"),
    ],
    13: [
        Phase(55, "GGGGGGGGGrrrrrrrrr"),
        Phase(9, "yyyyyyyyyrrrrrrrrr"),
        Phase(55, "rrrrrrrrrGGGGGGGGG"),
        Phase(9, "rrrrrrrrryyyyyyyyy"),
    ],
    14: [
        Phase(55, "GGGGGGGGGGrrrrrrrrrr"),
        Phase(9, "yyyyyyyyyyrrrrrrrrrr"),
        Phase(55, "rrrrrrrrrrGGGGGGGGGG"),
        Phase(9, "rrrrrrrrrryyyyyyyyyy"),
    ],
    15: [
        Phase(60, "GGGGGGGGGGGrrrrrrrrrrr"),
        Phase(10, "yyyyyyyyyyyrrrrrrrrrrr"),
        Phase(60, "rrrrrrrrrrrGGGGGGGGGGG"),
        Phase(10, "rrrrrrrrrrryyyyyyyyyyy"),
    ],
    16: [
        Phase(60, "GGGGGGGGGGGGrrrrrrrrrrrr"),
        Phase(10, "yyyyyyyyyyyyrrrrrrrrrrrr"),
        Phase(60, "rrrrrrrrrrrrGGGGGGGGGGGG"),
        Phase(10, "rrrrrrrrrrrryyyyyyyyyyyy"),
    ],
    17: [
        Phase(60, "GGGGGGGGGGGGGrrrrrrrrrrrrr"),
        Phase(10, "yyyyyyyyyyyyyrrrrrrrrrrrrr"),
        Phase(60, "rrrrrrrrrrrrrGGGGGGGGGGGGG"),
        Phase(10, "rrrrrrrrrrrrryyyyyyyyyyyyy"),
    ],
    18: [
        Phase(65, "GGGGGGGGGGGGGGrrrrrrrrrrrrrr"),
        Phase(11, "yyyyyyyyyyyyyyrrrrrrrrrrrrrr"),
        Phase(65, "rrrrrrrrrrrrrrGGGGGGGGGGGGGG"),
        Phase(11, "rrrrrrrrrrrrrryyyyyyyyyyyyyy"),
    ],
    19: [
        Phase(65, "GGGGGGGGGGGGGGGrrrrrrrrrrrrrrr"),
        Phase(11, "yyyyyyyyyyyyyyyrrrrrrrrrrrrrrr"),
        Phase(65, "rrrrrrrrrrrrrrrGGGGGGGGGGGGGGG"),
        Phase(11, "rrrrrrrrrrrrrrryyyyyyyyyyyyyyy"),
    ],
    20: [
        Phase(70, "GGGGGGGGGGGGGGGGrrrrrrrrrrrrrrrr"),
        Phase(12, "yyyyyyyyyyyyyyyyrrrrrrrrrrrrrrrr"),
        Phase(70, "rrrrrrrrrrrrrrrrGGGGGGGGGGGGGGGG"),
        Phase(12, "rrrrrrrrrrrrrrrryyyyyyyyyyyyyyyy"),
    ],
}


# Sets fixed timing for each traffic light
def set_fixed_timing(tls_id):
    """
    Configures fixed timing for traffic lights based on the number of lanes they control.

    Args:
        tls_id (str): Traffic light system ID.
    """
    # Get controlled lanes by the traffic light
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
    num_lanes = len(controlled_lanes)

    # Apply predefined phases based on lane count
    if num_lanes in fixed_phases_dict:
        # Retrieve phases from the dictionary
        phases = fixed_phases_dict[num_lanes]
        logic = Logic("fixed_program", 0, 0, phases)  # Define fixed logic
        traci.trafficlight.setProgramLogic(tls_id, logic)  # Apply logic
    else:
        # Log unsupported lane count if the configuration is missing
        print(f"Unsupported lane count {num_lanes} at traffic light {tls_id}")


# Runs the baseline agent simulation
def run_baseline():
    """
    Manages the simulation by initializing metrics, setting traffic light phases, and gathering data.
    """
    # Open a log file to record traffic light operations
    try:
        with open(log_file, "w") as log_handle:
            # Start SUMO simulation
            traci.start([sumoBinary, "-c", sumoConfig])

            # Initialize metrics and traffic light settings
            initialize_metrics()
            log_handle.write("Traffic Light Phase Log\n")
            log_handle.write("=" * 40 + "\n")

            # Detect and configure all traffic lights in the simulation
            tls_ids = traci.trafficlight.getIDList()
            log_handle.write(f"Detected Traffic Lights: {tls_ids}\n")

            for tls_id in tls_ids:
                # Set fixed timing for each traffic light
                set_fixed_timing(tls_id)
                log_handle.write(
                    f"Dynamic fixed timing set for traffic light: {tls_id}\n"
                )

            # Run simulation loop until no more vehicles are expected
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()  # Advance the simulation
                # Run performance tests
                gather_performance_data()
            print("Simulation completed successfully.")
            traci.close()

    # Handle exceptions and close SUMO connection gracefully
    except Exception as e:
        print(f"Error: {e}")
        traci.close()


# Main entry point for executing the baseline agent
if __name__ == "__main__":
    try:
        run_baseline()
    # Handle any errors during execution
    except Exception as e:
        print(f"Error: {e}")
        traci.close()

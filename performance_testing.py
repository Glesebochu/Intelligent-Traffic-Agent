import traci
import pandas as pd

# Configuration
sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"

# def get_average_waiting_time():
#     try:
#         trips = traci.simulation.getArrivedIDList()  # Get the list of completed trips
#         if len(trips) == 0:
#             print("No trips completed in the simulation.")
#             return 0
#         total_waiting_time = sum(traci.trip.getWaitingTime(trip) for trip in trips)  # Using trip-related method
#         return total_waiting_time / max(len(trips), 1)
#     except Exception as e:
#         print(f"Error calculating average waiting time: {e}")
#         return 0
def get_average_waiting_time():
    # try:
        # Get the list of completed trips
        trips = traci.simulation.getArrivedIDList()
        print(f"Completed trips: {trips}")  # Debugging log
        print(f"{len(trips)}")
        
        if len(trips) == 0:
            print("No trips completed in the simulation.")
            return 0
        
        total_waiting_time = 0
        total_vehicles = 0  # Count vehicles contributing to total waiting time
        index = 0
        # Iterate through all vehicles currently in the simulation
        vehicles_in_trip = traci.vehicle.getIDList()
        print(f"Vehicles in trip: {len(vehicles_in_trip)}")  # Debugging log
        while index < len(vehicles_in_trip):
            veh = vehicles_in_trip[index]
            # Check if the vehicle has completed its trip
            waiting_time = traci.vehicle.getWaitingTime(veh)
            total_waiting_time += waiting_time
            total_vehicles += 1  # Count this vehicle for average calculation
            print(f"Vehicle {veh} waiting time: {waiting_time}")  # Debugging log

            index += 1  # Increment index to check the next vehicle
        
        print(f"total veh: {total_vehicles}")

        # Check if any vehicles were processed, to avoid division by zero
        if total_vehicles == 0:
            print("No completed vehicles for waiting time calculation.")
            return 0
       

        # Calculate and return the average waiting time
        return total_waiting_time / max(total_vehicles, 1)  # Avoid division by zero
    # except Exception as e:
    #     print(f"Error calculating average waiting time: {e}")
    #     return 0



def get_average_travel_time():
    try:
        trips = traci.simulation.getArrivedIDList()  # Using completed trips
        if len(trips) == 0:
            print("No trips completed in the simulation.")
            return 0
        total_time = 0
        for trip in trips:
            travel_time = traci.trip.getJourneyTime(trip)  # Using trip-related method
            print(f"Trip {trip} Journey Time: {travel_time}")  # Debugging log
            total_time += travel_time
        avg_travel_time = total_time / max(len(trips), 1)
        print(f"Average Travel Time: {avg_travel_time}")  # Debugging log
        return avg_travel_time
    except Exception as e:
        print(f"Error calculating average travel time: {e}")
        return 0


def get_average_queue_length():
    try:
        total_queue_length = 0
        # Sum of vehicle counts across all edges
        edge_ids = traci.edge.getIDList()
        for edge in edge_ids:
            total_queue_length += traci.edge.getLastStepVehicleNumber(edge)
        return total_queue_length
    except Exception as e:
        print(f"Error calculating average queue length: {e}")
        return 0


def get_throughput():
    try:
        trips = traci.simulation.getArrivedIDList()  # Using completed trips
        print(f"Completed trips: {trips}")  # Debugging log
        return len(trips)
    except Exception as e:
        print(f"Error calculating throughput: {e}")
        return 0


def gather_performance_data(sim_runs):
    # try:
        results = []

        # Ensure SUMO simulation is already running
        if not traci.isLoaded():
            print("SUMO simulation is not connected. Ensure the baseline agent started it.")
            return

        for run in range(sim_runs):
            print(f"Gathering data for run {run + 1}/{sim_runs}")

            begin_time = traci.simulation.getTime()
            end_time = traci.simulation.getEndTime()

            total_waiting_time = 0
            total_travel_time = 0
            total_queue_length = 0
            total_throughput = 0

            while traci.simulation.getTime() < end_time:
                traci.simulationStep()  # Ensure the simulation step is advancing

                # Debugging: Print simulation time to ensure it's advancing
                current_time = traci.simulation.getTime()
                print(f"Simulation time: {current_time}")

                total_waiting_time += get_average_waiting_time()
                # total_travel_time += get_average_travel_time()
                # total_queue_length += get_average_queue_length()
                # total_throughput += get_throughput()

            # Avoid division by zero
            steps = max(1, (end_time - begin_time) / 1000)
            print(f"Steps for calculation: {steps}")  # Debugging log

            avg_waiting_time = total_waiting_time / steps
            # avg_travel_time = total_travel_time / steps
            # avg_queue_length = total_queue_length / steps
            # avg_throughput = total_throughput / steps

            results.append({
                "avg_waiting_time": avg_waiting_time
                # "avg_travel_time": avg_travel_time,
                # "avg_queue_length": avg_queue_length,
                # "avg_throughput": avg_throughput,
            })

        # Aggregate results and save to CSV
        metrics = {
            "Avg Waiting Time": [result["avg_waiting_time"] for result in results]
            # "Avg Travel Time": [result["avg_travel_time"] for result in results],
            # "Avg Queue Length": [result["avg_queue_length"] for result in results],
            # "Avg Throughput": [result["avg_throughput"] for result in results],
        }

        df = pd.DataFrame(metrics)
        output_file = "baseline_performance_metrics.csv"
        df.to_csv(output_file, index=False)
        print(f"Performance metrics successfully written to {output_file}")

    # except Exception as e:
    #     print(f"Error gathering performance data: {e}")

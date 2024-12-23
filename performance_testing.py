import traci
import os
import pandas as pd

# Configuration
sumoBinary = "sumo-gui"
sumoConfig = "CustomNetworks/twoLaneMap.sumocfg"


def get_average_waiting_time():
    try:
        vehicles = traci.vehicle.getIDList()
        return sum(traci.vehicle.getWaitingTime(veh) for veh in vehicles) / max(len(vehicles), 1)
    except Exception as e:
        print(f"Error calculating average waiting time: {e}")
        return 0


def get_average_travel_time():
    try:
        vehicles = traci.vehicle.getIDList()
        return sum(traci.vehicle.getAccumulatedWaitingTime(veh) for veh in vehicles) / max(len(vehicles), 1)
    except Exception as e:
        print(f"Error calculating average travel time: {e}")
        return 0


def get_average_queue_length():
    try:
        edge_ids = traci.edge.getIDList()
        return {edge: traci.edge.getLastStepHaltingNumber(edge) for edge in edge_ids}
    except Exception as e:
        print(f"Error calculating average queue length: {e}")
        return {}


def get_throughput():
    try:
        return len(traci.simulation.getArrivedIDList())
    except Exception as e:
        print(f"Error calculating throughput: {e}")
        return 0


def gather_performance_data(sim_runs):
    try:
        results = []
        edge_ids = []

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
            total_queue_lengths = {}
            total_throughput = 0

            while traci.simulation.getTime() < end_time:
                traci.simulationStep()

                total_waiting_time += get_average_waiting_time()
                total_travel_time += get_average_travel_time()
                total_throughput += get_throughput()

                queue_lengths = get_average_queue_length()
                for edge, length in queue_lengths.items():
                    if edge not in total_queue_lengths:
                        total_queue_lengths[edge] = 0
                    total_queue_lengths[edge] += length

                if not edge_ids:
                    edge_ids = list(queue_lengths.keys())

            # Avoid division by zero
            steps = max(1, (end_time - begin_time) / 1000)
            avg_waiting_time = total_waiting_time / steps
            avg_travel_time = total_travel_time / steps
            avg_throughput = total_throughput / steps
            avg_queue_lengths = {
                edge: length / steps for edge, length in total_queue_lengths.items()
            }

            results.append({
                "avg_waiting_time": avg_waiting_time,
                "avg_travel_time": avg_travel_time,
                "avg_throughput": avg_throughput,
                "avg_queue_lengths": avg_queue_lengths,
            })

        # Aggregate results and save to CSV
        metrics = {
            "Avg Waiting Time": [result["avg_waiting_time"] for result in results],
            "Avg Travel Time": [result["avg_travel_time"] for result in results],
            "Avg Throughput": [result["avg_throughput"] for result in results],
        }

        if edge_ids:
            for edge in edge_ids:
                metrics[f"Queue Length {edge}"] = [
                    result["avg_queue_lengths"].get(edge, 0) for result in results
                ]

        df = pd.DataFrame(metrics)
        output_file = "baseline_performance_metrics.csv"
        df.to_csv(output_file, index=False)
        print(f"Performance metrics successfully written to {output_file}")

    except Exception as e:
        print(f"Error gathering performance data: {e}")

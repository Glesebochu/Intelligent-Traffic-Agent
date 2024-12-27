import traci
import os
import json
import sumolib
import pandas as pd
from traci._trafficlight import Logic, Phase
import copy

# Configuration
import os

# Code for handling incidents
INCIDENT_TYPES = ["accident", "sudden_surge"]
RESPONSE_STRATEGIES = {
    "accident": "reroute",
    "sudden_surge": "reroute",
    "road_closure": "reroute",
}

# Thresholds for incident detection
ACCIDENT_SPEED_THRESHOLD = 1  # Speed below which an accident is suspected (m/s)
SURGE_QUEUE_THRESHOLD = 20  # Queue length above which a sudden surge is suspected

import random


# A function for simulating an accident
def simulate_accident(step):
    if step == 500:  # Trigger accident at step 500
        vehicle_id = random.choice(traci.vehicle.getIDList())
        traci.vehicle.setStop(vehicle_id, edgeID="edge1", pos=100, duration=200)
        print(f"Accident simulated for vehicle {vehicle_id} at step {step}.")


# A function for detecting incidents
def detect_incidents():
    incidents = []
    for edge_id in traci.edge.getIDList():
        avg_speed = traci.edge.getLastStepMeanSpeed(edge_id)
        queue_length = traci.edge.getLastStepHaltingNumber(edge_id)
        tls_id = traci.edge.getTLSID(edge_id)
        step = traci.simulation.getCurrentTime()
        queue_history = get_queue_history(edge_id)
        adjacent_queues = get_adjacent_queues(edge_id)
        edge_speeds = get_edge_speeds(edge_id)

        if detect_accident(
            avg_speed,
            queue_length,
            tls_id,
            edge_id,
            step,
            queue_history,
            adjacent_queues,
            edge_speeds,
        ):
            incidents.append(("accident", edge_id))
        if queue_length > SURGE_QUEUE_THRESHOLD:
            incidents.append(("sudden_surge", edge_id))
        if is_road_closed(
            edge_id
        ):  # Assuming you have a function to check road closures
            incidents.append(("road_closure", edge_id))

    return incidents


def block_edge(edge_id):
    """
    Blocks all lanes of the given edge by disallowing all vehicle types.

    Parameters:
    - edge_id (str): The ID of the edge to block.

    Returns:
    - None
    """
    try:
        # Get the number of lanes for the specified edge
        num_lanes = traci.edge.getLaneNumber(edge_id)

        # Block each lane by disallowing all vehicle types
        for lane_index in range(num_lanes):
            lane_id = f"{edge_id}_{lane_index}"  # Construct lane ID
            traci.lane.setDisallowed(lane_id, ["all"])  # Disallow all vehicle types

        print(f"Edge {edge_id} is now blocked.")
    except traci.TraCIException as e:
        print(f"Error blocking edge {edge_id}: {e}")
    except Exception as e:
        print(f"Unexpected error blocking edge {edge_id}: {e}")


def is_road_closed(edge_id):
    """
    Check if the road is closed by verifying the lane's disallowed vehicle types.

    Parameters:
    - edge_id: The ID of the edge to check.

    Returns:
    - True if the road is closed, False otherwise.
    """
    try:
        # Get the number of lanes for the edge
        lanes = traci.edge.getLaneNumber(edge_id)

        for lane_index in range(lanes):
            lane_id = f"{edge_id}_{lane_index}"  # Construct the lane ID
            print(f"Checking disallowed vehicles for lane: {lane_id}")

            # Get disallowed vehicle types for the lane
            disallowed_vehicles = traci.lane.getDisallowed(lane_id)

            # If disallowed is empty, assume lane is open
            if not disallowed_vehicles:
                return (
                    False  # Road is not closed if the lane is open to any vehicle type
                )

        # If all lanes have disallowed vehicles, the road is considered closed
        return True
    except traci.TraCIException as e:
        print(f"Error checking road closure for edge {edge_id}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in is_road_closed for edge {edge_id}: {e}")
        return False


def detect_accident(
    avg_speed,
    queue_length,
    tls_id,
    road_id,
    step,
    queue_history,
    adjacent_queues,
    edge_speeds,
):
    if is_red_light_active(tls_id, road_id):
        return False  # Likely caused by red light
    if is_persistent_issue(queue_history):
        return True  # Persistent issue
    if is_localized_congestion(queue_length, adjacent_queues):
        return False  # Likely a localized issue
    if avg_speed < 10 and has_high_speed_variance(edge_speeds):
        return True  # Speed and variance indicate accident
    return False


def is_red_light_active(tls_id, road_id):
    current_phase = traci.trafficlight.getPhase(tls_id)
    controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)

    # Check if road_id corresponds to lanes affected by a red light in the current phase
    return any(
        lane.split("_")[0] == road_id
        and traci.trafficlight.getRedYellowGreenState(tls_id)[i] == "r"
        for i, lane in enumerate(controlled_lanes)
    )


def is_persistent_issue(queue_history, threshold_steps=5):
    return all(queue > 0 for queue in queue_history[-threshold_steps:])


def is_localized_congestion(current_queue, adjacent_queues, localization_threshold=3):
    avg_adjacent_queue = sum(adjacent_queues) / len(adjacent_queues)
    return current_queue > avg_adjacent_queue * localization_threshold


def has_high_speed_variance(edge_speeds, variance_threshold=5):
    return max(edge_speeds) - min(edge_speeds) > variance_threshold


def get_queue_history(edge_id):
    """
    Retrieve the queue history for the given edge.

    Parameters:
    - edge_id: The ID of the edge to retrieve the queue history for.

    Returns:
    - A list of queue lengths for the past simulation steps.
    """
    try:
        # Retrieve historical queue data from a stored dictionary or database
        # For this example, assume we have a global dictionary `queue_history_data`
        global queue_history_data
        return queue_history_data.get(edge_id, [0] * 10)
    except traci.TraCIException as e:
        print(f"Error retrieving queue history for edge {edge_id}: {e}")
        return [0] * 10
    except Exception as e:
        print(f"Unexpected error in get_queue_history for edge {edge_id}: {e}")
        return [0] * 10


def get_adjacent_queues(edge_id):
    """
    Retrieve the queue lengths of adjacent edges.

    Parameters:
    - edge_id: The ID of the edge to retrieve the adjacent queues for.

    Returns:
    - A list of queue lengths for adjacent edges.
    """
    try:
        # Retrieve adjacent edges using the SUMO network
        net = sumolib.net.readNet(sumoConfig)
        edge = net.getEdge(edge_id)
        adjacent_edges = edge.getOutgoing()
        return [
            traci.edge.getLastStepHaltingNumber(adj_edge.getID())
            for adj_edge in adjacent_edges
        ]
    except traci.TraCIException as e:
        print(f"Error retrieving adjacent queues for edge {edge_id}: {e}")
        return [0] * 5
    except Exception as e:
        print(f"Unexpected error in get_adjacent_queues for edge {edge_id}: {e}")
        return [0] * 5


def get_edge_speeds(edge_id):
    """
    Retrieve the speed data for the given edge.

    Parameters:
    - edge_id: The ID of the edge to retrieve the speed data for.

    Returns:
    - A list of speeds for the past simulation steps.
    """
    try:
        # Retrieve historical speed data from a stored dictionary or database
        # For this example, assume we have a global dictionary `speed_history_data`
        global speed_history_data
        return speed_history_data.get(edge_id, [0] * 10)
    except traci.TraCIException as e:
        print(f"Error retrieving speed data for edge {edge_id}: {e}")
        return [0] * 10
    except Exception as e:
        print(f"Unexpected error in get_edge_speeds for edge {edge_id}: {e}")
        return [0] * 10


def handle_incidents(incidents):
    for incident_type, edge_id in incidents:
        strategy = RESPONSE_STRATEGIES[incident_type]
        if strategy == "reroute":
            print(f"Detected {incident_type} on edge {edge_id}.")
            reroute_traffic(edge_id)


def reroute_traffic(edge_id):
    try:
        # Get the list of vehicles on the affected edge
        vehicles = traci.edge.getLastStepVehicleIDs(edge_id)

        for vehicle_id in vehicles:
            # Find an alternative route for each vehicle
            current_route = traci.vehicle.getRoute(vehicle_id)
            alternative_route = find_alternative_route(current_route, edge_id)

            if alternative_route:
                # Update the vehicle's route
                traci.vehicle.setRoute(vehicle_id, alternative_route)
                print(
                    f"Rerouted vehicle {vehicle_id} from edge {edge_id} to alternative route."
                )
            else:
                print(
                    f"No alternative route found for vehicle {vehicle_id} on edge {edge_id}."
                )
    except traci.TraCIException as e:
        print(f"Error rerouting traffic from edge {edge_id}: {e}")


def find_alternative_route(current_route, blocked_edge):
    # Implement logic to find an alternative route avoiding the blocked edge
    # This is a placeholder implementation and should be replaced with actual routing logic
    alternative_route = []
    for edge in current_route:
        if edge != blocked_edge:
            alternative_route.append(edge)
    return alternative_route if alternative_route else None

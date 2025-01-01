import traceback
from Python_files.performance_testing_AD import gather_performance_data
import traci
import os
import json
import sumolib
import pandas as pd
from traci._trafficlight import Logic, Phase
import random

# Configuration
import os

# Code for defining incidents and their responses
INCIDENT_TYPES = ["road_closure", "sudden_surge"]
RESPONSE_STRATEGIES = {
    "sudden_surge": "reroute",
    "road_closure": "reroute",
}

# Thresholds for incident detection
SURGE_QUEUE_THRESHOLD = 30  # Queue length above which a sudden surge is suspected

def random_block_edge(step, edge_id='59', duration=50):
    """
    Randomly blocks an edge based on a given probability.

    Parameters:
    - edge_id (str): The ID of the edge to block.
    - probability (float): The probability of blocking the edge (0 to 1).
    - duration (int): Duration (in simulation steps) to keep the edge blocked.
    """
    final_step = step
    
    if random.random() < 0.01:
        print(f"Randomly blocking edge {edge_id} for {duration} steps.")
        final_step = block_edge(step, edge_id, duration)
    
    return final_step

def block_edge(step, edge_id, duration=50):
    """
    Blocks an edge dynamically, allowing existing vehicles to depart first, 
    while preventing new vehicles from entering.

    Parameters:
    - edge_id (str): The ID of the edge to block.
    - duration (int): Duration (in simulation steps) to keep the edge blocked after clearing.
    """
    try:
        # 1. Prevent new vehicles from entering the edge
        num_lanes = traci.edge.getLaneNumber(edge_id)
        for lane_index in range(num_lanes):
            lane_id = f"{edge_id}_{lane_index}"
            traci.lane.setDisallowed(lane_id, ["all"])  # Block new entries
            traci.edge.adaptTraveltime(edge_id, 99999)

        print(f"Edge {edge_id} is now restricted to existing vehicles.")

        # 2. Recalculate routes for all vehicles in the network that pass by the edge to be blocked
        vehicle_ids = traci.vehicle.getIDList()
        for vehicle_id in vehicle_ids:
            current_route = traci.vehicle.getRoute(vehicle_id)
            if edge_id in current_route:
                print(f"Current route for vehicle {vehicle_id}: {current_route}")
                traci.vehicle.rerouteTraveltime(vehicle_id)
                print(f"New route for vehicle {vehicle_id}: {traci.vehicle.getRoute(vehicle_id)}")

        # 3. Wait until all existing vehicles leave the edge
        while traci.edge.getLastStepVehicleNumber(edge_id) > 0:
            traci.simulationStep()
            step += 1
            gather_performance_data()

        # 4. Keep the edge blocked for the specified duration
        for _ in range(duration):
            traci.simulationStep()
            step += 1
            gather_performance_data()

        # 5. Allow new vehicles to enter the edge again
        for lane_index in range(num_lanes):
            lane_id = f"{edge_id}_{lane_index}"
            traci.lane.setAllowed(lane_id, ["all"])  # Unblock new entries
            traci.edge.adaptTraveltime(edge_id, 25)

        print(f"Edge {edge_id} is now open to all vehicles again.")

    except Exception as e:
        print(f"Error during blocking edge {edge_id} at step {step}: {e}")
        traceback.print_exc()

    return step   


def is_edge_blocked(edge_id):
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
            # print(f"Checking disallowed vehicles for lane: {lane_id}")
            
            # Get disallowed vehicle types for the lane
            disallowed_vehicles = traci.lane.getDisallowed(lane_id)
            
            # If disallowed is empty, assume lane is open
            if not disallowed_vehicles:
                return False  # Road is not closed if the lane is open to any vehicle type
        
        # If all lanes have disallowed vehicles, the road is considered closed
        return True
    except traci.TraCIException as e:
        print(f"Error checking road closure for edge {edge_id}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in is_road_closed for edge {edge_id}: {e}")
        return False

# A function for detecting incidents
def detect_incidents():
    incidents = []
    for edge_id in traci.edge.getIDList():
        queue_length = traci.edge.getLastStepHaltingNumber(edge_id)
        
        if queue_length > SURGE_QUEUE_THRESHOLD:
            incidents.append(('sudden_surge', edge_id))
        if is_edge_blocked(edge_id):  # Assuming you have a function to check road closures
            incidents.append(('road_closure', edge_id))
    
    if incidents:
        handle_incidents(incidents)
    else:
        print("No incidents detected.")

def handle_incidents(incidents):
    for incident_type, edge_id in incidents:
        strategy = RESPONSE_STRATEGIES[incident_type]
        if strategy == 'reroute':
            print(f"!! Detected {incident_type} on edge {edge_id}. !!")
            print("Rerouting...")

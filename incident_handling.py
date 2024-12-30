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
SURGE_QUEUE_THRESHOLD = 20  # Queue length above which a sudden surge is suspected

def random_block_edge(edge_id='59', duration=100):
    """
    Randomly blocks an edge based on a given probability.

    Parameters:
    - edge_id (str): The ID of the edge to block.
    - probability (float): The probability of blocking the edge (0 to 1).
    - duration (int): Duration (in simulation steps) to keep the edge blocked.
    """
    if random.random() < 0.01:
        print(f"Randomly blocking edge {edge_id} for {duration} steps.")
        block_edge(edge_id, duration)

def block_edge(edge_id, duration=100):
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

        print(f"Edge {edge_id} is now restricted to existing vehicles.")

        # 2. Wait until all existing vehicles leave the edge
        while True:
            vehicles_on_edge = [
                veh_id for veh_id in traci.vehicle.getIDList() 
                if traci.vehicle.getRoadID(veh_id) == edge_id
            ]

            if not vehicles_on_edge:  # No more vehicles on the edge
                break  # Proceed to blocking the edge completely
            traci.simulationStep()  # Continue simulation until clear

        print(f"Edge {edge_id} is now clear of vehicles. Proceeding to full block.")

        # 3. Block the edge completely for the specified duration
        for lane_index in range(num_lanes):
            lane_id = f"{edge_id}_{lane_index}"
            traci.lane.setDisallowed(lane_id, ["all"])  # Fully block all vehicles

        print(f"Edge {edge_id} is now fully blocked for {duration} steps.")

        # 4. Keep the edge blocked for the specified duration
        for _ in range(duration):
            traci.simulationStep()

        # 5. Unblock the edge after the duration ends
        for lane_index in range(num_lanes):
            lane_id = f"{edge_id}_{lane_index}"
            traci.lane.setAllowed(lane_id, ["all"])  # Restore permissions

        print(f"Edge {edge_id} is now unblocked.")

    except traci.TraCIException as e:
        print(f"Error handling edge {edge_id}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        
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

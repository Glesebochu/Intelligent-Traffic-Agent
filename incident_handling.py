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


def block_edge_with_reroute(edge_id):
    """
    Blocks an edge and forces vehicles to reroute dynamically.
    """
    try:
        # Enable rerouting for all vehicles to dynamically adjust their routes in response to the blocked edge
        for veh_id in traci.vehicle.getIDList():
            traci.vehicle.setParameter(veh_id, "device.rerouting.period", "10")  # Reroute every 10 seconds

        # Block each lane of the edge
        num_lanes = traci.edge.getLaneNumber(edge_id)
        for lane_index in range(num_lanes):
            lane_id = f"{edge_id}_{lane_index}"
            traci.lane.setDisallowed(lane_id, ["all"])  # Block the lane

        # Force reroute for vehicles already on the edge
        for veh_id in traci.vehicle.getIDList():
            if traci.vehicle.getRoadID(veh_id) == edge_id:
                traci.vehicle.rerouteTraveltime(veh_id)  # Force rerouting immediately

        print(f"Edge {edge_id} is now blocked, and rerouting is enabled.")

    except traci.TraCIException as e:
        print(f"Error blocking edge {edge_id}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def is_edge_closed(edge_id):
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
        
        block_edge_with_reroute(edge_id)
        
        for lane_index in range(lanes):
            lane_id = f"{edge_id}_{lane_index}"  # Construct the lane ID
            print(f"Checking disallowed vehicles for lane: {lane_id}")
            
            
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
        avg_speed = traci.edge.getLastStepMeanSpeed(edge_id)
        queue_length = traci.edge.getLastStepHaltingNumber(edge_id)
        tls_id = traci.edge.getTLSID(edge_id)
        step = traci.simulation.getCurrentTime()
        
        if queue_length > SURGE_QUEUE_THRESHOLD:
            incidents.append(('sudden_surge', edge_id))
        if is_edge_closed(edge_id):  # Assuming you have a function to check road closures
            incidents.append(('road_closure', edge_id))
    
    return incidents

def handle_incidents(incidents):
    for incident_type, edge_id in incidents:
        strategy = RESPONSE_STRATEGIES[incident_type]
        if strategy == 'reroute':
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
                print(f"Rerouted vehicle {vehicle_id} from edge {edge_id} to alternative route.")
            else:
                print(f"No alternative route found for vehicle {vehicle_id} on edge {edge_id}.")
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
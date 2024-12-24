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
INCIDENT_TYPES = ['accident', 'sudden_surge']
RESPONSE_STRATEGIES = {
    'accident': 'reroute',
    'sudden_surge': 'reroute',
    'road_closure': 'reroute'
}

# Thresholds for incident detection
ACCIDENT_SPEED_THRESHOLD = 2  # Speed below which an accident is suspected (m/s)
SURGE_QUEUE_THRESHOLD = 20    # Queue length above which a sudden surge is suspected

import random

# A function for simulating an accident
def simulate_accident(step):
    if step == 500:  # Trigger accident at step 500
        vehicle_id = random.choice(traci.vehicle.getIDList())
        traci.vehicle.setStop(vehicle_id, edgeID="edge1", pos=100, duration=200)
        print(f"Accident simulated for vehicle {vehicle_id} at step {step}.")
        
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
        
        if detect_accident(avg_speed, queue_length, tls_id, edge_id, step, queue_history, adjacent_queues, edge_speeds):
            incidents.append(('accident', edge_id))
        elif queue_length > SURGE_QUEUE_THRESHOLD:
            incidents.append(('sudden_surge', edge_id))
    
    return incidents

def detect_accident(avg_speed, queue_length, tls_id, road_id, step, queue_history, adjacent_queues, edge_speeds):
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
        lane.split("_")[0] == road_id and traci.trafficlight.getRedYellowGreenState(tls_id)[i] == "r"
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
    # Placeholder function to retrieve queue history for the edge
    return [0] * 10  # Replace with actual logic

def get_adjacent_queues(edge_id):
    # Placeholder function to retrieve queue lengths of adjacent edges
    return [0] * 5  # Replace with actual logic

def get_edge_speeds(edge_id):
    # Placeholder function to retrieve speed data for the edge
    return [0] * 10  # Replace with actual logic
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
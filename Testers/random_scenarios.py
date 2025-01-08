# random_scenarios.py

import random
import traci

# Scenario Parameters
ACCIDENT_INTERVAL = 100  # Time interval to introduce accidents (10 minutes)


# Function to simulate random incidents (accidents, road closures)
def simulate_random_incidents(step):
    """
    Introduce random incidents (like accidents or road closures) into the simulation.
    """
    all_lanes = []
    print(f"step: {step}")
    try:
        if step % ACCIDENT_INTERVAL == 0:
            # Get all traffic light IDs in the simulation
            tls_ids = traci.trafficlight.getIDList()

            # Collect all lanes controlled by traffic lights
            for tls_id in tls_ids:
                lanes = traci.trafficlight.getControlledLanes(tls_id)
                all_lanes.extend(lanes)

            # Get unique road IDs by extracting road part of lane IDs (typically 'roadID_laneID')
            road_ids = set()
            for lane in all_lanes:
                road_id = lane.split("_")[
                    0
                ]  # Extract road ID from lane ID (assuming lane ID format is 'roadID_laneID')
                road_ids.add(road_id)
            # Choose a random road ID from the available roads
            if road_ids:
                road_id = random.choice(
                    list(road_ids)
                )  # Choose a random road from the set of road IDs
                print(f"Introducing road closure on {road_id} at step {step}")

                # Get the traffic light associated with the road
                tls_id = random.choice(
                    tls_ids
                )  # Randomly pick a traffic light controlling this road
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)

                # Calculate the number of red phases based on controlled lanes
                num_red_phases = len(controlled_lanes)
                red_state = (
                    "r" * num_red_phases
                )  # Create a string with 'r' for each lane

                print(f"Setting red phases to {red_state} for traffic light {tls_id}")

                # Simulate road closure by setting all traffic lights on that road to red
                traci.trafficlight.setRedYellowGreenState(
                    tls_id, red_state
                )  # Block traffic by turning all signals red
            else:
                print("No road IDs found to simulate a closure.")

        else:
            # Simulate an accident by blocking lanes for a short period
            # Dynamically choose a lane from the previously collected lanes
            if all_lanes:
                lane_id = random.choice(all_lanes)
                print(f"Simulating accident on {lane_id} at step {step}")
                traci.lane.setMaxSpeed(
                    lane_id, 0
                )  # Set max speed to 0 to simulate an accident (no movement)

    except traci.TraCIException as e:
        print(f"Error simulating random incidents at step {step}: {e}")
    except Exception as e:
        print(f"Unexpected error in simulate_random_incidents at step {step}: {e}")


# Function to run all randomizing functions
def apply_random_scenarios(step):
    """
    Call all randomizing functions for testing scenarios (traffic demand, incidents, etc.).
    """
    print("Running all randomizing functions")
    try:
        simulate_random_incidents(step)
    except Exception as e:
        print(f"Error applying random scenarios at step {step}: {e}")

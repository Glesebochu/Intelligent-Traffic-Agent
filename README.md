# Intelligent-Traffic-Agent

An intelligent agent within the Simulation of Urban MObility (SUMO) platform to optimize traffic signal control in a simulated urban environment. The agent's goal is to reduce traffic congestion, improve traffic flow efficiency, and adapt to dynamic traffic patterns.

### **Simulation Environment**

- **SUMO Platform:** Utilize the open-source SUMO software for simulating urban traffic.
- **Urban Network:** Create a synthetic urban road network with multiple intersections and roads.
- **Traffic Demand:** Simulate realistic traffic flows, including rush hours, surges of vehicles, and unpredictable events.

### **Intelligent Agent Design**

- **PEAS Framework**
  - **Performance Measure:**
    - Minimize average travel time and vehicle waiting time at intersections.
    - Reduce overall traffic congestion and queue lengths.
    - Maintain balanced traffic flow throughout the network.
  - **Environment:**
    - A dynamic urban traffic network simulated by SUMO.
    - Includes multiple intersections, road segments, and traffic flows.
  - **Actuators:**
    - Control over traffic signal durations at intersections.
    - Ability to implement adaptive signal control strategies.
  - **Sensors:**
    - Real-time traffic data, including vehicle counts, speeds, queue lengths, and waiting times.
    - Detection of incidents or anomalies in traffic patterns.
- **Decision-Making Framework**
  - **Rule-Based System:**
    - Implement initial traffic signal control based on predefined rules (e.g., fixed-time control).
  - **Adaptive Control:**
    - Develop algorithms that adjust signal timings in response to real-time traffic conditions.
    - Use techniques such as threshold-based adjustments or state machine logic.
  - **Learning Capabilities (\*Future Extension):**
    - Integrate machine learning methods (e.g., reinforcement learning) to enable the agent to learn optimal control policies over time.

### **Simulation Scenarios**

- **Variable Traffic Demand:**
  - Simulate different traffic volumes, including peak and off-peak hours.
- **Random Events:**
  - Introduce incidents such as sudden surges or road closures to test the agent's adaptability.
- **Environmental Factors: (\*Future Extension)**
  - Consider weather conditions that may affect traffic flow (e.g., rain, fog).

## Installation Guide

You can get started on our agent by cloning this repo and following the installation steps [here](INSTALLATION.md).

## Taking our software out for a run

Go to our [V6 Adaptive Agent](Agents/V6adaptive_agent.py) and just run it with `python -u`.

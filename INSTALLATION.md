## **1. Install and Configure SUMO**

### **Objective:**

Set up the Simulation of Urban MObility (SUMO) on Windows 11 for traffic simulation.

### **Requirements:**

- **Windows 11, 64-bit**
- Python 3.6+ installed
- **Microsoft C++ Build Tools**
- Text editor or IDE (e.g., VS Code)

### **Steps:**

1. **System Check:**

   - Confirm Windows 11, 64-bit, and sufficient hardware resources.
   - Install **Microsoft C++ Build Tools** from [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022).
   - Select **"Desktop development with C++"** and required components during installation.

2. **Download and Install SUMO:**

   - Download the latest version from the [SUMO Downloads Page](https://sumo.dlr.de/docs/Downloads.php).
   - Run the installer and check **"Add SUMO to PATH"** during installation.
   - Verify installation:
     ```bash
     sumo
     ```
     The SUMO help menu should appear.

3. **Install TraCI (Traffic Control Interface):**

   - Open **Command Prompt (Admin):**
     ```bash
     pip install sumo
     ```
   - Ensure SUMO’s `tools` directory is accessible via Python.

4. **Test TraCI Connection:**

   - Create `test_traci.py` with the following code:

     ```python
     import traci, os

     if 'SUMO_HOME' in os.environ:
         tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
         import sys
         sys.path.append(tools)
     else:
         sys.exit("SUMO_HOME not set")

     traci.start(["sumo", "-c", "path/to/config.sumocfg"])
     print("Connected to SUMO via TraCI")
     traci.close()
     ```

   - Run the script:
     ```bash
     python test_traci.py
     ```
   - Expected output:
     ```
     Connected to SUMO via TraCI
     ```

### **Tips:**

- Refer to the [SUMO Documentation](https://sumo.dlr.de/docs/) for troubleshooting.
- Use community forums and GitHub issues for support.
- Ensure version compatibility between SUMO and Python.


import traci


def test_connection():
    print("Starting TraCI connection...")
    # Use the basemap.sumocfg file in your repository
    traci.start(["sumo", "-c", "basemap/basemap.sumocfg"])
    print("TraCI connection successful!")
    traci.close()

if __name__ == "__main__":
    test_connection()

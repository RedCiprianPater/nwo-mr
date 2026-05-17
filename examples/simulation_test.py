"""
Example: Robot Simulation Workflow
Tests robot in MR before physical deployment
"""

from nwo_mr import NWOMRClient, SimulationConfig
from nwo_robotics_cs import NWORoboticsClient


def main():
    # Initialize both systems
    nwo_mr = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0x...",
        private_key="0x..."
    )
    
    nwo_cs = NWORoboticsClient(
        api_url="https://nwo-capital-api.onrender.com/api"
    )
    
    # Get robot spec
    robot_spec = nwo_cs.get_robot_spec("pick_place_arm_v3")
    print(f"Loaded robot: {robot_spec['name']}")
    
    # Create simulation
    sim_config = SimulationConfig(
        world="warehouse_a",
        physics="mujoco",
        render="vr",
        robot_spec=robot_spec
    )
    
    sim = nwo_mr.simulation.create(sim_config)
    print(f"Simulation created: {sim['id']}")
    
    # Run task
    result = nwo_mr.simulation.run_task(
        simulation_id=sim['id'],
        task="pick_and_place",
        objects=["box_1", "box_2", "pallet_a"],
        iterations=100,
        record=True
    )
    
    print(f"Success rate: {result['success_rate']}%")
    print(f"Average time: {result['avg_time']}s")
    print(f"Energy used: {result['energy']}J")
    
    # If successful, deploy to real robot
    if result['success_rate'] > 95:
        print("Simulation passed! Deploying to physical robot...")
        deployment = nwo_cs.deploy(robot_spec, environment="warehouse_a")
        print(f"Deployed: {deployment['id']}")
    else:
        print("Simulation failed. Adjusting parameters...")


if __name__ == "__main__":
    main()

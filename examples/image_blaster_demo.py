"""
Example: Image Blaster Integration with NWO MR
Generate 3D environments from images and use in simulations
"""

from nwo_mr import NWOMRClient
from nwo_mr.image_blaster import ImageBlasterIntegration, BlasterConfig


def main():
    # Initialize NWO MR
    mr_client = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0x...",
        private_key="0x..."
    )
    
    # Initialize Image Blaster
    config = BlasterConfig(
        world_labs_api_key="wl_...",
        fal_api_key="fal_...",
        elevenlabs_api_key="el_...",
        face_count=50000,
        enable_pbr=True,
        generate_type="Normal"
    )
    
    blaster = ImageBlasterIntegration(config)
    
    print("=== Image Blaster + NWO MR Demo ===\n")
    
    # Example 1: Blast single image
    print("1. Blasting image to 3D scene...")
    scene = blaster.blast_image(
        image_path="factory_floor.jpg",
        scene_name="industrial_factory",
        confirm_steps=True
    )
    
    print(f"   Created scene: {scene.scene_id}")
    print(f"   Objects: {len(scene.objects)}")
    print(f"   Sounds: {len(scene.sounds)}")
    print(f"   Environment: {scene.environment_spz}")
    
    # Example 2: Import to NWO MR
    print("\n2. Importing to NWO MR...")
    mr_scene = blaster.import_to_nwo_mr(
        blasted_scene=scene,
        mr_client=mr_client,
        world_name="factory_training_ground"
    )
    
    print(f"   Simulation ID: {mr_scene['simulation_id']}")
    print(f"   World: {mr_scene['world_name']}")
    
    # Example 3: Test robot in generated environment
    print("\n3. Testing robot in generated environment...")
    sim = mr_client.simulation.enter(mr_scene['simulation_id'])
    
    # Spawn robot
    robot = mr_client.simulation.spawn_robot(
        simulation_id=mr_scene['simulation_id'],
        robot_type="pick_place_arm"
    )
    
    # Run tests
    result = mr_client.simulation.run_task(
        simulation_id=mr_scene['simulation_id'],
        task="navigate_and_grasp",
        iterations=50
    )
    
    print(f"   Success rate: {result['success_rate']}%")
    print(f"   Ready for physical deployment: {result['success_rate'] > 95}")
    
    # Example 4: Create NFT from scene
    print("\n4. Creating marketplace NFT...")
    nft = blaster.create_marketplace_nft(
        blasted_scene=scene,
        mr_client=mr_client,
        price_eth=0.5,
        royalty=0.05
    )
    
    print(f"   NFT ID: {nft['nft_id']}")
    print(f"   Listed for: {nft['price']} ETH")
    print(f"   Royalty: {nft['royalty'] * 100}%")
    
    print("\n=== Demo Complete ===")


def batch_example():
    """Batch process multiple images for training dataset."""
    
    config = BlasterConfig(
        world_labs_api_key="wl_...",
        fal_api_key="fal_..."
    )
    
    blaster = ImageBlasterIntegration(config)
    
    # Batch blast multiple environments
    images = [
        "warehouse_1.jpg",
        "warehouse_2.jpg",
        "kitchen.jpg",
        "office.jpg",
        "construction_site.jpg"
    ]
    
    def progress_callback(current, total, scene, error):
        if error:
            print(f"  [{current+1}/{total}] Failed: {error}")
        else:
            print(f"  [{current+1}/{total}] Completed: {scene.scene_id}")
    
    print("Batch blasting images...")
    scenes = blaster.batch_blast(images, callback=progress_callback)
    
    print(f"\nCompleted: {len([s for s in scenes if s])}/{len(images)} scenes")


def agent_autonomous_example():
    """Agent autonomously creates and sells environments."""
    
    from nwo_mr.agent_economy import AgentEconomy
    
    mr_client = NWOMRClient(...)
    economy = AgentEconomy(mr_client)
    
    blaster = ImageBlasterIntegration(BlasterConfig(...))
    
    # Agent finds or generates concept
    concept = "futuristic robot charging station"
    
    # Generate image from concept
    print(f"Agent generating scene for: {concept}")
    scene = blaster.blast_from_description(
        description=concept,
        generate_image=True,
        image_model="gpt-image-2"
    )
    
    # Import to MR
    mr_scene = blaster.import_to_nwo_mr(scene, mr_client)
    
    # Test if it's good for robot training
    result = mr_client.simulation.run_task(
        mr_scene['simulation_id'],
        "robot_navigation",
        iterations=20
    )
    
    if result['success_rate'] > 90:
        # High quality - sell as premium NFT
        nft = blaster.create_marketplace_nft(
            scene, mr_client,
            price_eth=1.0,  # Premium price
            royalty=0.07
        )
        print(f"Agent created and listed premium environment: {nft['nft_id']}")
    else:
        # Lower quality - sell cheaper or keep for personal use
        print("Scene quality insufficient for marketplace - keeping for training")


if __name__ == "__main__":
    main()
    # batch_example()
    # agent_autonomous_example()

"""
Image Blaster integration for NWO MR.
Rapid 3D environment generation from single images.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
import subprocess
import json
from pathlib import Path


@dataclass
class BlastedScene:
    """Result from Image Blaster pipeline."""
    scene_id: str
    source_image: str
    environment_spz: str  # Gaussian splat
    objects: List[Dict[str, str]]  # List of {'name': str, 'path': str, 'format': str}
    sounds: List[Dict[str, str]]  # List of {'name': str, 'path': str, 'type': str}
    metadata: Dict[str, Any]


@dataclass
class BlasterConfig:
    """Configuration for Image Blaster."""
    world_labs_api_key: str
    fal_api_key: str
    elevenlabs_api_key: Optional[str] = None
    face_count: int = 50000
    enable_pbr: bool = True
    generate_type: str = "Normal"  # Normal, LowPoly, Geometry
    polygon_type: str = "triangle"  # triangle, quadrilateral
    prefer_gpt_image: bool = False


class ImageBlasterIntegration:
    """
    Integration with Image Blaster for rapid 3D environment generation.
    
    Transforms single images into complete 3D scenes:
    - Gaussian splat environments (World Labs)
    - 3D object meshes (Hunyuan-3D via FAL)
    - Ambient & physics sound effects (ElevenLabs)
    
    Perfect for:
    - Rapid robot training environment creation
    - Agent-designed virtual spaces
    - NFT marketplace 3D assets
    - Collaborative MR workspaces
    """
    
    def __init__(
        self,
        config: BlasterConfig,
        working_dir: str = "/tmp/image-blaster"
    ):
        self.config = config
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up directories
        self.input_dir = self.working_dir / "input"
        self.output_dir = self.working_dir / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def blast_image(
        self,
        image_path: str,
        scene_name: Optional[str] = None,
        confirm_steps: bool = True
    ) -> BlastedScene:
        """
        Transform single image into complete 3D scene.
        
        Pipeline:
        1. Copy image to input directory
        2. Run Image Blaster via Claude
        3. Parse output files
        4. Return structured scene data
        """
        import shutil
        from datetime import datetime
        
        # Generate scene ID
        scene_id = scene_name or f"scene_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        scene_output_dir = self.output_dir / scene_id
        scene_output_dir.mkdir(exist_ok=True)
        
        # Copy image to input
        input_image = self.input_dir / f"{scene_id}.jpg"
        shutil.copy(image_path, input_image)
        
        # Build Claude command
        claude_prompt = self._build_claude_prompt(scene_id, confirm_steps)
        
        # Execute Image Blaster pipeline
        # This would typically run Claude Code with the skill
        result = self._execute_blaster(scene_id, input_image, scene_output_dir)
        
        # Parse results
        return self._parse_output(scene_id, image_path, scene_output_dir)
    
    def _build_claude_prompt(self, scene_name: str, confirm_steps: bool) -> str:
        """Build prompt for Claude Code."""
        prompt = f"""Please blast the image in input/{scene_name}.jpg and create a complete 3D scene.

Configuration:
- Face count: {self.config.face_count}
- PBR materials: {self.config.enable_pbr}
- Generate type: {self.config.generate_type}
- Polygon type: {self.config.polygon_type}
"""
        
        if confirm_steps:
            prompt += "\nPlease confirm each step with me before proceeding."
        
        if self.config.prefer_gpt_image:
            prompt += "\nPrefer GPT-Image-2 for image editing tasks."
        
        return prompt
    
    def _execute_blaster(
        self,
        scene_id: str,
        input_image: Path,
        output_dir: Path
    ) -> Dict:
        """
        Execute Image Blaster pipeline.
        
        In production, this would:
        1. Launch Claude Code with image-blaster skills
        2. Monitor progress
        3. Collect output files
        """
        # Set environment variables for API keys
        env = os.environ.copy()
        env["WORLD_LABS_API_KEY"] = self.config.world_labs_api_key
        env["FAL_API_KEY"] = self.config.fal_api_key
        if self.config.elevenlabs_api_key:
            env["ELEVENLABS_API_KEY"] = self.config.elevenlabs_api_key
        
        # Simulate execution (in production, this runs Claude)
        return {
            "status": "success",
            "scene_id": scene_id,
            "output_dir": str(output_dir)
        }
    
    def _parse_output(self, scene_id: str, source_image: str, output_dir: Path) -> BlastedScene:
        """Parse Image Blaster output into structured data."""
        objects = []
        sounds = []
        environment_spz = ""
        
        # Find all output files
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                name = file_path.stem
                
                if suffix == ".spz":
                    environment_spz = str(file_path)
                elif suffix in [".glb", ".obj"]:
                    objects.append({
                        "name": name,
                        "path": str(file_path),
                        "format": suffix[1:]
                    })
                elif suffix == ".mp3":
                    sound_type = "ambient" if "ambient" in name.lower() else "physics"
                    sounds.append({
                        "name": name,
                        "path": str(file_path),
                        "type": sound_type
                    })
        
        # Load metadata if exists
        metadata_path = output_dir / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        
        return BlastedScene(
            scene_id=scene_id,
            source_image=source_image,
            environment_spz=environment_spz,
            objects=objects,
            sounds=sounds,
            metadata=metadata
        )
    
    def blast_from_description(
        self,
        description: str,
        generate_image: bool = True,
        image_model: str = "gpt-image-2"
    ) -> BlastedScene:
        """
        Generate scene from text description.
        
        1. Generate reference image from description (optional)
        2. Blast image to 3D scene
        """
        if generate_image:
            # Generate image first
            image_path = self._generate_image(description, image_model)
        else:
            raise ValueError("Must provide image_path if generate_image=False")
        
        return self.blast_image(image_path, scene_name=description[:30].replace(" ", "_"))
    
    def _generate_image(self, description: str, model: str) -> str:
        """Generate reference image from description."""
        # This would integrate with DALL-E, Midjourney, or GPT-Image
        # For now, placeholder
        image_path = self.input_dir / f"generated_{hash(description)}.jpg"
        return str(image_path)
    
    def import_to_nwo_mr(
        self,
        blasted_scene: BlastedScene,
        mr_client,
        world_name: Optional[str] = None
    ) -> Dict:
        """
        Import blasted scene into NWO MR.
        
        Uploads all assets and creates simulation environment.
        """
        world_name = world_name or f"blasted_{blasted_scene.scene_id}"
        
        # Upload environment (Gaussian splat)
        env_upload = mr_client._request(
            'POST',
            '/v1/mr/simulation/upload-environment',
            {
                'name': world_name,
                'gaussian_splat': blasted_scene.environment_spz,
                'format': 'spz'
            }
        )
        
        # Upload 3D objects
        object_ids = []
        for obj in blasted_scene.objects:
            with open(obj['path'], 'rb') as f:
                obj_upload = mr_client._request(
                    'POST',
                    '/v1/mr/simulation/upload-object',
                    {
                        'name': obj['name'],
                        'format': obj['format'],
                        'file': f.read()  # In practice, use multipart upload
                    }
                )
                object_ids.append(obj_upload['object_id'])
        
        # Upload sounds
        sound_ids = []
        for sound in blasted_scene.sounds:
            with open(sound['path'], 'rb') as f:
                sound_upload = mr_client._request(
                    'POST',
                    '/v1/mr/simulation/upload-sound',
                    {
                        'name': sound['name'],
                        'type': sound['type'],
                        'file': f.read()
                    }
                )
                sound_ids.append(sound_upload['sound_id'])
        
        # Create simulation with all assets
        sim_config = {
            'world': world_name,
            'physics': 'mujoco',
            'render': 'mr',
            'environment_id': env_upload['environment_id'],
            'objects': object_ids,
            'sounds': sound_ids,
            'source_image': blasted_scene.source_image
        }
        
        simulation = mr_client.simulation.create(sim_config)
        
        return {
            'simulation_id': simulation['id'],
            'world_name': world_name,
            'environment_id': env_upload['environment_id'],
            'objects': object_ids,
            'sounds': sound_ids,
            'source_image': blasted_scene.source_image
        }
    
    def create_marketplace_nft(
        self,
        blasted_scene: BlastedScene,
        mr_client,
        price_eth: float = 0.5,
        royalty: float = 0.05
    ) -> Dict:
        """
        Package blasted scene as NFT for marketplace.
        
        Creates artifact from 3D scene and lists on NWO MR market.
        """
        # Create artifact
        artifact = mr_client.market.design_artifact(
            category="3d_environment",
            name=f"Blasted Scene: {blasted_scene.scene_id}",
            attributes={
                "objects_count": len(blasted_scene.objects),
                "sounds_count": len(blasted_scene.sounds),
                "has_gaussian_splat": bool(blasted_scene.environment_spz),
                "generation_method": "image_blaster",
                "rarity": self._calculate_rarity(blasted_scene)
            },
            visual_3d=blasted_scene.objects[0]['path'] if blasted_scene.objects else None,
            compatible_with=["unity", "unreal", "godot", "threejs", "nwo_mr"]
        )
        
        # Mint NFT
        nft = mr_client.market.mint_nft(
            artifact=artifact,
            collection="NWO_Blasted_Environments",
            royalty=royalty
        )
        
        # List for sale
        listing = mr_client.market.list_nft(
            nft_id=nft.id,
            price=price_eth,
            currency="ETH",
            auction=False,
            duration_days=30
        )
        
        return {
            'nft_id': nft.id,
            'artifact_id': artifact.id,
            'listing_id': listing['id'],
            'price': price_eth,
            'royalty': royalty
        }
    
    def _calculate_rarity(self, scene: BlastedScene) -> str:
        """Calculate rarity based on scene complexity."""
        score = len(scene.objects) + len(scene.sounds)
        if scene.environment_spz:
            score += 5
        
        if score >= 15:
            return "legendary"
        elif score >= 10:
            return "epic"
        elif score >= 5:
            return "rare"
        elif score >= 3:
            return "uncommon"
        else:
            return "common"
    
    def batch_blast(
        self,
        image_paths: List[str],
        callback=None
    ) -> List[BlastedScene]:
        """
        Batch process multiple images.
        
        Useful for creating training datasets or marketplace collections.
        """
        results = []
        
        for i, image_path in enumerate(image_paths):
            try:
                scene = self.blast_image(
                    image_path,
                    scene_name=f"batch_{i}_{Path(image_path).stem}"
                )
                results.append(scene)
                
                if callback:
                    callback(i, len(image_paths), scene, None)
                    
            except Exception as e:
                if callback:
                    callback(i, len(image_paths), None, e)
                results.append(None)
        
        return results

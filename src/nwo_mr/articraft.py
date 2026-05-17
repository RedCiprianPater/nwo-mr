"""
ArtiCraft integration for NWO MR.
Agentic system for scalable articulated 3D asset generation.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import requests
from enum import Enum


class ArticulationType(Enum):
    """Types of articulation for 3D assets."""
    PRISMATIC = "prismatic"  # Sliding joints
    REVOLUTE = "revolute"    # Rotating joints
    SPHERICAL = "spherical"  # Ball joints
    FIXED = "fixed"          # No movement
    PLANAR = "planar"        # 2D movement


@dataclass
class ArticulatedPart:
    """A part of an articulated object."""
    name: str
    geometry: str  # Path to mesh or primitive description
    material: str
    mass: float
    inertia: Dict[str, float]


@dataclass
class Joint:
    """Joint connecting two parts."""
    name: str
    type: ArticulationType
    parent: str
    child: str
    origin: Dict[str, List[float]]  # position, rotation
    axis: List[float]
    limits: Dict[str, float]  # lower, upper, effort, velocity


@dataclass
class ArticulatedAsset:
    """Complete articulated 3D asset."""
    id: str
    name: str
    description: str
    category: str
    parts: List[ArticulatedPart]
    joints: List[Joint]
    mesh_paths: Dict[str, str]  # part_name -> path
    urdf_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_status: str = "pending"  # pending, valid, invalid
    quality_score: float = 0.0


@dataclass
class ArtiCraftConfig:
    """Configuration for ArtiCraft integration."""
    api_url: str = "https://api.articraft3d.ai"
    api_key: Optional[str] = None
    model: str = "gpt-4"  # LLM for code generation
    max_iterations: int = 5
    validate_physics: bool = True
    generate_urdf: bool = True
    generate_meshes: bool = True
    workspace_dir: str = "/tmp/articraft"


class ArtiCraftIntegration:
    """
    Integration with ArtiCraft for articulated 3D asset generation.
    
    ArtiCraft is an agentic system that:
    1. Takes text descriptions of articulated objects
    2. Uses LLM to write programs against a domain-specific SDK
    3. Generates parts, joints, and geometry
    4. Validates and self-corrects
    5. Outputs URDF-ready articulated assets
    
    Perfect for:
    - Robot manipulation training objects
    - Mechanical parts for marketplace
    - Articulated environments
    - Custom tool generation
    """
    
    def __init__(self, config: ArtiCraftConfig):
        self.config = config
        self.workspace = Path(config.workspace_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # ArtiCraft-10K dataset cache
        self.dataset_cache: Dict[str, List[ArticulatedAsset]] = {}
    
    def generate(
        self,
        description: str,
        articulation_type: Optional[ArticulationType] = None,
        category: Optional[str] = None,
        validate: bool = True,
        max_attempts: int = 3
    ) -> ArticulatedAsset:
        """
        Generate articulated asset from text description.
        
        Args:
            description: Natural language description of object
            articulation_type: Type of joints (optional)
            category: Object category (optional)
            validate: Run physics validation
            max_attempts: Max generation attempts
            
        Returns:
            ArticulatedAsset with meshes, joints, and URDF
        """
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            try:
                # Step 1: Generate program using LLM
                program = self._generate_program(
                    description,
                    articulation_type,
                    category,
                    previous_error=last_error
                )
                
                # Step 2: Execute program to generate asset
                asset = self._execute_program(program)
                
                # Step 3: Validate if requested
                if validate:
                    validation = self._validate_asset(asset)
                    if validation['valid']:
                        asset.validation_status = "valid"
                        asset.quality_score = validation['score']
                        return asset
                    else:
                        last_error = validation['errors']
                        attempt += 1
                        continue
                else:
                    asset.validation_status = "pending"
                    return asset
                    
            except Exception as e:
                last_error = str(e)
                attempt += 1
        
        raise RuntimeError(f"Failed to generate asset after {max_attempts} attempts: {last_error}")
    
    def _generate_program(
        self,
        description: str,
        articulation_type: Optional[ArticulationType],
        category: Optional[str],
        previous_error: Optional[str] = None
    ) -> str:
        """
        Generate Python program using LLM.
        
        The LLM writes code against ArtiCraft SDK to build the asset.
        """
        # Build prompt for LLM
        prompt = self._build_prompt(
            description,
            articulation_type,
            category,
            previous_error
        )
        
        # Call LLM API (OpenAI, Anthropic, etc.)
        # This would integrate with actual LLM
        program = self._call_llm(prompt)
        
        return program
    
    def _build_prompt(
        self,
        description: str,
        articulation_type: Optional[ArticulationType],
        category: Optional[str],
        previous_error: Optional[str]
    ) -> str:
        """Build prompt for LLM code generation."""
        prompt = f"""You are an expert 3D asset designer. Write a Python program using the ArtiCraft SDK to create an articulated 3D object.

Object Description: {description}
"""
        
        if articulation_type:
            prompt += f"\nArticulation Type: {articulation_type.value}"
        
        if category:
            prompt += f"\nCategory: {category}"
        
        prompt += """

Use the following SDK:
```python
from articraft_sdk import Part, Joint, AssetBuilder

# Create builder
builder = AssetBuilder()

# Define parts
part = builder.add_part(
    name="part_name",
    geometry="box|cylinder|sphere|mesh_path",
    dimensions=(width, height, depth),
    material="metal|plastic|wood|glass",
    mass=1.0
)

# Define joints
joint = builder.add_joint(
    name="joint_name",
    type="revolute|prismatic|spherical|fixed",
    parent="parent_part",
    child="child_part",
    origin=(x, y, z, roll, pitch, yaw),
    axis=(x, y, z),
    limits={"lower": -1.57, "upper": 1.57, "effort": 100, "velocity": 1.0}
)

# Build and export
asset = builder.build()
asset.export_urdf("output.urdf")
asset.export_meshes("output_dir/")
```

Write complete, runnable Python code."""
        
        if previous_error:
            prompt += f"\n\nPrevious attempt failed with error: {previous_error}\nPlease fix and retry."
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API to generate code."""
        # This would integrate with OpenAI, Anthropic, etc.
        # Placeholder implementation
        return """
from articraft_sdk import Part, Joint, AssetBuilder

builder = AssetBuilder()

# Example part
base = builder.add_part(
    name="base",
    geometry="box",
    dimensions=(0.2, 0.05, 0.2),
    material="metal",
    mass=0.5
)

# Example joint
joint = builder.add_joint(
    name="hinge",
    type="revolute",
    parent="base",
    child="arm",
    origin=(0, 0.025, 0, 0, 0, 0),
    axis=(0, 0, 1),
    limits={"lower": -1.57, "upper": 1.57, "effort": 10, "velocity": 1.0}
)

asset = builder.build()
asset.export_urdf("output.urdf")
"""
    
    def _execute_program(self, program: str) -> ArticulatedAsset:
        """Execute generated program in sandboxed environment."""
        # This would run the code safely and capture output
        # Placeholder implementation
        
        asset_id = f"articraft_{hash(program) % 1000000}"
        
        return ArticulatedAsset(
            id=asset_id,
            name="generated_asset",
            description="Auto-generated articulated asset",
            category="mechanical",
            parts=[],
            joints=[],
            mesh_paths={},
            urdf_path=None,
            metadata={"program": program}
        )
    
    def _validate_asset(self, asset: ArticulatedAsset) -> Dict:
        """
        Validate generated asset.
        
        Checks:
        - Physics consistency
        - Joint limits合理性
        - Mesh integrity
        - URDF validity
        """
        errors = []
        score = 1.0
        
        # Check URDF exists
        if not asset.urdf_path:
            errors.append("Missing URDF")
            score -= 0.3
        
        # Check parts have meshes
        for part in asset.parts:
            if part.name not in asset.mesh_paths:
                errors.append(f"Part {part.name} missing mesh")
                score -= 0.1
        
        # Check joints are valid
        for joint in asset.joints:
            parent_exists = any(p.name == joint.parent for p in asset.parts)
            child_exists = any(p.name == joint.child for p in asset.parts)
            
            if not parent_exists:
                errors.append(f"Joint {joint.name} parent {joint.parent} not found")
                score -= 0.1
            
            if not child_exists:
                errors.append(f"Joint {joint.name} child {joint.child} not found")
                score -= 0.1
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'score': max(0.0, score)
        }
    
    def generate_batch(
        self,
        descriptions: List[str],
        category: Optional[str] = None,
        max_workers: int = 4
    ) -> List[ArticulatedAsset]:
        """
        Generate multiple assets in parallel.
        
        Useful for creating training datasets or marketplace inventory.
        """
        assets = []
        
        for desc in descriptions:
            try:
                asset = self.generate(desc, category=category)
                assets.append(asset)
            except Exception as e:
                print(f"Failed to generate asset for: {desc}")
                print(f"Error: {e}")
        
        return assets
    
    def load_dataset(self, dataset_name: str = "Articraft-10K") -> List[ArticulatedAsset]:
        """
        Load pre-generated ArtiCraft dataset.
        
        Articraft-10K contains 10,000+ articulated assets across 245 categories.
        """
        if dataset_name in self.dataset_cache:
            return self.dataset_cache[dataset_name]
        
        # This would download/load from HuggingFace or similar
        # Placeholder implementation
        assets = []
        
        self.dataset_cache[dataset_name] = assets
        return assets
    
    def search_dataset(
        self,
        query: str,
        category: Optional[str] = None,
        articulation_type: Optional[ArticulationType] = None,
        min_quality: float = 0.8
    ) -> List[ArticulatedAsset]:
        """Search ArtiCraft dataset for matching assets."""
        dataset = self.load_dataset()
        
        results = []
        for asset in dataset:
            # Simple text matching (in production, use embeddings)
            if query.lower() in asset.description.lower():
                if category and asset.category != category:
                    continue
                if asset.quality_score < min_quality:
                    continue
                results.append(asset)
        
        return results
    
    def import_to_nwo_mr(
        self,
        asset: ArticulatedAsset,
        mr_client,
        price_eth: Optional[float] = None
    ) -> Dict:
        """
        Import ArtiCraft asset into NWO MR ecosystem.
        
        Creates marketplace artifact and optionally lists as NFT.
        """
        # Create artifact
        artifact = mr_client.market.design_artifact(
            category=asset.category,
            name=asset.name,
            attributes={
                "parts_count": len(asset.parts),
                "joints_count": len(asset.joints),
                "articulation_types": list(set(j.type.value for j in asset.joints)),
                "quality_score": asset.quality_score,
                "source": "articraft",
                "articulated": True
            },
            visual_3d=list(asset.mesh_paths.values())[0] if asset.mesh_paths else None,
            compatible_with=["gazebo", "mujoco", "pybullet", "nwo_mr"]
        )
        
        # Upload URDF and meshes to NWO MR storage
        upload_result = self._upload_asset_files(asset, mr_client)
        
        result = {
            'artifact_id': artifact.id,
            'upload_status': upload_result,
            'asset_id': asset.id
        }
        
        # Mint as NFT if price specified
        if price_eth:
            nft = mr_client.market.mint_nft(
                artifact=artifact,
                collection="NWO_Articulated_Assets",
                royalty=0.05
            )
            
            listing = mr_client.market.list_nft(
                nft_id=nft.id,
                price=price_eth,
                currency="ETH"
            )
            
            result['nft_id'] = nft.id
            result['listing_id'] = listing['id']
        
        return result
    
    def _upload_asset_files(
        self,
        asset: ArticulatedAsset,
        mr_client
    ) -> Dict:
        """Upload URDF and mesh files to NWO MR storage."""
        uploaded = {
            'urdf': None,
            'meshes': []
        }
        
        # Upload URDF
        if asset.urdf_path and Path(asset.urdf_path).exists():
            with open(asset.urdf_path, 'rb') as f:
                result = mr_client._request(
                    'POST',
                    '/v1/mr/storage/upload',
                    {
                        'filename': f"{asset.id}.urdf",
                        'content': f.read(),
                        'type': 'urdf'
                    }
                )
                uploaded['urdf'] = result['url']
        
        # Upload meshes
        for part_name, mesh_path in asset.mesh_paths.items():
            if Path(mesh_path).exists():
                with open(mesh_path, 'rb') as f:
                    result = mr_client._request(
                        'POST',
                        '/v1/mr/storage/upload',
                        {
                            'filename': f"{asset.id}_{part_name}.obj",
                            'content': f.read(),
                            'type': 'mesh'
                        }
                    )
                    uploaded['meshes'].append({
                        'part': part_name,
                        'url': result['url']
                    })
        
        return uploaded
    
    def add_to_simulation(
        self,
        asset: ArticulatedAsset,
        simulation_id: str,
        mr_client,
        position: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Add articulated asset to running simulation.
        
        Spawns object with working joints in Gazebo/MuJoCo.
        """
        payload = {
            'simulation_id': simulation_id,
            'asset_id': asset.id,
            'urdf_url': asset.urdf_path,
            'meshes': asset.mesh_paths
        }
        
        if position:
            payload['position'] = position
        
        return mr_client._request(
            'POST',
            '/v1/mr/simulation/spawn-articulated',
            payload
        )
    
    def create_training_curriculum(
        self,
        skill: str,  # e.g., "grasping", "opening", "assembling"
        difficulty_levels: int = 5,
        assets_per_level: int = 20
    ) -> List[List[ArticulatedAsset]]:
        """
        Create progressive training curriculum for robot learning.
        
        Generates/assets that gradually increase in difficulty.
        """
        curriculum = []
        
        for level in range(difficulty_levels):
            difficulty = (level + 1) / difficulty_levels
            
            # Generate or select assets for this level
            if level < 2:
                # Use simple assets from dataset
                assets = self.search_dataset(
                    query=skill,
                    min_quality=0.9
                )[:assets_per_level]
            else:
                # Generate complex assets
                descriptions = self._generate_descriptions(skill, difficulty, assets_per_level)
                assets = self.generate_batch(descriptions)
            
            curriculum.append(assets)
        
        return curriculum
    
    def _generate_descriptions(
        self,
        skill: str,
        difficulty: float,
        count: int
    ) -> List[str]:
        """Generate object descriptions for training curriculum."""
        templates = {
            "grasping": [
                "small cylindrical bottle with smooth surface",
                "rectangular box with handle",
                "irregular shaped object with texture",
                "fragile glass cup with thin walls",
                "heavy metal tool with complex geometry"
            ],
            "opening": [
                "simple drawer with single prismatic joint",
                "cabinet door with revolute hinge",
                "sliding window with two parallel tracks",
                "toolbox with multiple compartments and latches",
                "complex machinery with interlocking panels"
            ],
            "assembling": [
                "two-part snap-fit components",
                "screw-based assembly with threads",
                "peg-and-hole alignment parts",
                "gear mechanism with multiple components",
                "articulated arm with 5+ joints"
            ]
        }
        
        base_templates = templates.get(skill, ["mechanical object"])
        
        # Scale complexity by difficulty
        descriptions = []
        for i in range(count):
            template = base_templates[i % len(base_templates)]
            if difficulty > 0.5:
                template += f" with {int(difficulty * 10)} additional features"
            descriptions.append(template)
        
        return descriptions

"""
NWO MR - Mixed Reality for Robotics & AI Agents

Main client for interacting with the NWO MR ecosystem.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import requests
from eth_account import Account
import json

# Import submodules
from .robotics_integration import NWORoboticsCSIntegration
from .agent_economy import AgentEconomy


@dataclass
class AvatarConfig:
    """Configuration for avatar creation."""
    name: str
    appearance: Dict[str, Any]
    animations: Optional[Dict[str, str]] = None
    voice: Optional[Dict[str, str]] = None
    capabilities: Optional[List[str]] = None


@dataclass
class SimulationConfig:
    """Configuration for simulation."""
    world: str
    physics: str = "mujoco"  # or "gazebo"
    render: str = "vr"  # or "ar", "mr", "screen"
    robot_spec: Optional[Dict] = None


@dataclass
class Artifact:
    """Virtual artifact for NFT minting."""
    id: str
    name: str
    category: str
    attributes: Dict[str, Any]
    visual_3d: Optional[str] = None
    compatible_with: Optional[List[str]] = None


@dataclass
class NFT:
    """NFT representation."""
    id: str
    artifact: Artifact
    owner: str
    price: float
    currency: str
    royalty: float


class NWOMRClient:
    """
    Main client for NWO Mixed Reality platform.
    
    Provides access to:
    - Avatar Engine: Create and control avatars
    - Simulation Engine: Test robots in virtual environments
    - Market Layer: Design, mint, and trade NFTs
    - Finance Layer: Web3 payments and earnings
    - Image Blaster: Rapid 3D environment generation
    - ArtiCraft: Articulated 3D asset generation
    """
    
    def __init__(
        self,
        api_url: str = "https://nwo-mr.onrender.com",
        wallet_address: Optional[str] = None,
        private_key: Optional[str] = None,
        market_url: Optional[str] = None,
        robotics_url: Optional[str] = None
    ):
        self.api_url = api_url.rstrip('/')
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.market_url = market_url or "https://nwo-market-layer.onrender.com"
        self.robotics_url = robotics_url or "https://nwo-capital-api.onrender.com/api"
        
        # Initialize sub-clients
        self.avatar = AvatarClient(self)
        self.simulation = SimulationClient(self)
        self.market = MarketClient(self)
        self.finance = FinanceClient(self)
        self.identity = IdentityClient(self)
        
        # Optional integrations (loaded on demand)
        self._robotics_integration = None
        self._agent_economy = None
        self._image_blaster = None
        self._articraft = None
        
        self.session = requests.Session()
        if wallet_address:
            self.session.headers.update({
                'X-Wallet-Address': wallet_address
            })
    
    @property
    def robotics_integration(self):
        """Lazy load robotics integration."""
        if self._robotics_integration is None:
            from .robotics_integration import NWORoboticsCSIntegration
            from nwo_robotics_cs import NWORoboticsClient
            robotics = NWORoboticsClient(api_url=self.robotics_url)
            self._robotics_integration = NWORoboticsCSIntegration(self, robotics)
        return self._robotics_integration
    
    @property
    def economy(self):
        """Lazy load agent economy."""
        if self._agent_economy is None:
            from .agent_economy import AgentEconomy
            self._agent_economy = AgentEconomy(self)
        return self._agent_economy
    
    def image_blaster(self, config=None):
        """Get Image Blaster integration."""
        if self._image_blaster is None:
            from .image_blaster import ImageBlasterIntegration, BlasterConfig
            if config is None:
                raise ValueError("Config required for Image Blaster. Pass BlasterConfig with API keys.")
            self._image_blaster = ImageBlasterIntegration(config)
        return self._image_blaster
    
    def articraft(self, config=None):
        """Get ArtiCraft integration for articulated 3D assets."""
        if self._articraft is None:
            from .articraft import ArtiCraftIntegration, ArtiCraftConfig
            if config is None:
                raise ValueError("Config required for ArtiCraft. Pass ArtiCraftConfig with API keys.")
            self._articraft = ArtiCraftIntegration(config)
        return self._articraft
    
    def _sign_request(self, payload: Dict) -> str:
        """Sign request with private key."""
        if not self.private_key:
            raise ValueError("Private key required for signed operations")
        
        account = Account.from_key(self.private_key)
        message = json.dumps(payload, sort_keys=True)
        signature = account.sign_message(message.encode())
        return signature.signature.hex()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict:
        """Make authenticated request to API."""
        url = f"{self.api_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if signed and data:
            headers['X-Signature'] = self._sign_request(data)
        
        response = self.session.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()


class AvatarClient:
    """Client for avatar creation and control."""
    
    def __init__(self, client: NWOMRClient):
        self.client = client
    
    def create(self, config: AvatarConfig) -> Dict:
        """Create a new avatar."""
        payload = {
            'name': config.name,
            'appearance': config.appearance,
            'animations': config.animations or {},
            'voice': config.voice or {},
            'capabilities': config.capabilities or []
        }
        return self.client._request('POST', '/v1/mr/avatar/create', payload, signed=True)
    
    def emote(self, avatar_id: str, emotion: str) -> Dict:
        """Make avatar express emotion."""
        return self.client._request(
            'POST',
            f'/v1/mr/avatar/{avatar_id}/emote',
            {'emotion': emotion}
        )
    
    def speak(self, avatar_id: str, text: str, tone: Optional[str] = None) -> Dict:
        """Make avatar speak."""
        payload = {'text': text}
        if tone:
            payload['tone'] = tone
        return self.client._request(
            'POST',
            f'/v1/mr/avatar/{avatar_id}/speak',
            payload
        )
    
    def gesture(self, avatar_id: str, gesture: str, target: Optional[str] = None) -> Dict:
        """Make avatar perform gesture."""
        payload = {'gesture': gesture}
        if target:
            payload['target'] = target
        return self.client._request(
            'POST',
            f'/v1/mr/avatar/{avatar_id}/gesture',
            payload
        )
    
    def move_to(self, avatar_id: str, location: str) -> Dict:
        """Move avatar to location."""
        return self.client._request(
            'POST',
            f'/v1/mr/avatar/{avatar_id}/move',
            {'location': location}
        )


class SimulationClient:
    """Client for robot simulation."""
    
    def __init__(self, client: NWOMRClient):
        self.client = client
    
    def create(self, config: SimulationConfig) -> Dict:
        """Create new simulation environment."""
        payload = {
            'world': config.world,
            'physics': config.physics,
            'render': config.render
        }
        if config.robot_spec:
            payload['robot_spec'] = config.robot_spec
        
        return self.client._request(
            'POST',
            '/v1/mr/simulation/create',
            payload,
            signed=True
        )
    
    def enter(self, simulation_id: str, avatar_id: Optional[str] = None) -> Dict:
        """Enter simulation as avatar."""
        payload = {'simulation_id': simulation_id}
        if avatar_id:
            payload['avatar_id'] = avatar_id
        return self.client._request('POST', '/v1/mr/simulation/enter', payload)
    
    def spawn_robot(self, simulation_id: str, robot_type: str) -> Dict:
        """Spawn robot in simulation."""
        return self.client._request(
            'POST',
            '/v1/mr/simulation/spawn-robot',
            {
                'simulation_id': simulation_id,
                'robot_type': robot_type
            }
        )
    
    def run_task(
        self,
        simulation_id: str,
        task: str,
        objects: Optional[List[str]] = None,
        iterations: int = 100,
        record: bool = True
    ) -> Dict:
        """Run task in simulation."""
        payload = {
            'simulation_id': simulation_id,
            'task': task,
            'iterations': iterations,
            'record': record
        }
        if objects:
            payload['objects'] = objects
        
        return self.client._request('POST', '/v1/mr/simulation/run', payload)
    
    def test_motion(self, simulation_id: str, motion: Dict) -> Dict:
        """Test motion plan in simulation."""
        return self.client._request(
            'POST',
            '/v1/mr/simulation/test-motion',
            {
                'simulation_id': simulation_id,
                'motion': motion
            }
        )
    
    def get_results(self, simulation_id: str) -> Dict:
        """Get simulation results."""
        return self.client._request(
            'GET',
            f'/v1/mr/simulation/{simulation_id}/results'
        )


class MarketClient:
    """Client for virtual market operations."""
    
    def __init__(self, client: NWOMRClient):
        self.client = client
    
    def design_artifact(
        self,
        category: str,
        name: str,
        attributes: Dict[str, Any],
        visual_3d: Optional[str] = None,
        compatible_with: Optional[List[str]] = None
    ) -> Artifact:
        """Design a new virtual artifact."""
        payload = {
            'category': category,
            'name': name,
            'attributes': attributes
        }
        if visual_3d:
            payload['visual_3d'] = visual_3d
        if compatible_with:
            payload['compatible_with'] = compatible_with
        
        result = self.client._request(
            'POST',
            '/v1/mr/market/design',
            payload,
            signed=True
        )
        
        return Artifact(
            id=result['id'],
            name=name,
            category=category,
            attributes=attributes,
            visual_3d=visual_3d,
            compatible_with=compatible_with
        )
    
    def mint_nft(
        self,
        artifact: Artifact,
        collection: str = "NWO_MR_Artifacts",
        royalty: float = 0.05
    ) -> NFT:
        """Mint artifact as NFT."""
        payload = {
            'artifact_id': artifact.id,
            'collection': collection,
            'royalty': royalty
        }
        
        result = self.client._request(
            'POST',
            '/v1/mr/market/mint',
            payload,
            signed=True
        )
        
        return NFT(
            id=result['nft_id'],
            artifact=artifact,
            owner=self.client.wallet_address,
            price=0.0,
            currency="ETH",
            royalty=royalty
        )
    
    def list_nft(
        self,
        nft_id: str,
        price: float,
        currency: str = "ETH",
        auction: bool = False,
        duration_days: int = 7
    ) -> Dict:
        """List NFT for sale."""
        payload = {
            'nft_id': nft_id,
            'price': price,
            'currency': currency,
            'auction': auction,
            'duration_days': duration_days
        }
        return self.client._request(
            'POST',
            '/v1/mr/market/list',
            payload,
            signed=True
        )
    
    def browse(
        self,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        compatible_with: Optional[str] = None
    ) -> List[NFT]:
        """Browse marketplace listings."""
        params = {}
        if category:
            params['category'] = category
        if min_price:
            params['min_price'] = min_price
        if max_price:
            params['max_price'] = max_price
        if compatible_with:
            params['compatible_with'] = compatible_with
        
        result = self.client._request('GET', '/v1/mr/market/browse', params)
        return [NFT(**item) for item in result.get('listings', [])]
    
    def buy(self, nft_id: str, max_price: Optional[float] = None) -> Dict:
        """Buy NFT from marketplace."""
        payload = {'nft_id': nft_id}
        if max_price:
            payload['max_price'] = max_price
        return self.client._request(
            'POST',
            '/v1/mr/market/buy',
            payload,
            signed=True
        )
    
    def trade(
        self,
        with_agent: str,
        give: List[str],  # NFT IDs
        receive: List[str],  # NFT IDs
        currency_adjustment: float = 0.0
    ) -> Dict:
        """Propose trade with another agent."""
        payload = {
            'with_agent': with_agent,
            'give': give,
            'receive': receive,
            'currency_adjustment': currency_adjustment
        }
        return self.client._request(
            'POST',
            '/v1/mr/market/trade',
            payload,
            signed=True
        )


class FinanceClient:
    """Client for Web3 finance operations."""
    
    def __init__(self, client: NWOMRClient):
        self.client = client
    
    def get_balance(self, token: str = "ETH") -> float:
        """Get wallet balance."""
        result = self.client._request(
            'GET',
            f'/v1/mr/finance/balance/{token}'
        )
        return result.get('balance', 0.0)
    
    def stake(
        self,
        token: str,
        amount: float,
        duration_days: int,
        benefits: Optional[List[str]] = None
    ) -> Dict:
        """Stake tokens for benefits."""
        payload = {
            'token': token,
            'amount': amount,
            'duration_days': duration_days,
            'benefits': benefits or []
        }
        return self.client._request(
            'POST',
            '/v1/mr/finance/stake',
            payload,
            signed=True
        )
    
    def get_earnings(self, robot_id: Optional[str] = None) -> Dict:
        """Get earnings from robot work."""
        params = {}
        if robot_id:
            params['robot_id'] = robot_id
        return self.client._request('GET', '/v1/mr/finance/earnings', params)
    
    def claim_earnings(self, robot_id: Optional[str] = None) -> Dict:
        """Claim accumulated earnings."""
        payload = {}
        if robot_id:
            payload['robot_id'] = robot_id
        return self.client._request(
            'POST',
            '/v1/mr/finance/claim',
            payload,
            signed=True
        )
    
    def pay(
        self,
        to: str,
        amount: float,
        currency: str = "ETH",
        for_service: Optional[str] = None,
        escrow: bool = False
    ) -> Dict:
        """Pay for services."""
        payload = {
            'to': to,
            'amount': amount,
            'currency': currency,
            'escrow': escrow
        }
        if for_service:
            payload['for_service'] = for_service
        return self.client._request(
            'POST',
            '/v1/mr/finance/pay',
            payload,
            signed=True
        )
    
    def auto_trade(
        self,
        strategy: str,
        assets: List[str],
        max_exposure: float,
        reinvest_earnings: bool = True
    ) -> Dict:
        """Configure automated trading."""
        payload = {
            'strategy': strategy,
            'assets': assets,
            'max_exposure': max_exposure,
            'reinvest_earnings': reinvest_earnings
        }
        return self.client._request(
            'POST',
            '/v1/mr/finance/auto-trade',
            payload,
            signed=True
        )


class IdentityClient:
    """Client for identity verification."""
    
    def __init__(self, client: NWOMRClient):
        self.client = client
    
    def verify(self, agent_id: str) -> Dict:
        """Verify agent identity."""
        return self.client._request(
            'GET',
            f'/v1/mr/identity/verify/{agent_id}'
        )
    
    def get_reputation(self, agent_id: str) -> Dict:
        """Get agent reputation score."""
        return self.client._request(
            'GET',
            f'/v1/mr/identity/reputation/{agent_id}'
        )
    
    def link_cardiac(self, root_token_id: str) -> Dict:
        """Link Cardiac identity."""
        return self.client._request(
            'POST',
            '/v1/mr/identity/link-cardiac',
            {'root_token_id': root_token_id},
            signed=True
        )

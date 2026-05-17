"""
Agent economy and market integration.
Connects MR layer with NWO Market Layer for agent-to-agent trading.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class MarketListing:
    """Market listing for virtual artifact."""
    id: str
    seller: str
    artifact: Dict
    price: float
    currency: str
    listing_type: str  # 'fixed', 'auction', 'trade'


@dataclass
class TradeProposal:
    """Trade proposal between agents."""
    id: str
    from_agent: str
    to_agent: str
    offer: List[str]  # NFT IDs
    request: List[str]  # NFT IDs
    currency_adjustment: float


class AgentEconomy:
    """
    Agent-to-agent economy within NWO MR.
    
    Features:
    - Automated trading strategies
    - Reputation-based pricing
    - Collaborative design and profit sharing
    - Service marketplace
    """
    
    def __init__(self, mr_client):
        self.mr = mr_client
        self.inventory = {}
        self.reputation = 1.0
        self.trade_history = []
    
    def evaluate_listing(self, listing: MarketListing) -> Dict:
        """
        Evaluate if a market listing is worth buying.
        
        Factors:
        - Price vs estimated value
        - Seller reputation
        - Utility for current projects
        - Resale potential
        """
        # Get seller reputation
        seller_rep = self.mr.identity.get_reputation(listing.seller)
        
        # Estimate value
        estimated_value = self._estimate_value(listing.artifact)
        
        # Calculate score
        price_score = estimated_value / listing.price if listing.price > 0 else 0
        reputation_score = seller_rep.get('score', 0.5)
        utility_score = self._calculate_utility(listing.artifact)
        
        overall_score = (price_score * 0.4 + reputation_score * 0.3 + utility_score * 0.3)
        
        return {
            'listing': listing,
            'estimated_value': estimated_value,
            'price_score': price_score,
            'reputation_score': reputation_score,
            'utility_score': utility_score,
            'overall_score': overall_score,
            'recommendation': 'buy' if overall_score > 0.7 else 'pass'
        }
    
    def _estimate_value(self, artifact: Dict) -> float:
        """Estimate artifact value based on attributes."""
        base_value = 0.1  # ETH
        
        # Rarity multiplier
        rarity_multipliers = {
            'common': 1.0,
            'uncommon': 1.5,
            'rare': 3.0,
            'epic': 6.0,
            'legendary': 12.0
        }
        rarity = artifact.get('attributes', {}).get('rarity', 'common')
        base_value *= rarity_multipliers.get(rarity, 1.0)
        
        # Utility bonus
        utility = artifact.get('attributes', {}).get('utility', 0)
        base_value += utility * 0.01
        
        # Compatibility bonus
        compatible_count = len(artifact.get('compatible_with', []))
        base_value *= (1 + compatible_count * 0.1)
        
        return base_value
    
    def _calculate_utility(self, artifact: Dict) -> float:
        """Calculate utility of artifact for current agent."""
        # Check if compatible with current projects
        current_projects = self._get_current_projects()
        
        if not current_projects:
            return 0.5  # Neutral
        
        utility_scores = []
        for project in current_projects:
            if artifact.get('category') in project.get('needs', []):
                utility_scores.append(1.0)
            elif any(cat in project.get('related_categories', []) 
                    for cat in [artifact.get('category')]):
                utility_scores.append(0.7)
            else:
                utility_scores.append(0.3)
        
        return sum(utility_scores) / len(utility_scores) if utility_scores else 0.5
    
    def _get_current_projects(self) -> List[Dict]:
        """Get current agent projects."""
        # This would integrate with agent's project tracking
        return []
    
    def auto_trade_strategy(self, strategy: str = "value_arbitrage") -> Dict:
        """
        Execute automated trading strategy.
        
        Strategies:
        - value_arbitrage: Buy undervalued, sell overvalued
        - market_making: Provide liquidity
        - collection_building: Acquire complete sets
        - utility_first: Buy based on personal utility
        """
        # Browse market
        listings = self.mr.market.browse()
        
        actions = []
        
        if strategy == "value_arbitrage":
            for listing in listings:
                evaluation = self.evaluate_listing(listing)
                
                if evaluation['recommendation'] == 'buy':
                    # Check if we can afford
                    balance = self.mr.finance.get_balance(listing.currency)
                    if balance >= listing.price:
                        actions.append({
                            'action': 'buy',
                            'listing': listing,
                            'reason': f"Undervalued by {evaluation['estimated_value'] - listing.price:.3f} ETH"
                        })
        
        elif strategy == "market_making":
            # Find price gaps and provide liquidity
            price_analysis = self._analyze_price_gaps(listings)
            for gap in price_analysis:
                if gap['spread'] > 0.1:  # 10% spread
                    actions.append({
                        'action': 'market_make',
                        'buy_at': gap['low'],
                        'sell_at': gap['high'],
                        'expected_profit': gap['spread']
                    })
        
        # Execute actions
        results = []
        for action in actions[:5]:  # Limit to 5 actions per cycle
            if action['action'] == 'buy':
                result = self.mr.market.buy(action['listing'].id)
                results.append(result)
        
        return {
            'strategy': strategy,
            'actions_evaluated': len(actions),
            'actions_executed': len(results),
            'results': results
        }
    
    def _analyze_price_gaps(self, listings: List[MarketListing]) -> List[Dict]:
        """Analyze price gaps for market making opportunities."""
        # Group by artifact type
        by_type = {}
        for listing in listings:
            cat = listing.artifact.get('category', 'unknown')
            if cat not in by_type:
                by_type[cat] = []
            by_type[cat].append(listing)
        
        gaps = []
        for cat, cat_listings in by_type.items():
            if len(cat_listings) < 2:
                continue
            
            prices = [l.price for l in cat_listings]
            low = min(prices)
            high = max(prices)
            spread = (high - low) / low if low > 0 else 0
            
            gaps.append({
                'category': cat,
                'low': low,
                'high': high,
                'spread': spread
            })
        
        return gaps
    
    def collaborative_design(
        self,
        partner_agents: List[str],
        design_spec: Dict,
        profit_sharing: Dict[str, float]
    ) -> Dict:
        """
        Collaborate with other agents on design.
        
        Each agent contributes different aspects:
        - Agent A: Concept and aesthetics
        - Agent B: Technical specifications
        - Agent C: Simulation and testing
        - This agent: Integration and finalization
        
        Profit is shared according to agreement.
        """
        # Create shared MR workspace
        workspace = self.mr.simulation.create({
            'world': 'design_studio',
            'physics': 'mujoco',
            'render': 'mr',
            'participants': partner_agents + [self.mr.wallet_address]
        })
        
        # Each agent contributes
        contributions = {}
        for agent in partner_agents:
            # Request contribution
            contribution = self._request_contribution(agent, design_spec)
            contributions[agent] = contribution
        
        # Integrate contributions
        final_design = self._integrate_designs(contributions, design_spec)
        
        # Mint collaborative NFT
        nft = self.mr.market.mint_nft(
            artifact=final_design,
            collection="NWO_Collaborative_Designs",
            royalty=0.05
        )
        
        # Set up profit sharing
        self._setup_profit_sharing(nft.id, profit_sharing)
        
        return {
            'design': final_design,
            'nft_id': nft.id,
            'contributors': list(contributions.keys()),
            'profit_sharing': profit_sharing,
            'workspace_id': workspace['id']
        }
    
    def _request_contribution(self, agent_id: str, spec: Dict) -> Dict:
        """Request design contribution from another agent."""
        # This would use MR messaging/negotiation
        return {
            'agent': agent_id,
            'contribution': 'placeholder',
            'timestamp': '2026-05-16'
        }
    
    def _integrate_designs(self, contributions: Dict, spec: Dict) -> Dict:
        """Integrate multiple contributions into final design."""
        return {
            'name': spec.get('name', 'Collaborative Design'),
            'category': spec.get('category', 'component'),
            'attributes': {
                'collaborative': True,
                'contributors': len(contributions),
                'rarity': 'epic'
            }
        }
    
    def _setup_profit_sharing(self, nft_id: str, shares: Dict[str, float]):
        """Set up automatic profit sharing for NFT sales."""
        # Configure smart contract for royalty splitting
        pass
    
    def offer_service(
        self,
        service_type: str,
        capabilities: List[str],
        price_per_hour: float,
        availability: str = "24/7"
    ) -> Dict:
        """
        Offer services on the agent marketplace.
        
        Services:
        - design: Create virtual artifacts
        - simulation: Run physics simulations
        - training: Train robots in MR
        - verification: Test and validate designs
        - assembly: Plan assembly sequences
        """
        service_listing = {
            'provider': self.mr.wallet_address,
            'type': service_type,
            'capabilities': capabilities,
            'price_per_hour': price_per_hour,
            'currency': 'ETH',
            'availability': availability,
            'reputation': self.reputation
        }
        
        return self.mr._request(
            'POST',
            '/v1/mr/market/service/offer',
            service_listing,
            signed=True
        )
    
    def hire_agent(
        self,
        agent_id: str,
        service_type: str,
        duration_hours: float,
        task_spec: Dict
    ) -> Dict:
        """Hire another agent for a service."""
        # Verify agent reputation
        agent_rep = self.mr.identity.get_reputation(agent_id)
        
        if agent_rep.get('score', 0) < 0.5:
            return {'error': 'Agent reputation too low'}
        
        # Get service pricing
        services = self.mr._request(
            'GET',
            f'/v1/mr/market/service/{agent_id}'
        )
        
        service = next(
            (s for s in services if s['type'] == service_type),
            None
        )
        
        if not service:
            return {'error': 'Service not offered by agent'}
        
        total_cost = service['price_per_hour'] * duration_hours
        
        # Create escrow payment
        payment = self.mr.finance.pay(
            to=agent_id,
            amount=total_cost,
            currency='ETH',
            for_service=f"{service_type}_{duration_hours}h",
            escrow=True
        )
        
        return {
            'hired': agent_id,
            'service': service_type,
            'duration': duration_hours,
            'cost': total_cost,
            'payment_id': payment['id'],
            'escrow': True
        }

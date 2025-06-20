"""Main entry point for Sub-Agent execution"""

import asyncio
import os
import signal
from typing import Optional
from ..config.settings import RaidConfig
from ..config.sub_agent_config import SubAgentConfigurator
from .agent import SubAgent


class SubAgentRunner:
    """Runner for Sub-Agent execution"""
    
    def __init__(self):
        self.sub_agent: Optional[SubAgent] = None
        self.running = False
    
    async def run(self, profile_name: Optional[str] = None) -> None:
        """Run the Sub-Agent"""
        # Get profile name from environment or parameter
        if not profile_name:
            profile_name = os.getenv("RAID_SUB_AGENT_PROFILE")
        
        if not profile_name:
            raise ValueError("Sub-Agent profile name must be provided via RAID_SUB_AGENT_PROFILE env var or parameter")
        
        # Load configuration
        config = RaidConfig.from_env()
        configurator = SubAgentConfigurator()
        
        try:
            profile = configurator.load_profile(profile_name)
        except FileNotFoundError:
            raise ValueError(f"Sub-Agent profile '{profile_name}' not found")
        
        # Create and start Sub-Agent
        self.sub_agent = SubAgent(profile, config.message_queue, config)
        
        # Set up signal handlers for graceful shutdown
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
        
        self.running = True
        
        try:
            await self.sub_agent.start()
        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        finally:
            await self._shutdown()
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False
    
    async def _shutdown(self) -> None:
        """Graceful shutdown"""
        if self.sub_agent:
            await self.sub_agent.stop()


async def main(profile_name: Optional[str] = None) -> None:
    """Main entry point"""
    runner = SubAgentRunner()
    await runner.run(profile_name)


if __name__ == "__main__":
    import sys
    
    # Get profile name from command line args if provided
    profile_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        asyncio.run(main(profile_name))
    except Exception as e:
        print(f"Failed to start Sub-Agent: {e}")
        sys.exit(1)
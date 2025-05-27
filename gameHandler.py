from abc import ABC, abstractmethod
from customdataclasses import GameConfig
from typing import List, Dict


class GameHandler(ABC):
    """Abstract base class for game-specific handlers"""

    @property
    @abstractmethod
    def game_type(self) -> str:
        """Return the game type identifier"""
        pass

    @property
    @abstractmethod
    def default_ports(self) -> List[int]:
        """Return default ports for this game"""
        pass

    @abstractmethod
    def parse_config(self, cfg_json: str) -> GameConfig:
        """Parse game-specific configuration from JSON"""
        pass

    @abstractmethod
    def generate_env_vars(self, config, subscription_id: str) -> Dict[str, str]:
        """Generate environment variables for docker compose"""
        pass

    def validate_config(self, config: GameConfig) -> bool:
        """Validate game configuration (override if needed)"""
        return bool(config.name and config.port)

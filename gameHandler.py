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
    def get_env_file_format(self, subscription_id) -> str:
        """Returns env file name of game"""
        pass

    @abstractmethod
    def parse_config(self, cfg_json: str) -> GameConfig:
        """Parse game-specific configuration from JSON"""
        pass

    @abstractmethod
    def generate_env_vars(self, config, subscription_id: str) -> Dict[str, str]:
        """Generate environment variables for docker compose"""
        pass

    @abstractmethod
    def fill_compose_file(self, defaults: Dict, src_template_path: str, target_compose_file: str):
        """Fills compose file with defaults and any custom variables by extending defaults"""
        pass

    @abstractmethod
    def update_config_file(
        self, env_vars: Dict, subscription_path: str, subscription_id: str
    ):
        """Fills compose file with defaults and any custom variables"""
        pass

    @abstractmethod
    def create_default_subscription_config_file(
        self,
        subscription_path: str,
        subscription_id: str,
        docker_game_template_path: str,
    ):
        """Copies the env/config file from  docker game template path to subscription path"""
        pass

    def validate_config(self, config: GameConfig) -> bool:
        """Validate game configuration (override if needed)"""
        return bool(config.name and config.port)

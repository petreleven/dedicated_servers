from dataclasses import dataclass
from typing import Dict, List, Union, Optional


@dataclass
class ServerResult:
    """Standardized result structure"""

    action: str
    subscription_id: str
    status: str
    error: Optional[str] = None
    container_id: Optional[str] = None
    container_ip: Optional[str] = None
    metrics: Optional[Dict] = None
    ports: Optional[List[int]] = None

    def to_dict(self) -> Dict[str, Union[bool, str, int, dict]]:
        result = {
            "action": self.action,
            "subscription_id": self.subscription_id,
            "status": self.status,
        }
        if self.error:
            result["error"] = self.error
        if self.container_id:
            result["container_id"] = self.container_id
        if self.container_ip:
            result["container_ip"] = self.container_ip
        if self.metrics:
            result["metrics"] = self.metrics
        if self.ports:
            result["ports"] = self.ports
        return result


@dataclass
class GameConfig:
    """Base configuration for game servers"""

    name: str
    port: int
    password: str
    world: str = "defaultworld"
    public: bool = True
    max_players: int = 10


@dataclass
class ValheimConfig(GameConfig):
    """Valheim-specific configuration"""

    crossplay: bool = False
    save_interval: int = 1800
    backups: int = 4
    backup_short: int = 7200
    backup_long: int = 43200
    preset: str = "Normal"
    # Modifiers
    modifier_combat: str = "normal"
    modifier_death: str = "casual"
    modifier_resources: str = "more"
    modifier_raids: str = "none"
    modifier_portals: str = "casual"
    # Individual setkey properties
    no_map: bool = False
    player_events: bool = False
    passive_mobs: bool = False
    no_build_cost: bool = False

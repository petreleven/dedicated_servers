import pathlib
import shutil
import tempfile
from customdataclasses import ValheimConfig
from gameHandler import GameHandler
import base64
import json
from portchecker import get_available_ports
from typing import List, Dict
from jinja2 import Environment, select_autoescape, FileSystemLoader
import os

from setup_server import GameServerManager


class ValheimHandler(GameHandler):
    """Handler for Valheim game servers"""

    def __init__(self) -> None:
        super().__init__()

    @property
    def game_type(self) -> str:
        return "valheim"

    @property
    def default_ports(self) -> List[int]:
        ports = get_available_ports(n=2)
        return ports

    def get_env_file_format(self, subscription_id) -> str:
        return f".{self.game_type}_{subscription_id}_env"

    def parse_config(self, cfg_json: str) -> ValheimConfig:
        """Parse Valheim-specific configuration"""
        try:
            decoded_bytes = base64.b64decode(cfg_json)
            cfg = json.loads(decoded_bytes)
        except (ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Invalid config payload: {e}")

        # Extract modifiers safely
        mods = cfg.get("modifiers", {})

        return ValheimConfig(
            name=cfg.get("name", "myvalheimserver"),
            port=cfg.get("port", 2456),
            password=cfg.get("password", "somethingsecret"),
            world=cfg.get("world", "myworld"),
            public=cfg.get("public", True),
            max_players=cfg.get("maxplayers", 10),
            crossplay=cfg.get("crossplay", False),
            save_interval=cfg.get("saveinterval", 1800),
            backups=cfg.get("backups", 4),
            backup_short=cfg.get("backupshort", 7200),
            backup_long=cfg.get("backuplong", 43200),
            preset=cfg.get("preset", "Normal"),
            modifier_combat=mods.get("Combat", "normal"),
            modifier_death=mods.get("DeathPenalty", "casual"),
            modifier_resources=mods.get("Resources", "more"),
            modifier_raids=mods.get("Raids", "none"),
            modifier_portals=mods.get("Portals", "casual"),
            no_map=cfg.get("nomap", False),
            player_events=cfg.get("playerevents", False),
            passive_mobs=cfg.get("passivemobs", False),
            no_build_cost=cfg.get("nobuildcost", False),
        )

    def generate_env_vars(
        self, config: ValheimConfig, subscription_id: str
    ) -> Dict[str, str]:
        """Generate Valheim-specific environment variables"""
        return {
            "PORT": str(config.port),
            "SERVER_NAME": config.name,
            "SERVER_PASSWORD": config.password,
            "CROSSPLAY_ENABLED": str(config.crossplay).lower(),
            "WORLD_NAME": config.world,
            "PUBLIC": str(int(config.public)),
            "SAVE_DIR": "/valheim/saves",
            "SAVE_INTERVAL": str(config.save_interval),
            "KEEP_BACKUPS": str(config.backups),
            "BACKUPS_SHORT": str(config.backup_short),
            "BACKUPS_LONG": str(config.backup_long),
            "SERVER_PRESET": config.preset,
            "MODIFIER_COMBAT": config.modifier_combat,
            "MODIFIER_DEATH": config.modifier_death,
            "MODIFIER_RESOURCES": config.modifier_resources,
            "MODIFIER_RAIDS": config.modifier_raids,
            "MODIFIER_PORTALS": config.modifier_portals,
            # Individual setkey properties
            "NO_MAP": str(config.no_map).lower(),
            "PLAYER_EVENTS": str(config.player_events).lower(),
            "PASSIVE_MOBS": str(config.passive_mobs).lower(),
            "NO_BUILD_COST": str(config.no_build_cost).lower(),
        }

    def fill_compose_file(self, defaults: Dict, src_template_path:str,target_compose_file:str):
        src_path = pathlib.Path(src_template_path)
        j_env = Environment(
            loader=FileSystemLoader(str(src_path.absolute().parent)),
            autoescape=select_autoescape(),
        )
        j_template = j_env.get_template(src_path.name)
        s = j_template.render(defaults)
        os.makedirs("./tmp", exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, mode="w", dir="./temp") as f:
            f.write(s)

        shutil.move(f.name, target_compose_file)
        if not pathlib.Path(target_compose_file).exists():
            raise FileNotFoundError(compose_file)

    def update_config_file(
        self, env_vars: Dict, subscription_path: str, subscription_id: str
    ):
        # Write environment file
        env_file = os.path.join(
            subscription_path,
            self.get_env_file_format(subscription_id),
        )
        os.makedirs("./tmp", exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, mode="w", dir="./temp") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        shutil.move(src=f.name, dst=env_file)

    def create_default_subscription_config_file(
        self,
        subscription_path: str,
        subscription_id: str,
        docker_game_template_path: str,
    ):
        src_env_template_file = os.path.join(
            docker_game_template_path, f".{self.game_type}_env"
        )
        if not os.path.exists(src_env_template_file):
            raise Exception(
                f"Environment template not found for game: {self.game_type} at {src_env_template_file}"
            )

        target_env_subscription_file = os.path.join(
            subscription_path, self.get_env_file_format(subscription_id)
        )
        # Copy environment template
        return_code, _, stderr = GameServerManager.run_command(
            f"cp -r {src_env_template_file} {target_env_subscription_file}"
        )
        if return_code != 0:
            raise Exception(f"Unable to copy env template file: {stderr}")

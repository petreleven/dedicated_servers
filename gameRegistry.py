from gameHandler import GameHandler
from ValheimHandler import ValheimHandler
import logging
from typing import Dict, List


class GameRegistry:
    """Registry for managing game handlers"""

    def __init__(self):
        self._handlers: Dict[str, GameHandler] = {}
        self.logger = logging.getLogger("game-server-setup")
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in game handlers"""
        self.register(ValheimHandler())

    def register(self, handler: GameHandler):
        """Register a new game handler"""
        self._handlers[handler.game_type] = handler
        self.logger.info(f"Registered handler for {handler.game_type}")

    def get_handler(self, game_type: str) -> GameHandler:
        """Get handler for specific game type"""
        if game_type not in self._handlers:
            raise ValueError(f"No handler registered for game type: {game_type}")
        return self._handlers[game_type]

    def get_supported_games(self) -> List[str]:
        """Get list of supported game types"""
        return list(self._handlers.keys())

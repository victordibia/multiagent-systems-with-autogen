from abc import ABC, abstractmethod
from typing import List, Optional

from ...datamodel   import (
    GameState, 
    Player, 
    Game,
    Move
)

class GameEngine(ABC):
    """Abstract base class for game engines"""
    
    @abstractmethod
    def get_state(self) -> GameState:
        """Returns current game state"""
        pass
    
    @abstractmethod
    def is_valid_move(self, move: str) -> bool:
        """Checks if a move is valid in current state"""
        pass
    
    @abstractmethod
    def make_move(self, move: Move) -> bool:
        """Attempts to make a move. Returns True if successful"""
        pass
    
    @abstractmethod
    def is_game_over(self) -> bool:
        """Checks if the game has ended"""
        pass
    
    @abstractmethod
    def get_winner(self) -> Optional[Player]:
        """Returns winner if game is over, None otherwise"""
        pass
    
    @abstractmethod
    def get_valid_moves(self) -> List[str]:
        """Returns list of valid moves in current state"""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Resets the game to initial state"""
        pass

    @abstractmethod
    def create_game(self, player_white: str, player_black: str) -> Game:
        """Creates a new game instance"""
        pass
 
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any, Generic, TypeVar
import asyncio
from datetime import datetime
import logging
from ...datamodel import (
    Game,
    GameState,
    GameTurn,
    Player,
    GameResult,
    AIMove,
    GameType,
    ChessMetadata,
    TicTacToeMetadata
)
from ..engines import GameEngine, ChessGameEngine, TicTacToeEngine
from ...agents import AIAgent
from .base import BaseGameMatch 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables for generic typing
TEngine = TypeVar('TEngine', bound=GameEngine)
TMetadata = TypeVar('TMetadata')
 
 
class TicTacToeMatch(BaseGameMatch[TicTacToeEngine, TicTacToeMetadata]):
    """Tic-tac-toe specific match implementation"""
    
    def get_current_agent(self, state: GameState) -> AIAgent:
        return self.player_one if state.current_player == Player.PLAYER_ONE else self.player_two
    
    def create_forfeit_move(self, state: GameState, agent: AIAgent) -> AIMove:
        return AIMove(
            player=state.current_player,
            move_notation="forfeit",
            model_name=agent.name,
            reasoning="Failed to generate valid tic-tac-toe move",
            tokens_used=0,
            retry_count=agent.config.max_retries,
            raw_response="",
            prompt_used="",
            is_valid=False,
            game_type=GameType.TIC_TAC_TOE,
            timestamp=datetime.utcnow()
        )
    
    def validate_game_state(self, state: GameState) -> bool:
        # Tic-tac-toe specific validation
        metadata = TicTacToeMetadata(**state.metadata)
        board = state.state_repr.split(',')
        return len(board) == 9  # Simple validation for 3x3 board
    
    def get_game_specific_summary(self) -> Dict[str, Any]:
        if not self.game:
            return {}
            
        final_state = self.game.final_state
        
        return {
            "final_board": final_state.state_repr,
            "winning_line": self._find_winning_line(final_state.state_repr)
        }
    
    def _find_winning_line(self, board_str: str) -> Optional[List[int]]:
        # Tic-tac-toe specific helper method
        board = board_str.split(',')
        # Check winning combinations...
        return None
 
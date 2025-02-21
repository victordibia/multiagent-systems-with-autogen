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
 
class ChessMatch(BaseGameMatch[ChessGameEngine, ChessMetadata]):
    """Chess-specific match implementation"""
    
    def get_current_agent(self, state: GameState) -> AIAgent:
        return self.player_one if state.current_player == Player.PLAYER_ONE else self.player_two
    
    def create_forfeit_move(self, state: GameState, agent: AIAgent) -> AIMove:
        return AIMove(
            player=state.current_player,
            move_notation="forfeit",
            model_name=agent.name,
            reasoning="Failed to generate valid chess move",
            tokens_used=0,
            retry_count=agent.config.max_retries,
            raw_response="",
            prompt_used="",
            is_valid=False,
            game_type=GameType.CHESS,
            timestamp=datetime.utcnow()
        )
    
    def validate_game_state(self, state: GameState) -> bool:
        # Chess-specific validation
        metadata = ChessMetadata(**state.metadata)
        return not (metadata.checkmate or metadata.stalemate)
    
    def get_game_specific_summary(self) -> Dict[str, Any]:
        if not self.game:
            return {}
            
        final_state = self.game.final_state
        metadata = ChessMetadata(**final_state.metadata)
        
        return {
            "checkmate": metadata.checkmate,
            "stalemate": metadata.stalemate,
            "final_position": final_state.state_repr,
            "total_captures": len([m for m in metadata.move_history if 'x' in m])
        }

 
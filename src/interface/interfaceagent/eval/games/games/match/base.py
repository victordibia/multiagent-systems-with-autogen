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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables for generic typing
TEngine = TypeVar('TEngine', bound=GameEngine)
TMetadata = TypeVar('TMetadata')

class BaseGameMatch(ABC, Generic[TEngine, TMetadata]):
    """Base class for game matches"""
    
    def __init__(
        self,
        player_one: AIAgent,
        player_two: AIAgent,
        game_engine: TEngine,
        max_moves: int = 100,
        move_timeout: float = 30.0
    ):
        self.player_one = player_one
        self.player_two = player_two
        self.game_engine = game_engine
        self.max_moves = max_moves
        self.move_timeout = move_timeout
        self.game: Optional[Game] = None
        
    @abstractmethod
    def get_current_agent(self, state: GameState) -> AIAgent:
        """Get the agent for the current turn"""
        pass
    
    @abstractmethod
    def create_forfeit_move(self, state: GameState, agent: AIAgent) -> AIMove:
        """Create a forfeit move for the specific game type"""
        pass
    
    @abstractmethod
    def validate_game_state(self, state: GameState) -> bool:
        """Validate game state for specific game rules"""
        pass

    @abstractmethod
    def get_game_specific_summary(self) -> Dict[str, Any]:
        """Get game-type specific summary data"""
        pass
    
    async def play(self) -> Game:
        """Play a complete game between the agents"""
        # Initialize new game
        self.game = self.game_engine.create_game(
            player_one=self.player_one.name,
            player_two=self.player_two.name
        )
        
        turn_number = 0
        
        try:
            while not self.game_engine.is_game_over() and turn_number < self.max_moves:
                turn_number += 1
                
                # Get and validate current state
                current_state = self.game_engine.get_state()
                if not self.validate_game_state(current_state):
                    logger.error("Invalid game state detected")
                    break
                
                # Get current agent
                current_agent = self.get_current_agent(current_state)
                
                # Record turn start time
                turn_start = datetime.utcnow()
                
                # Get agent's move with timeout
                try:
                    move = await asyncio.wait_for(
                        current_agent.move(current_state),
                        timeout=self.move_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Agent {current_agent.name} move timed out")
                    move = None
                
                # Calculate turn duration
                turn_duration = (datetime.utcnow() - turn_start).total_seconds() * 1000
                
                if not move or not move.is_valid:
                    logger.warning(f"Agent {current_agent.name} failed to make a valid move")
                    game_turn = GameTurn(
                        turn_number=turn_number,
                        game_state_before=current_state,
                        move=self.create_forfeit_move(current_state, current_agent),
                        game_state_after=current_state,
                        duration_ms=int(turn_duration)
                    )
                    self.game.turns.append(game_turn)
                    self.handle_forfeit(current_state.current_player)
                    break
                
                # Make the move
                success = self.game_engine.make_move(move)
                if not success:
                    logger.error(f"Failed to make move {move.move_notation}")
                    continue
                
                # Record the turn
                game_turn = GameTurn(
                    turn_number=turn_number,
                    game_state_before=current_state,
                    move=move,
                    game_state_after=self.game_engine.get_state(),
                    duration_ms=int(turn_duration)
                )
                self.game.turns.append(game_turn)
            
            # Finalize game
            self.finalize_game(turn_number)
            return self.game
            
        except Exception as e:
            logger.error(f"Error during game: {str(e)}")
            self.handle_error(e)
            return self.game
    
    def handle_forfeit(self, forfeiting_player: Player) -> None:
        """Handle game end due to forfeit"""
        self.game.result = (
            GameResult.PLAYER_TWO_WIN if forfeiting_player == Player.PLAYER_ONE
            else GameResult.PLAYER_ONE_WIN
        )
    
    def handle_error(self, error: Exception) -> None:
        """Handle game error"""
        self.game.end_time = datetime.utcnow()
        self.game.final_state = self.game_engine.get_state()
        self.game.result = GameResult.DRAW
        self.game.metadata["error"] = str(error)
    
    def finalize_game(self, turn_number: int) -> None:
        """Finalize the game state"""
        if turn_number >= self.max_moves:
            logger.info("Game ended due to maximum moves reached")
            self.game.result = GameResult.DRAW
        
        self.game.final_state = self.game_engine.get_state()
        self.game.end_time = datetime.utcnow()
    
    def get_game_summary(self) -> dict:
        """Get a summary of the game"""
        if not self.game:
            return {"status": "No game played"}
            
        summary = {
            "game_id": self.game.game_id,
            "player_one": self.game.player_one,
            "player_two": self.game.player_two,
            "result": self.game.result,
            "total_turns": len(self.game.turns),
            "duration_seconds": (self.game.end_time - self.game.start_time).total_seconds(),
            "moves": [turn.move.move_notation for turn in self.game.turns],
            "player_one_stats": self.player_one.get_stats(),
            "player_two_stats": self.player_two.get_stats()
        }
        
        # Add game-specific summary data
        summary.update(self.get_game_specific_summary())
        
        return summary
 
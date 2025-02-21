from typing import Dict, Any
import time
from datetime import datetime
from .base import AIAgent, AgentConfig
import chess
from ..datamodel import (
    GameState,
    AIMove
)

class StockfishChessAgent(AIAgent):
    """Chess engine based agent using Stockfish"""
    
    def __init__(
        self,
        name: str = "Stockfish",
        depth: int = 15,
        config: AgentConfig = None
    ):
        super().__init__(name, config)
        import chess.engine
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        self.depth = depth
    
    def __del__(self):
        """Ensure engine cleanup on deletion"""
        if hasattr(self, 'engine'):
            self.engine.quit()
    
    def _create_prompt(self, game_state: GameState) -> str:
        """Create a simple prompt for logging purposes"""
        return f"Analyzing position: {game_state.state_repr}"
    
    async def _generate_move(self, game_state: GameState, attempt: int) -> AIMove:
        """Generate a move using Stockfish"""
        try:
            # Create a chess.Board from FEN
            board = chess.Board(game_state.state_repr)
            
            # Get engine analysis
            start_time = time.time()
            result = self.engine.analyse(board, chess.engine.Limit(depth=self.depth))
            analysis_time = time.time() - start_time
            
            # Extract best move and score
            best_move = result["pv"][0]
            score = result["score"].relative.score()
            
            # Convert to UCI format
            move_uci = best_move.uci()
            
            # Create reasoning string
            if score is not None:
                reasoning = f"Position evaluation: {score/100:.2f}, Analysis depth: {self.depth}"
            else:
                reasoning = f"Analysis depth: {self.depth}"
            
            # Create AIMove object
            ai_move = AIMove(
                player=game_state.current_player,
                move_notation=move_uci,
                model_name=self.name,
                reasoning=reasoning,
                tokens_used=0,  # Traditional engines don't use tokens
                retry_count=attempt,
                raw_response=str(result),
                prompt_used=self._create_prompt(game_state),
                is_valid=move_uci in game_state.valid_moves,
                timestamp=datetime.utcnow()
            )
            
            return ai_move
            
        except Exception as e:
            # Create an invalid move object for tracking
            return AIMove(
                player=game_state.current_player,
                move_notation="",
                model_name=self.name,
                reasoning=f"Error: {str(e)}",
                tokens_used=0,
                retry_count=attempt,
                raw_response=str(e),
                prompt_used=self._create_prompt(game_state),
                is_valid=False,
                timestamp=datetime.utcnow()
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        stats = super().get_stats()
        stats.update({
            "engine_type": "Stockfish",
            "analysis_depth": self.depth
        })
        return stats
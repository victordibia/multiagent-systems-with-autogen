import random
from datetime import datetime
from ..datamodel import GameState, AIMove, Player, GeneralPlayer
from .base import AIAgent, AgentConfig

class BasicTicTacToeAgent(AIAgent):
    """Basic agent for TicTacToe that picks a random valid move."""
    
    def __init__(self, name: str = "BasicTicTacToe", config: AgentConfig = None):
        super().__init__(name, config)
    
    def _create_prompt(self, game_state: GameState) -> str:
        # Minimal prompt for logging or debugging 
        return f"TicTacToe state: {game_state.state_repr}"
    
    def _map_player(self, gp: GeneralPlayer) -> Player:
        # Map generic players to Player (assume PLAYER_ONE -> white, PLAYER_TWO -> black)
        return Player.WHITE if gp == GeneralPlayer.PLAYER_ONE else Player.BLACK
    
    async def _generate_move(self, game_state: GameState, attempt: int) -> AIMove:
        valid_moves = game_state.valid_moves
        if not valid_moves:
            move_choice = ""
            is_valid = False
        else:
            move_choice = random.choice(valid_moves)
            is_valid = True
        
        # Map current generic player to a game-specific Player enum
        mapped_player = self._map_player(game_state.current_player)
        
        return AIMove(
            player=mapped_player,
            move_notation=move_choice,
            model_name=self.name,
            reasoning="Random move selection",
            tokens_used=0,
            retry_count=attempt,
            raw_response="",
            prompt_used=self._create_prompt(game_state),
            is_valid=is_valid,
            timestamp=datetime.utcnow()
        )

# ...existing code if needed...

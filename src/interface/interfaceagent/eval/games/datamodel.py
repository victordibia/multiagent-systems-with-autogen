from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

class Player(str, Enum):
    WHITE = "white"
    BLACK = "black"

class GameResult(str, Enum):
    WHITE_WIN = "white_win"
    BLACK_WIN = "black_win"
    DRAW = "draw"
    IN_PROGRESS = "in_progress"

class GeneralPlayer(str, Enum):
    PLAYER_ONE = "player_one"
    PLAYER_TWO = "player_two"

class ChessMetadata(BaseModel):
    check: bool = Field(description="Whether the current player is in check")
    checkmate: bool = Field(description="Whether the game ended in checkmate")
    stalemate: bool = Field(description="Whether the game ended in stalemate")
    insufficient_material: bool = Field(description="Whether there is insufficient material to win")
    can_claim_draw: bool = Field(description="Whether a draw can be claimed")
    halfmove_clock: int = Field(description="Number of halfmoves since last pawn advance or capture")
    fullmove_number: int = Field(description="The number of the full move")
    move_history: List[str] = Field(default_factory=list, description="List of moves in UCI format")

class GameState(BaseModel):
    """Represents the current state of any game"""
    current_player: GeneralPlayer  # changed from Player to GeneralPlayer
    is_terminal: bool = Field(description="Whether the game has ended")
    winner: Optional[GeneralPlayer] = Field(None, description="Winner of the game if terminated")
    valid_moves: List[str] = Field(description="List of valid moves in the current state")
    state_repr: str = Field(description="String representation of the game state (e.g., FEN in chess)")
    metadata: Dict[str, Any] = Field(description="Game-specific metadata")

class Move(BaseModel):
    """Represents a single move in the game"""
    player: Player
    move_notation: str = Field(description="Move in game-specific notation (e.g., UCI in chess)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_valid: bool = Field(description="Whether the move was valid")

class AIMove(Move):
    """Represents a move made by an AI agent"""
    model_name: str = Field(description="Name of the AI model")
    reasoning: str = Field(description="AI's reasoning for the move")
    tokens_used: int = Field(description="Number of tokens used for this move")
    retry_count: int = Field(0, description="Number of retries needed to generate valid move")
    raw_response: str = Field(description="Raw response from the AI model")
    prompt_used: str = Field(description="Prompt used to generate the move")
    
class GameTurn(BaseModel):
    """Represents a complete turn in the game"""
    turn_number: int
    game_state_before: GameState
    move: AIMove
    game_state_after: GameState
    duration_ms: int = Field(description="Time taken for this turn in milliseconds")

class Game(BaseModel):
    """Represents a complete game"""
    game_id: str = Field(description="Unique identifier for the game")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    player_white: str = Field(description="Name/ID of white player")
    player_black: str = Field(description="Name/ID of black player")
    initial_state: GameState
    turns: List[GameTurn] = Field(default_factory=list)
    final_state: Optional[GameState] = None
    result: GameResult = Field(default=GameResult.IN_PROGRESS)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TournamentResult(BaseModel):
    """Represents results from a tournament between AI models"""
    tournament_id: str = Field(description="Unique identifier for the tournament")
    start_time: datetime
    end_time: datetime
    participants: List[str] = Field(description="List of AI model names")
    games: List[Game]
    statistics: Dict[str, Any] = Field(description="Tournament statistics")

    @property
    def total_games(self) -> int:
        return len(self.games)
    
    @property
    def winner(self) -> Optional[str]:
        # Logic to determine tournament winner based on games
        pass

class ModelPerformance(BaseModel):
    """Statistics for a single AI model's performance"""
    model_name: str
    games_played: int
    games_won: int
    games_lost: int
    games_drawn: int
    average_moves_per_game: float
    average_tokens_per_move: float
    average_retries_per_move: float
    total_tokens_used: int
    average_time_per_move_ms: float
    win_rate: float = Field(description="Win rate as a percentage")

    @property
    def win_rate_percentage(self) -> float:
        if self.games_played == 0:
            return 0.0
        return (self.games_won / self.games_played) * 100



class GameType(str, Enum):
    CHESS = "chess"
    TIC_TAC_TOE = "tic_tac_toe"
    BACKGAMMON = "backgammon"

class ChessMetadata(BaseModel):
    check: bool
    checkmate: bool 

class TicTacToeMetadata(BaseModel):
    last_mark_position: Optional[Tuple[int, int]] = None  
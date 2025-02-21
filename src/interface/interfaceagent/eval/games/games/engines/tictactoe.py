from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from ...datamodel import (
    GameState,
    GeneralPlayer,   # added generic player
    Game,
    GameResult,
    GameType,
    TicTacToeMetadata
)
from ..engines import GameEngine

class TicTacToeEngine(GameEngine):
    """Tic-tac-toe game implementation using generic players."""
    
    def __init__(self):
        # Board is represented as a list of 9 elements
        # Empty = None, X = GeneralPlayer.PLAYER_ONE, O = GeneralPlayer.PLAYER_TWO
        self.board: List[Optional[GeneralPlayer]] = [None] * 9
        self.current_player = GeneralPlayer.PLAYER_ONE  # using generic role
        self.game: Optional[Game] = None
        self.move_history: List[int] = []
        
        # Winning combinations (indices)
        self.winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]              # Diagonals
        ]
    
    def get_state(self) -> GameState:
        """Returns current game state"""
        return GameState(
            current_player=self.current_player,
            is_terminal=self.is_game_over(),
            winner=self.get_winner(),
            valid_moves=self.get_valid_moves(),
            state_repr=self._board_to_string(),
            metadata=self._get_metadata()
        )
    
    def is_valid_move(self, move: str) -> bool:
        """Checks if a move is valid in current state"""
        try:
            position = int(move)
            return (
                0 <= position < 9 and
                self.board[position] is None
            )
        except ValueError:
            return False
    
    def make_move(self, move: str) -> bool:
        """Attempts to make a move. Returns True if successful"""
        if not self.is_valid_move(move):
            return False
        
        position = int(move)
        self.board[position] = self.current_player
        self.move_history.append(position)
        
        # Update current player
        self.current_player = (
            GeneralPlayer.PLAYER_TWO if self.current_player == GeneralPlayer.PLAYER_ONE
            else GeneralPlayer.PLAYER_ONE
        )
        
        # Update game metadata if exists
        if self.game:
            self.game.metadata["move_history"] = self.move_history
            if self.is_game_over():
                self.game.end_time = datetime.utcnow()
                self.game.final_state = self.get_state()
                self.game.result = self._get_game_result()
        
        return True
    
    def is_game_over(self) -> bool:
        """Checks if the game has ended"""
        return self.get_winner() is not None or len(self.get_valid_moves()) == 0
    
    def get_winner(self) -> Optional[GeneralPlayer]:
        """Returns winner if game is over, None otherwise"""
        for combo in self.winning_combinations:
            values = [self.board[i] for i in combo]
            if values[0] is not None and all(v == values[0] for v in values):
                return values[0]
        return None
    
    def get_valid_moves(self) -> List[str]:
        """Returns list of valid moves in current state"""
        return [str(i) for i, cell in enumerate(self.board) if cell is None]
    
    def reset(self) -> None:
        """Resets the game to initial state"""
        self.board = [None] * 9
        self.current_player = GeneralPlayer.PLAYER_ONE
        self.game = None
        self.move_history = []
    
    def create_game(self, player_one: str, player_two: str) -> Game:
        """Creates a new game instance"""
        self.reset()
        initial_state = self.get_state()
        
        self.game = Game(
            game_id=str(uuid.uuid4()),
            start_time=datetime.utcnow(),
            player_white=player_one,
            player_black=player_two,
            initial_state=initial_state,
            result=GameResult.IN_PROGRESS,
            metadata={
                "game_type": GameType.TIC_TAC_TOE,
                "move_history": [],
                "board_size": 3,
                "winning_combinations": self.winning_combinations
            }
        )
        
        return self.game
    
    def _board_to_string(self) -> str:
        """Map generic players to symbols for TicTacToe"""
        mapping = {
            GeneralPlayer.PLAYER_ONE: 'X',
            GeneralPlayer.PLAYER_TWO: 'O',
            None: '-'
        }
        return ','.join(mapping[cell] for cell in self.board)
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Get current game metadata"""
        return TicTacToeMetadata(
            last_move=self.move_history[-1] if self.move_history else None,
            move_history=self.move_history.copy(),
            board_size=3,
            winning_combinations=self.winning_combinations,
            center_taken=self.board[4] is not None,
            corners_taken=sum(1 for i in [0, 2, 6, 8] if self.board[i] is not None)
        ).dict()
    
    def _get_game_result(self) -> GameResult:
        """Determine game result"""
        winner = self.get_winner()
        
        if winner == GeneralPlayer.PLAYER_ONE:
            return GameResult.WHITE_WIN
        elif winner == GeneralPlayer.PLAYER_TWO:
            return GameResult.BLACK_WIN
        elif self.is_game_over():
            return GameResult.DRAW
        else:
            return GameResult.IN_PROGRESS
    
    def get_board_visual(self) -> str:
        """Returns a visual representation of the board"""
        symbols = {
            GeneralPlayer.PLAYER_ONE: 'X',
            GeneralPlayer.PLAYER_TWO: 'O',
            None: ' '
        }
        
        rows = [
            self.board[i:i+3] for i in range(0, 9, 3)
        ]
        
        board_str = '\n-----------\n'.join(
            ' | '.join(symbols[cell] for cell in row)
            for row in rows
        )
        
        return f"\n{board_str}\n"
    
    def load_state(self, moves: List[int]) -> bool:
        """Loads a game state from a list of moves"""
        try:
            self.reset()
            for move in moves:
                if not self.make_move(str(move)):
                    return False
            return True
        except Exception:
            self.reset()
            return False

# # Example usage
# if __name__ == "__main__":
#     # Create a new tic-tac-toe game
#     engine = TicTacToeEngine()
    
#     # Initialize a game
#     game = engine.create_game("Player1", "Player2")
    
#     # Get initial state
#     state = engine.get_state()
#     print(f"Current player: {state.current_player}")
#     print(f"Valid moves: {state.valid_moves}")
#     print(engine.get_board_visual())
    
#     # Make some moves
#     moves = ["4", "0", "1", "3", "7"]  # Center, top-left, top-middle, middle-left, bottom-middle
#     for move in moves:
#         if engine.is_valid_move(move):
#             engine.make_move(move)
#             print(f"\nMade move: {move}")
#             print(engine.get_board_visual())
#             print(f"Valid moves: {engine.get_valid_moves()}")
#             print(f"Game over: {engine.is_game_over()}")
#             winner = engine.get_winner()
#             if winner:
#                 print(f"Winner: {winner}")
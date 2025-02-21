from typing import List, Optional, Dict, Any
import chess
import uuid
from datetime import datetime
from .base import GameEngine
from ...datamodel import (
    GameState,
    GeneralPlayer,  # use generic players
    Player,
    ChessMetadata,
    Game,
    GameResult,
    Move
)

 
class ChessGameEngine(GameEngine):
    """Chess implementation using python-chess with generic players"""
    
    def __init__(self, player_one_is_white: bool = True):
        self.board = chess.Board()
        self.game: Optional[Game] = None
        self.player_map = {  # map generic players to chess colors based on configuration
            GeneralPlayer.PLAYER_ONE: (Player.WHITE if player_one_is_white else Player.BLACK),
            GeneralPlayer.PLAYER_TWO: (Player.BLACK if player_one_is_white else Player.WHITE)
        }
        self.current_player = GeneralPlayer.PLAYER_ONE
        self.reset()
    
    def get_state(self) -> GameState:
        return GameState(
            current_player=self.current_player,
            is_terminal=self.board.is_game_over(),
            winner=self.get_winner(),
            valid_moves=self.get_valid_moves(),
            state_repr=self.board.fen(),
            metadata=self._get_metadata()
        )
    
    def is_valid_move(self, move: str) -> bool:
        try:
            chess_move = chess.Move.from_uci(move)
            return chess_move in self.board.legal_moves
        except ValueError:
            return False
    
    def make_move(self, move: Move) -> bool:
        if not self.is_valid_move(move.move_notation):
            return False
        
        chess_move = chess.Move.from_uci(move.move_notation)
        self.board.push(chess_move)
        
        # Switch generic current player
        self.current_player = (GeneralPlayer.PLAYER_TWO if self.current_player == GeneralPlayer.PLAYER_ONE else GeneralPlayer.PLAYER_ONE)
        
        # Update game metadata
        if self.game:
            metadata = self._get_metadata()
            metadata["move_history"].append(move.move_notation)
            
            # Update game state
            if self.is_game_over():
                self.game.end_time = datetime.utcnow()
                self.game.final_state = self.get_state()
                self.game.result = self._get_game_result()
        
        return True
    
    def is_game_over(self) -> bool:
        return self.board.is_game_over()
    
    def get_winner(self) -> Optional[GeneralPlayer]:
        winner = self._determine_winner()
        if winner is None:
            return None
        for general_player, player in self.player_map.items():
            if player == winner:
                return general_player
        return None
    
    def get_valid_moves(self) -> List[str]:
        return [move.uci() for move in self.board.legal_moves]
    
    def reset(self) -> None:
        self.board = chess.Board()
        self.game = None
    
    def create_game(self, player_white: str, player_black: str) -> Game:
        self.reset()
        initial_state = self.get_state()
        
        self.game = Game(
            game_id=str(uuid.uuid4()),
            start_time=datetime.utcnow(),
            player_white=player_white,
            player_black=player_black,
            initial_state=initial_state,
            result=GameResult.IN_PROGRESS,
            metadata={
                "engine": "chess",
                "initial_fen": self.board.fen(),
                "moves": []
            }
        )
        
        return self.game
    
    def _determine_winner(self) -> Optional[Player]:
        if not self.is_game_over():
            return None
        
        if self.board.is_checkmate():
            # If it's checkmate, the player who just moved won
            return Player.BLACK if self.board.turn else Player.WHITE
        
        # Draw conditions
        if (self.board.is_stalemate() or 
            self.board.is_insufficient_material() or 
            self.board.is_fifty_moves() or 
            self.board.is_repetition()):
            return None
            
        return None
    
    def _get_game_result(self) -> GameResult:
        winner = self._determine_winner()
        
        if winner == Player.WHITE:
            return GameResult.WHITE_WIN
        elif winner == Player.BLACK:
            return GameResult.BLACK_WIN
        elif self.is_game_over():
            return GameResult.DRAW
        else:
            return GameResult.IN_PROGRESS
    
    def _get_metadata(self) -> Dict[str, Any]:
        return ChessMetadata(
            check=self.board.is_check(),
            checkmate=self.board.is_checkmate(),
            stalemate=self.board.is_stalemate(),
            insufficient_material=self.board.is_insufficient_material(),
            can_claim_draw=self.board.can_claim_draw(),
            halfmove_clock=self.board.halfmove_clock,
            fullmove_number=self.board.fullmove_number,
            move_history=[] if not self.game else self.game.metadata.get("moves", [])
        ).dict()
    
    def get_board_visual(self) -> str:
        """Returns a string representation of the current board state"""
        return str(self.board)
    
    def get_game_pgn(self) -> str:
        """Returns the game in PGN format"""
        return str(self.board.epd())
    
    def load_fen(self, fen: str) -> bool:
        """Loads a position from FEN notation"""
        try:
            self.board = chess.Board(fen)
            if self.game:
                self.game.metadata["current_fen"] = fen
            return True
        except ValueError:
            return False
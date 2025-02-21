class BaseGameMatch:
    def __init__(self, game, player_one, player_two):
        self.game = game
        self.player_one = player_one
        self.player_two = player_two

    def get_game_summary(self) -> dict:
        """Get a summary of the game"""
        if not self.game:
            return {"status": "No game played"}
            
        summary = {
            "game_id": self.game.game_id,
            "player_one": self.game.player_white,  # changed from player_one to player_white
            "player_two": self.game.player_black,  # changed from player_two to player_black
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

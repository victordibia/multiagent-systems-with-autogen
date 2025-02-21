import asyncio
# ...existing imports...
from interfaceagent.eval.games.engines.tictactoe import TicTacToeEngine
from interfaceagent.eval.games.agents.tictactoe import BasicTicTacToeAgent

async def run_match():
    engine = TicTacToeEngine()
    game = engine.create_game("Player1", "Player2")
    agent = BasicTicTacToeAgent()
    
    print("Starting TicTacToe match")
    print(engine.get_board_visual())
    
    while not engine.is_game_over():
        state = engine.get_state()
        ai_move = await agent.move(state)
        if not ai_move:
            print("No valid move returned, ending match.")
            break
        print(f"Move chosen: {ai_move.move_notation}")
        engine.make_move(ai_move.move_notation)
        print(engine.get_board_visual())
    
    winner = engine.get_winner()
    if winner:
        print(f"Winner: {winner}")
    else:
        print("Match draw.")

if __name__ == "__main__":
    asyncio.run(run_match())

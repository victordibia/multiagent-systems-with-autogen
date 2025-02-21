from datetime import datetime
from openai import OpenAI 
from .base import AIAgent, AgentConfig

from ..datamodel import (
    GameState,
    AIMove
)

class OpenAIBaseAgent(AIAgent):
    """Base class for OpenAI-based agents"""
    
    def __init__(
        self, 
        name: str,
        api_key: str,
        model: str = "gpt-4",
        config: AgentConfig = None
    ):
        super().__init__(name, config)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent"""
        return """You are a chess engine. Your task is to analyze the current board position
        and suggest the best move. You should:
        1. Analyze the current position
        2. Consider possible moves and their consequences
        3. Select the best move
        4. Explain your reasoning
        5. Return the move in UCI format (e.g., 'e2e4')
        
        Only return moves that are valid in the current position."""
    
    def _create_chess_prompt(self, game_state: GameState) -> str:
        """Create a chess-specific prompt"""
        return f"""Current board position (FEN):
        {game_state.state_repr}
        
        Playing as: {game_state.current_player}
        Valid moves: {', '.join(game_state.valid_moves)}
        
        Previous moves: {game_state.metadata.get('move_history', [])}
        
        Analyze the position and provide:
        1. Your chosen move in UCI format
        2. A brief explanation of your reasoning
        
        Format your response as:
        MOVE: <uci_move>
        REASONING: <your_explanation>"""
    
    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse the response to extract move and reasoning"""
        try:
            # Split into lines and clean
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            move = None
            reasoning = None
            
            for line in lines:
                if line.startswith('MOVE:'):
                    move = line.replace('MOVE:', '').strip()
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
            
            if not move or not reasoning:
                raise ValueError("Missing move or reasoning in response")
                
            return move, reasoning
            
        except Exception as e:
            raise ValueError(f"Failed to parse response: {str(e)}")
    
    async def _generate_move(self, game_state: GameState, attempt: int) -> AIMove:
        """Generate a move using OpenAI API"""
        system_prompt = self._create_system_prompt()
        chess_prompt = self._create_chess_prompt(game_state)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chess_prompt}
                ],
                temperature=self.config.temperature,
                timeout=self.config.timeout_seconds
            )
            
            # Extract the response content
            response_text = response.choices[0].message.content
            move_text, reasoning = self._parse_response(response_text)
            
            # Create AIMove object
            ai_move = AIMove(
                player=game_state.current_player,
                move_notation=move_text,
                model_name=self.name,
                reasoning=reasoning,
                tokens_used=response.usage.total_tokens,
                retry_count=attempt,
                raw_response=response_text,
                prompt_used=chess_prompt,
                is_valid=move_text in game_state.valid_moves,
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
                prompt_used=chess_prompt,
                is_valid=False,
                timestamp=datetime.utcnow()
            )
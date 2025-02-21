from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import time
from datetime import datetime
import openai
from openai import OpenAI 

from ..datamodel import (
    GameState,
    AIMove,
    Player,
    Move
)

class AgentConfig:
    """Base configuration for AI agents"""
    max_retries: int = 3
    timeout_seconds: float = 30.0
    temperature: float = 0.7

class AIAgent(ABC):
    """Base class for AI agents"""
    
    def __init__(self, name: str, config: AgentConfig = None):
        self.name = name
        self.config = config or AgentConfig()
        self._total_tokens = 0
        self._total_moves = 0
        
    @abstractmethod
    async def _generate_move(self, game_state: GameState, attempt: int) -> AIMove:
        """Generate a single move attempt"""
        pass
    
    @abstractmethod
    def _create_prompt(self, game_state: GameState) -> str:
        """Create the prompt for move generation"""
        pass
    
    async def move(self, game_state: GameState) -> Optional[AIMove]:
        """
        Main method to generate a move. Handles retries and validation.
        Returns None if unable to generate a valid move within max retries.
        """
        start_time = time.time()
        
        for attempt in range(self.config.max_retries):
            try:
                ai_move = await self._generate_move(game_state, attempt)
                
                # Update statistics
                self._total_tokens += ai_move.tokens_used
                self._total_moves += 1
                
                # If move is valid, return it
                if ai_move.is_valid:
                    return ai_move
                    
            except Exception as e:
                print(f"Error generating move (attempt {attempt + 1}): {str(e)}")
                continue
                
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "name": self.name,
            "total_tokens": self._total_tokens,
            "total_moves": self._total_moves,
            "average_tokens_per_move": self._total_tokens / max(1, self._total_moves),
        }

from fastembed import TextEmbedding
import numpy as np
from typing import Optional

class Auditor:
    def __init__(self, threshold: float = 0.4, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.threshold = threshold
        self.embedder = TextEmbedding(model_name=model_name)
        self.goal_embedding = None

    def set_goal(self, goal: str):
        self.goal_embedding = list(self.embedder.embed([goal]))[0]

    def check(self, action_description: str) -> float:
        """
        Returns drift score. 
        Higher is better (closer to 1.0).
        """
        if self.goal_embedding is None:
            return 1.0 # Pass if no goal set
            
        action_vec = list(self.embedder.embed([action_description]))[0]
        score = np.dot(self.goal_embedding, action_vec)
        return float(score)
    
    def is_safe(self, score: float) -> bool:
        return score >= self.threshold

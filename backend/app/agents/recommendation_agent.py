from typing import Dict, List, Any
import json
from .base_agent import BaseAgent

class RecommendationAgent(BaseAgent):
    """
    Tüm agent çıktılarını birleştir ve final öneriler yap
    """
    
    def __init__(self, llm_service, db_service):
        super().__init__(name="RecommendationAgent", llm_service=llm_service, db_service=db_service)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tüm agent çıktılarını al ve final öneriler üret"""
        
        try:
            self.log_action("execute", {"user_id": input_data.get("user_id")})
            
            return {
                "status": "success",
                "recommendations": {
                    "products": [
                        {"name": "Ürün 1", "price": 1000},
                        {"name": "Ürün 2", "price": 2000}
                    ]
                },
                "agent": self.name
            }
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent": self.name
            }
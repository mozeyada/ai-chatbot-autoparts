"""
Helper function to handle vague vehicle-related queries using LLM.
"""
from intent import call_groq_api

def handle_vague_vehicle_query(message: str, groq_api_key: str) -> str:
    """Handle vague vehicle-related queries using LLM"""
    try:
        system_prompt = """You are a helpful auto parts store assistant.
        
        The user has mentioned something about a vehicle but hasn't specified what parts they need.
        
        Respond in a friendly, conversational way (2-3 sentences) that:
        1. Acknowledges their message about their vehicle
        2. Asks what specific parts they're looking for
        3. Provides examples of common parts (battery, tires, brakes, oil, filters)
        
        Be helpful and natural in your response.
        """
        
        return call_groq_api(groq_api_key, message, system_prompt)
    except Exception as e:
        print(f"LLM vehicle query handling failed: {e}")
        return "I'd be happy to help with your car! What specific parts are you looking for? For example, do you need a battery, tires, brakes, or something else?"
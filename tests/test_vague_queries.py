#!/usr/bin/env python3
"""
Unit tests for vague query handling
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_greeting_handling():
    """Test that simple greetings are handled properly"""
    bot = AutoPartsChatbot()
    
    # Simple greeting should be classified as chitchat, not nonsense
    response = bot.process_message("Hi", [])
    
    # Should respond with a greeting, not a nonsense message
    assert "help" in response.lower()
    assert "vehicle" in response.lower() or "part" in response.lower()

def test_vague_car_query():
    """Test handling of vague car-related queries"""
    bot = AutoPartsChatbot()
    
    # Vague car query
    response = bot.process_message("My car", [])
    
    # Should respond with a helpful message asking for more details
    assert "part" in response.lower()
    assert "vehicle" in response.lower() or "car" in response.lower()

def test_unknown_query_llm_response():
    """Test that unknown queries get LLM responses"""
    bot = AutoPartsChatbot()
    
    # Unknown query that should trigger LLM response
    response = bot.process_message("I have a good car", [])
    
    # Should not contain the default unknown response
    assert "I didn't catch that" not in response
    
    # Should contain helpful guidance
    assert "part" in response.lower() or "vehicle" in response.lower()

if __name__ == "__main__":
    pytest.main([__file__])
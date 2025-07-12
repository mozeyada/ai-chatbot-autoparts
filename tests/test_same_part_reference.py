#!/usr/bin/env python3
"""
Unit tests for same part/car reference resolution
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_same_part_reference():
    """Toyota tires flow, then 'same car' → bot should not ask for make again"""
    bot = AutoPartsChatbot()
    
    # Establish Toyota tires context
    response1 = bot.process_message("Toyota tires", [])
    assert "toyota" in response1.lower()
    assert "tire" in response1.lower()
    
    # Use same car reference
    response2 = bot.process_message("same car", [])
    
    # Should not ask for make again
    assert "which make" not in response2.lower()
    assert "available makes" not in response2.lower()
    # Should reference Toyota context
    assert "toyota" in response2.lower() or "what type of part" in response2.lower()

def test_same_part_reference_with_new_part():
    """Test same car with new part specification"""
    bot = AutoPartsChatbot()
    
    # Establish Honda context
    bot.process_message("Honda battery", [])
    
    # Use same car with new part
    response = bot.process_message("same car brakes", [])
    
    # Should find Honda brakes
    assert "honda" in response.lower()
    assert "brake" in response.lower()
    assert "which make" not in response.lower()

def test_that_one_reference():
    """Test 'that one' reference"""
    bot = AutoPartsChatbot()
    
    # Establish context
    bot.process_message("Ford battery", [])
    
    # Use that one reference
    response = bot.process_message("that one", [])
    
    # Should maintain Ford battery context
    assert "ford" in response.lower() or "battery" in response.lower()

def test_same_part_without_context():
    """Test same part reference without prior context"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("same car", [])
    
    # Should handle gracefully
    assert len(response) > 0
    # May ask for clarification or give general help

if __name__ == "__main__":
    pytest.main([__file__])
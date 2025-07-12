#!/usr/bin/env python3
"""
Unit tests for same car coreference resolution
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_same_car_coref():
    """Toyota battery → tires → same car returns Toyota tires without re-asking make"""
    bot = AutoPartsChatbot()
    
    # Step 1: Toyota battery
    response1 = bot.process_message("Toyota battery", [])
    assert "toyota" in response1.lower()
    
    # Step 2: tires (should use Toyota context)
    response2 = bot.process_message("tires", [])
    assert "toyota" in response2.lower()
    assert "tire" in response2.lower()
    
    # Step 3: same car (should use Toyota context)
    response3 = bot.process_message("same car", [])
    assert "toyota" in response3.lower()
    assert "didn't catch that" not in response3.lower()

def test_coref_resolver():
    """Test coreference resolver function directly"""
    bot = AutoPartsChatbot()
    
    # Set up context
    ctx = {'vehicle_make': 'Honda', 'part_category': 'Battery'}
    
    # Test vehicle coreference
    resolved = bot.resolve_coref("same car tires", ctx)
    assert "Honda" in resolved
    
    # Test part coreference
    resolved = bot.resolve_coref("same part for Toyota", ctx)
    assert "Battery" in resolved

if __name__ == "__main__":
    pytest.main([__file__])
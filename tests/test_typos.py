#!/usr/bin/env python3
"""
Unit tests for typo handling in vehicle makes and parts
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_vehicle_make_typos():
    """Test that vehicle make typos are fuzzy matched correctly"""
    bot = AutoPartsChatbot()
    
    # Test common typos
    assert bot.normalize_make("hond") == "Honda"
    assert bot.normalize_make("toyta") == "Toyota"
    assert bot.normalize_make("chevy") == "Chevrolet"
    assert bot.normalize_make("mercedes") == "Mercedes-Benz"
    assert bot.normalize_make("volkswagen") == "Volkswagen"

def test_batteries_for_my_hond():
    """Test 'batteries for my hond' should not ask again for make"""
    bot = AutoPartsChatbot()
    
    # Process the message with vehicle typo
    response = bot.process_message("batteries for my hond", [])
    
    # Should either find Honda battery parts OR offer lead capture
    # Should NOT ask for make again since "hond" should resolve to "Honda"
    assert "which vehicle make" not in response.lower()
    assert "honda" in response.lower() or "sorry" in response.lower() or "notify" in response.lower()
    
    # Verify the session captured Honda correctly
    assert bot.session_vehicle == "Honda"
    assert bot.session_part == "Battery"

def test_extract_vehicle_and_part_with_typos():
    """Test vehicle and part extraction with various typos"""
    bot = AutoPartsChatbot()
    
    # Test vehicle typos
    vehicle, part = bot.extract_vehicle_and_part("hond battery")
    assert vehicle == "Honda"
    assert part == "Battery"
    
    vehicle, part = bot.extract_vehicle_and_part("toyta tires")
    assert vehicle == "Toyota"
    assert part == "Tires"
    
    # Test part typos
    vehicle, part = bot.extract_vehicle_and_part("Honda battries")
    assert vehicle == "Honda"
    assert part == "Battery"

if __name__ == "__main__":
    pytest.main([__file__])
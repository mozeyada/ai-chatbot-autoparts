#!/usr/bin/env python3
"""
Unit tests for context preservation and state management fixes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_install_follow_up():
    """Battery → install keeps context and provides time estimate"""
    bot = AutoPartsChatbot()
    
    # Get Toyota battery
    response1 = bot.process_message("Toyota battery", [])
    assert "toyota" in response1.lower()
    assert "battery" in response1.lower()
    
    # Ask for installation - should preserve context
    response2 = bot.process_message("installation", [])
    
    # Should provide time estimate and keep context
    assert "30 minutes" in response2.lower() or "30" in response2
    assert "toyota" in response2.lower() or "battery" in response2.lower()
    assert "appointment" in response2.lower() or "book" in response2.lower()

def test_toxic_preserves_state():
    """Toxic language should preserve conversation context"""
    bot = AutoPartsChatbot()
    
    # Establish context
    bot.process_message("Honda battery", [])
    
    # Use toxic language
    response = bot.process_message("fuck you", [])
    
    # Should de-escalate but preserve context
    assert "respectful" in response.lower()
    assert "honda" in response.lower() or "battery" in response.lower()

def test_lead_capture_sales_query():
    """Car sales query should trigger lead capture"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("I need to buy a new car", [])
    
    # Should offer dealership help and trigger lead capture
    assert "dealership" in response.lower()
    assert "contact" in response.lower()
    assert bot.awaiting_lead_capture == True

def test_chitchat_no_invalid_count():
    """Chitchat should not increment invalid turns counter"""
    bot = AutoPartsChatbot()
    
    initial_count = bot.oops_count
    
    # Chitchat should not increment counter
    bot.process_message("How is it going", [])
    
    assert bot.oops_count == initial_count

def test_install_time_lookup():
    """Test installation time lookup from CSV"""
    bot = AutoPartsChatbot()
    
    # Test known categories
    assert bot.get_install_time_minutes("Battery") == 30
    assert bot.get_install_time_minutes("Tires") == 45
    assert bot.get_install_time_minutes("Brakes") == 90
    
    # Test fallback
    assert bot.get_install_time_minutes("Unknown Part") == 45

def test_available_makes_dynamic():
    """Test that available makes come from data"""
    bot = AutoPartsChatbot()
    
    makes = bot.get_available_makes()
    
    # Should be a list of strings
    assert isinstance(makes, list)
    assert len(makes) > 0
    assert all(isinstance(make, str) for make in makes)
    
    # Should include common makes
    assert "Honda" in makes
    assert "Toyota" in makes

if __name__ == "__main__":
    pytest.main([__file__])
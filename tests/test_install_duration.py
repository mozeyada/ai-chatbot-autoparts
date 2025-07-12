#!/usr/bin/env python3
"""
Unit tests for installation duration estimates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_install_duration():
    """Ask for Honda battery, then 'When can I come to install it?' → expects '30 min'"""
    bot = AutoPartsChatbot()
    
    # First get Honda battery
    response1 = bot.process_message("Honda battery", [])
    assert "honda" in response1.lower()
    assert "battery" in response1.lower()
    
    # Ask about installation timing
    response2 = bot.process_message("When can I come to install it?", [])
    
    # Should provide duration estimate
    assert "30 minutes" in response2.lower() or "30 min" in response2.lower()
    assert "appointment" in response2.lower() or "book" in response2.lower()

def test_tire_installation_duration():
    """Test tire installation duration"""
    bot = AutoPartsChatbot()
    
    bot.process_message("Toyota tires", [])
    response = bot.process_message("how long to install", [])
    
    assert "45 minutes" in response.lower() or "45 min" in response.lower()

def test_brake_installation_duration():
    """Test brake installation duration"""
    bot = AutoPartsChatbot()
    
    bot.process_message("Honda brakes", [])
    response = bot.process_message("installation time", [])
    
    assert "90 minutes" in response.lower() or "90 min" in response.lower()

def test_installation_without_context():
    """Test installation query without prior context"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("how long to install", [])
    
    # Should ask for more info
    assert "what part" in response.lower() or "help" in response.lower()

if __name__ == "__main__":
    pytest.main([__file__])
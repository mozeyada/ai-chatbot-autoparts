#!/usr/bin/env python3
"""
Unit tests for DIY installation guidance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_lights_installation_diy():
    """Test after lights recommendation, user asks 'Do I install myself?' → bot provides DIY tip + booking offer"""
    bot = AutoPartsChatbot()
    
    # First get a lights recommendation
    response1 = bot.process_message("Toyota lights", [])
    assert "light" in response1.lower()
    
    # Ask about installation
    response2 = bot.process_message("Do I install myself?", [])
    
    # Should provide DIY guidance
    assert "installation is typically" in response2.lower()
    assert "diy guide" in response2.lower() or "steps" in response2.lower()
    assert "safety" in response2.lower()
    assert "book professional installation" in response2.lower() or "technician" in response2.lower()

def test_battery_installation_diy():
    """Test battery installation provides DIY tips"""
    bot = AutoPartsChatbot()
    
    # Get battery recommendation
    bot.process_message("Honda battery", [])
    
    # Ask about installation
    response = bot.process_message("how do I install this?", [])
    
    # Should provide battery-specific DIY tips
    assert "installation is typically" in response.lower()
    assert "disconnect negative terminal first" in response.lower() or "safety gloves" in response.lower()
    assert "technician" in response.lower()

def test_wiper_installation_diy():
    """Test wiper blade installation provides simple DIY tips"""
    bot = AutoPartsChatbot()
    
    # Get wiper recommendation
    bot.process_message("Toyota wiper blades", [])
    
    # Ask about installation
    response = bot.process_message("installation", [])
    
    # Should provide simple DIY guidance
    assert "installation is typically" in response.lower()
    assert "easy" in response.lower()
    assert "technician" in response.lower()

def test_air_filter_installation_diy():
    """Test air filter installation provides DIY guidance"""
    bot = AutoPartsChatbot()
    
    # Get air filter recommendation
    bot.process_message("Honda air filter", [])
    
    # Ask about installation
    response = bot.process_message("how to install", [])
    
    # Should provide air filter DIY tips
    assert "installation is typically" in response.lower()
    assert "air filter" in response.lower()
    assert "technician" in response.lower()

def test_spark_plugs_installation_diy():
    """Test spark plugs installation provides medium difficulty DIY tips"""
    bot = AutoPartsChatbot()
    
    # Get spark plugs recommendation
    bot.process_message("Honda spark plugs", [])
    
    # Ask about installation
    response = bot.process_message("fitting", [])
    
    # Should provide spark plug specific guidance
    assert "installation is typically" in response.lower()
    assert "medium" in response.lower() or "gap" in response.lower()
    assert "technician" in response.lower()

def test_installation_without_recent_part():
    """Test installation query without recent part recommendation"""
    bot = AutoPartsChatbot()
    
    # Ask about installation without context
    response = bot.process_message("Do you do installation?", [])
    
    # Should offer general installation help
    assert "certified mechanics" in response.lower() or "professional installation" in response.lower()
    assert "what part" in response.lower()

if __name__ == "__main__":
    pytest.main([__file__])
#!/usr/bin/env python3
"""
Unit tests for installation flow
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_diy_install_flow():
    """Lights recommendation → 'Do I install myself?' returns DIY tip + booking offer"""
    bot = AutoPartsChatbot()
    
    # Get lights recommendation
    response1 = bot.process_message("Toyota lights", [])
    assert "light" in response1.lower()
    
    # Ask about installation
    response2 = bot.process_message("Do I install myself?", [])
    
    # Should provide DIY guidance or installation help
    assert len(response2) > 50  # Substantial response
    assert "install" in response2.lower()

def test_installation_intent_detection():
    """Test installation intent is detected"""
    bot = AutoPartsChatbot()
    
    install_phrases = [
        "install",
        "installation", 
        "fit",
        "fitting",
        "how do I put",
        "do you do the install"
    ]
    
    for phrase in install_phrases:
        intent = bot.detect_intent(phrase)
        assert intent == 'installation'

def test_complex_part_install():
    """Complex parts should offer service booking"""
    bot = AutoPartsChatbot()
    
    # Get brake recommendation
    bot.process_message("Honda brakes", [])
    
    # Ask about installation
    response = bot.process_message("installation", [])
    
    # Should offer professional installation
    assert "professional" in response.lower() or "service" in response.lower() or "technician" in response.lower()

if __name__ == "__main__":
    pytest.main([__file__])
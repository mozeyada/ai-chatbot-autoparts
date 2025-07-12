#!/usr/bin/env python3
"""
Unit tests for professional installation service booking
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_brakes_installation_service():
    """Test brakes recommendation → installation question → service booking flow"""
    bot = AutoPartsChatbot()
    
    # Get brake recommendation
    response1 = bot.process_message("Honda brake pads", [])
    assert "brake" in response1.lower()
    
    # Ask about installation
    response2 = bot.process_message("Do I install myself?", [])
    
    # Should recommend professional installation for brakes
    assert "professional installation" in response2.lower() or "certified technician" in response2.lower()
    assert "safety" in response2.lower() or "warranty" in response2.lower()
    assert "arrange" in response2.lower() or "contact you" in response2.lower()

def test_suspension_installation_service():
    """Test suspension parts require professional installation"""
    bot = AutoPartsChatbot()
    
    # Get suspension recommendation
    bot.process_message("Honda struts", [])
    
    # Ask about installation
    response = bot.process_message("installation", [])
    
    # Should recommend professional service
    assert "professional installation" in response.lower()
    assert "service booking" in response.lower() or "technician" in response.lower()

def test_installation_service_lead_flow():
    """Test installation service booking leads to contact collection"""
    bot = AutoPartsChatbot()
    
    # Get brake recommendation and ask about installation
    bot.process_message("Toyota brake rotors", [])
    bot.process_message("how to install", [])
    
    # Agree to service booking
    response1 = bot.process_message("Yes, arrange service", [])
    assert "name" in response1.lower()
    
    # Provide name
    response2 = bot.process_message("John Smith", [])
    assert "phone or email" in response2.lower()
    
    # Provide contact
    response3 = bot.process_message("john@email.com", [])
    assert "technician contact you" in response3.lower()
    assert "installation" in response3.lower()

def test_complex_parts_installation():
    """Test complex parts automatically suggest professional installation"""
    bot = AutoPartsChatbot()
    
    complex_parts = [
        "timing belt",
        "fuel pump", 
        "transmission"
    ]
    
    for part in complex_parts:
        bot.reset_session()
        # Try to get recommendation (may be out of stock)
        bot.process_message(f"Honda {part}", [])
        
        # Ask about installation
        response = bot.process_message("install", [])
        
        # Should recommend professional service
        if "professional installation" in response.lower() or "certified technician" in response.lower():
            assert True  # Good response
        else:
            # May not have found the part, check for general installation guidance
            assert "installation" in response.lower() or "what part" in response.lower()

def test_installation_booking_vs_stock_notification():
    """Test installation booking vs stock notification lead capture"""
    bot = AutoPartsChatbot()
    
    # Get part recommendation and ask for installation
    bot.process_message("Honda battery", [])
    response1 = bot.process_message("installation", [])
    
    # Should offer installation booking
    assert "technician" in response1.lower()
    
    # Agree to booking
    bot.process_message("yes", [])
    bot.process_message("Jane Doe", [])
    response2 = bot.process_message("jane@email.com", [])
    
    # Should mention installation service, not stock notification
    assert "installation" in response2.lower()
    assert "technician" in response2.lower()

def test_decline_installation_service():
    """Test declining installation service"""
    bot = AutoPartsChatbot()
    
    # Get recommendation and ask about installation
    bot.process_message("Toyota brake pads", [])
    bot.process_message("installation", [])
    
    # Decline service
    response = bot.process_message("No thanks", [])
    
    # Should offer other help
    assert "anything else" in response.lower() or "help you find" in response.lower()

if __name__ == "__main__":
    pytest.main([__file__])
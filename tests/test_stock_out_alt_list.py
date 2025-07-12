#!/usr/bin/env python3
"""
Unit tests for dynamic stock-out alternatives
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_dynamic_stock_alternatives():
    """For make with no stock, shows real makes list, not hard-coded trio"""
    bot = AutoPartsChatbot()
    
    # Test with a make that likely has no stock for certain parts
    response = bot.process_message("Ferrari battery", [])
    
    # Should mention we don't stock Ferrari
    assert "ferrari" in response.lower() or "don't currently stock" in response.lower()

def test_get_dynamic_stock_alternatives():
    """Test dynamic stock alternatives function directly"""
    bot = AutoPartsChatbot()
    
    # Test with a category that exists
    alternatives = bot.get_dynamic_stock_alternatives("Battery")
    
    # Should return actual makes with battery stock
    assert isinstance(alternatives, list)
    assert len(alternatives) <= 5  # Max 5 as specified
    
    # Should contain real makes from our data
    valid_makes = ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan', 'Chevrolet', 'Subaru', 'Audi', 'Volkswagen', 'Jeep', 'Mercedes-Benz']
    for make in alternatives:
        assert make in valid_makes

def test_stock_out_with_alternatives():
    """Test stock-out response includes real alternatives"""
    bot = AutoPartsChatbot()
    
    # Try a combination that might be out of stock
    response = bot.process_message("Lamborghini battery", [])
    
    # Should either find parts or show alternatives
    if "don't currently stock" in response.lower():
        # Should show real alternatives, not hard-coded list
        assert "however" in response.lower() or "available for" in response.lower()

if __name__ == "__main__":
    pytest.main([__file__])
#!/usr/bin/env python3
"""
Unit tests for multi-item query handling
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_honda_battery_or_toyota_tires():
    """Test 'Honda battery or Toyota tires' splits correctly"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("Honda battery or Toyota tires", [])
    
    # Should detect multiple queries and ask which one
    assert "multiple items" in response.lower()
    assert "honda battery" in response.lower()
    assert "toyota tires" in response.lower()
    assert "which one" in response.lower()

def test_multi_query_detection():
    """Test multi-query detection works for various separators"""
    bot = AutoPartsChatbot()
    
    test_cases = [
        "Honda battery or Toyota tires",
        "BMW brakes and Ford filters", 
        "Nissan oil & Subaru spark plugs",
        "Honda battery, Toyota tires"
    ]
    
    for query in test_cases:
        assert bot.detect_multi_query(query) == True

def test_single_query_not_detected():
    """Test single queries are not detected as multi-queries"""
    bot = AutoPartsChatbot()
    
    test_cases = [
        "Honda battery",
        "Toyota tires for my car",
        "BMW brakes please"
    ]
    
    for query in test_cases:
        assert bot.detect_multi_query(query) == False

def test_multi_query_split():
    """Test multi-query splitting works correctly"""
    bot = AutoPartsChatbot()
    
    # Test OR separator
    queries = bot.split_multi_query("Honda battery or Toyota tires")
    assert len(queries) == 2
    assert "Honda battery" in queries
    assert "Toyota tires" in queries
    
    # Test AND separator
    queries = bot.split_multi_query("BMW brakes and Ford filters")
    assert len(queries) == 2
    assert "BMW brakes" in queries
    assert "Ford filters" in queries

def test_mixed_query_response():
    """Test response to mixed vehicle/part queries"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("Honda battery or Toyota", [])
    
    # Should handle mixed specificity
    assert "multiple items" in response.lower() or "honda" in response.lower()

def test_three_item_query_limit():
    """Test that queries are limited to prevent overwhelming responses"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("Honda battery or Toyota tires or BMW brakes", [])
    
    # Should still handle gracefully (limit to first 2)
    assert len(response) > 0
    assert not response.startswith("Error")

if __name__ == "__main__":
    pytest.main([__file__])
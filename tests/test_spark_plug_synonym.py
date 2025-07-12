#!/usr/bin/env python3
"""
Unit tests for spark plug synonym mapping
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_spark_plugs_never_shows_ignition():
    """Test 'spark plugs' never surfaces 'ignition' in reply text"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("spark plugs", [])
    
    # Should not contain 'ignition' in user-facing text
    assert "ignition" not in response.lower()
    # Should contain 'spark' or 'plug'
    assert "spark" in response.lower() or "plug" in response.lower()

def test_spark_plug_singular():
    """Test 'spark plug' maps correctly"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("Honda spark plug", [])
    
    # Should not show 'ignition' to user
    assert "ignition" not in response.lower()
    # Should show spark plug related content
    assert "spark" in response.lower()

def test_plugs_synonym():
    """Test 'plugs' maps to spark plugs"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("Toyota plugs", [])
    
    # Should handle plugs as spark plugs
    assert "ignition" not in response.lower()

def test_category_normalization():
    """Test category normalization returns correct display names"""
    bot = AutoPartsChatbot()
    
    # Test spark plug normalization
    normalized = bot.normalize_category("spark plugs")
    assert normalized == "Spark Plugs"
    
    # Test display category
    display = bot.get_display_category("spark plugs")
    assert display == "spark plugs"
    assert "ignition" not in display.lower()

def test_honda_spark_plugs_search():
    """Test Honda spark plugs search uses correct category"""
    bot = AutoPartsChatbot()
    
    # Set up session
    bot.session_vehicle = "Honda"
    bot.session_part = "Spark Plugs"
    
    # Search should work with correct category
    parts = bot.search_parts("Honda", "Spark Plugs")
    # Should return results or empty list, not error
    assert isinstance(parts, list)

def test_synonym_mapping_consistency():
    """Test that all spark plug synonyms map consistently"""
    bot = AutoPartsChatbot()
    
    synonyms = ["spark plug", "spark plugs", "plugs"]
    
    for synonym in synonyms:
        normalized = bot.normalize_category(synonym)
        assert normalized == "Spark Plugs"
        
        display = bot.get_display_category(synonym)
        assert "ignition" not in display.lower()
        assert "spark" in display.lower()

if __name__ == "__main__":
    pytest.main([__file__])
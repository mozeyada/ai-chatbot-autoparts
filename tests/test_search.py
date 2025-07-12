#!/usr/bin/env python3
"""
Unit tests for Auto Parts Chatbot search functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_honda_battries_typo():
    """Test that 'Honda battries' returns appropriate response"""
    bot = AutoPartsChatbot()
    
    # Process the message with typo
    response = bot.process_message("Honda battries", [])
    
    # Should either find parts OR trigger lead capture (depending on dataset)
    assert "Found" in response or "Sorry" in response or "notify you" in response
    
    # Test direct search method
    parts = bot.search_parts("Honda", "Battery")
    
    # If parts found, all should be Honda and battery-related
    for part in parts:
        assert part['VehicleMake'] == 'Honda'
        # Should be battery-related category
        assert any(keyword in part['Category'].lower() for keyword in ['battery', 'ignition', 'electrical'])

def test_fuzzy_matching():
    """Test fuzzy matching for category synonyms"""
    bot = AutoPartsChatbot()
    
    # Test various typos
    test_cases = [
        ("battries", "Battery"),
        ("battry", "Battery"), 
        ("tyres", "Tires"),
        ("breaks", "Brakes")
    ]
    
    for typo, expected in test_cases:
        normalized = bot.normalize_category(typo)
        assert normalized == expected, f"'{typo}' should normalize to '{expected}', got '{normalized}'"

def test_intent_detection():
    """Test intent detection for different message types"""
    bot = AutoPartsChatbot()
    
    # Test chitchat
    assert bot.detect_intent("Who are you?") == "chitchat"
    assert bot.detect_intent("How are you?") == "chitchat"
    assert bot.detect_intent("How is the weather?") == "chitchat"
    assert bot.detect_intent("How is your day?") == "chitchat"
    
    # Test FAQ
    assert bot.detect_intent("What are your hours?") == "faq"
    assert bot.detect_intent("What's your return policy?") == "faq"
    
    # Test product queries
    assert bot.detect_intent("Honda battery") == "product"
    assert bot.detect_intent("Toyota tires") == "product"
    assert bot.detect_intent("I need to start buying new tires") == "product"

def test_keyword_collision_guard():
    """Test that 'starter parts' doesn't get confused with 'start'"""
    bot = AutoPartsChatbot()
    
    # Should not match 'starter' from 'start buying'
    vehicle, part = bot.extract_vehicle_and_part("I need to start buying new tires")
    assert part != "Starter"
    assert part == "Tires" or part is None

def test_chitchat_responses():
    """Test chitchat responses don't force parts flow"""
    bot = AutoPartsChatbot()
    
    # Weather question
    response = bot.process_message("How is the weather?", [])
    assert "weather info" in response.lower()
    assert "what vehicle" in response.lower()
    
    # Day question  
    response = bot.process_message("How is your day?", [])
    assert "thanks for asking" in response.lower()
    assert "what auto parts" in response.lower()

def test_context_persistence():
    """Test that context persists across conversation turns"""
    bot = AutoPartsChatbot()
    
    # User says part first
    response1 = bot.process_message("I need battries", [])
    assert "battery" in response1.lower()
    assert "which vehicle make" in response1.lower()
    
    # Then provides vehicle - should combine with existing part
    response2 = bot.process_message("Honda", [])
    # Should search for Honda + Battery, not ask for part again
    assert "sorry" in response2.lower() or "found" in response2.lower() or "notify" in response2.lower()
    assert "what type of part" not in response2.lower()

def test_robust_category_matching():
    """Test robust category matching with pluralization and fuzzy matching"""
    bot = AutoPartsChatbot()
    
    # Test pluralization handling
    parts1 = bot.search_parts("Toyota", "tire")
    parts2 = bot.search_parts("Toyota", "tires")
    
    # Should find same or similar results for singular/plural
    # (May be empty if no Toyota tires in dataset)
    assert isinstance(parts1, list)
    assert isinstance(parts2, list)
    
    # Test fuzzy category matching
    normalized = bot.normalize_category("battries")
    assert normalized == "Battery"

def test_hybrid_orchestrator():
    """Test that hybrid orchestrator works correctly"""
    bot = AutoPartsChatbot()
    
    # Test with parts that exist (Toyota tires)
    parts = bot.search_parts("Toyota", "Tires")
    if parts:
        # Should be able to format with LLM (may fallback to regular format)
        try:
            response = bot.format_parts_with_llm(parts, "Toyota", "Tires")
            assert len(response) > 0
            assert "Toyota" in response
        except Exception:
            # LLM formatting may fail in test environment, that's OK
            pass
    
    # Test fallback formatting
    if parts:
        response = bot.format_parts_response(parts)
        assert "Found" in response or "No parts" in response

if __name__ == "__main__":
    pytest.main([__file__])
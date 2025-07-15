"""
Data loading and saving functions for the Auto Parts Chatbot.
Handles loading products, FAQs, synonyms, install tips, install times, vehicle synonyms,
and managing leads file operations.
"""

import pandas as pd
import json
import csv
from datetime import datetime
from typing import Dict, List
import re


def load_products() -> pd.DataFrame:
    """Load products data from CSV file"""
    try:
        return pd.read_csv('data/products.csv')
    except FileNotFoundError:
        print("Error: products.csv not found. Please ensure data files exist.")
        return pd.DataFrame()


def load_faq() -> List[Dict]:
    """Load FAQ data from JSON file"""
    try:
        with open('data/faq.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load FAQ data: {e}")
        return []


def load_synonyms() -> Dict[str, str]:
    """Load category synonyms from CSV file"""
    synonyms = {}
    try:
        with open('data/category_synonyms.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Synonym' in row and 'CategoryName' in row:
                    synonyms[row['Synonym'].lower()] = row['CategoryName']
    except (FileNotFoundError, csv.Error) as e:
        print(f"Warning: Could not load synonyms: {e}")
    return synonyms


def load_install_tips() -> Dict:
    """Load installation tips from JSON file"""
    try:
        with open('data/install_tips.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load install tips: {e}")
        return {}


def load_install_times() -> Dict:
    """Load installation times from CSV file"""
    try:
        times_df = pd.read_csv('data/install_times.csv')
        return dict(zip(times_df['Category'], times_df['Minutes']))
    except (FileNotFoundError, pd.errors.EmptyDataError) as e:
        print(f"Warning: Could not load install times: {e}")
        return {}


def load_vehicle_synonyms() -> Dict[str, str]:
    """Load vehicle make synonyms for typo correction"""
    vehicle_synonyms = {
        'hond': 'Honda',
        'honda': 'Honda',
        'toyta': 'Toyota', 
        'toyota': 'Toyota',
        'ford': 'Ford',
        'nissan': 'Nissan',
        'bmw': 'BMW',
        'chevy': 'Chevrolet',
        'chevrolet': 'Chevrolet',
        'subaru': 'Subaru',
        'audi': 'Audi',
        'volkswagen': 'Volkswagen',
        'jeep': 'Jeep',
        'mercedes': 'Mercedes-Benz',
        'mercedes-benz': 'Mercedes-Benz'
    }
    return vehicle_synonyms


def init_leads_file(leads_file: str):
    """Initialize leads CSV file if it doesn't exist"""
    try:
        pd.read_csv(leads_file)
    except FileNotFoundError:
        try:
            df = pd.DataFrame(columns=['timestamp', 'name', 'phone', 'email', 'vehicle_make', 'part_category', 'message', 'service_requested'])
            df.to_csv(leads_file, index=False)
        except Exception as e:
            print(f"Warning: Could not create leads file: {e}")


def extract_contact_info(contact_text: str) -> tuple[str, str]:
    """Extract phone and email from contact text"""
    phone = ''
    email = ''
    
    if 'both' in contact_text.lower():
        return '', ''
    
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}|\d{10})', contact_text)
    if phone_match:
        phone = phone_match.group(1)
    
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', contact_text)
    if email_match:
        email = email_match.group(1)
    
    return phone, email


def save_lead_with_service(leads_file: str, name: str, contact: str, vehicle_make: str, part_category: str, original_message: str, service_requested: bool = False):
    """Save lead with service request flag"""
    try:
        phone, email = extract_contact_info(contact)
        
        lead_data = {
            'timestamp': datetime.now().isoformat(),
            'name': name,
            'phone': phone,
            'email': email,
            'vehicle_make': vehicle_make or '',
            'part_category': part_category or '',
            'message': original_message,
            'service_requested': service_requested
        }
        
        df = pd.read_csv(leads_file)
        new_row = pd.DataFrame([lead_data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(leads_file, index=False)
        
    except Exception as e:
        print(f"Warning: Could not save lead: {e}")


def save_lead(leads_file: str, name: str, contact: str, vehicle_make: str, part_category: str, original_message: str):
    """Backward compatibility wrapper for saving leads"""
    save_lead_with_service(leads_file, name, contact, vehicle_make, part_category, original_message, False)


def load_training_data(file_path: str) -> List[Dict]:
    """Load and preprocess training data for the NLP model"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return [
                {
                    "text": item["text"],
                    "label": item["label"]
                }
                for item in data
            ]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load training data: {e}")
        return []
"""
Intent detection, coreference resolution, and message processing logic for the Auto Parts Chatbot.
Handles natural language understanding, business logic, and conversation flow management.
"""

import requests
import json
import re
from typing import Dict, List, Tuple, Optional
from rapidfuzz import process, fuzz


def resolve_coref(text: str, ctx: dict) -> str:
    """Resolve coreference expressions using slot memory"""
    text_lower = text.lower().strip()
    
    COREF_PART = ["same part", "same one", "that part", "those", "it"]
    COREF_VEH = ["same car", "same make", "that car", "that make", "my car"]
    
    resolved = text
    
    # Resolve part coreferences
    if any(phrase in text_lower for phrase in COREF_PART) and ctx.get('part_category'):
        for phrase in COREF_PART:
            if phrase in text_lower:
                resolved = resolved.replace(phrase, ctx['part_category'])
                break
    
    # Resolve vehicle coreferences
    if any(phrase in text_lower for phrase in COREF_VEH) and ctx.get('vehicle_make'):
        resolved = f"{resolved} {ctx['vehicle_make']}"
    
    return resolved


def is_toxic(message: str) -> bool:
    """Check for toxic language using simple keyword detection"""
    toxic_keywords = [
        'fuck', 'shit', 'damn', 'bitch', 'asshole', 'stupid', 'idiot', 
        'moron', 'dumb', 'retard', 'hate', 'kill', 'die', 'rude', 'dump'
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in toxic_keywords)


def is_valid_name(name: str) -> bool:
    """Validate if input is a proper name, not a car make or other entity"""
    name = name.strip().lower()
    
    # Car makes that might be confused with names
    car_makes = ['honda', 'toyota', 'ford', 'bmw', 'nissan', 'chevrolet', 'subaru', 'audi', 'volkswagen', 'jeep', 'mercedes']
    
    # Common parts that might be confused
    parts = ['battery', 'tire', 'brake', 'oil', 'filter']
    
    # Too short or invalid patterns
    if len(name) < 2 or name.isdigit():
        return False
    
    # Check if it's a car make or part
    if name in car_makes or name in parts:
        return False
    
    # Basic name pattern (letters, spaces, common name characters)
    import re
    if re.match(r'^[a-zA-Z\s\-\']{2,30}$', name.strip()):
        return True
    
    return False


def extract_contact_details(message: str) -> dict:
    """Extract phone and email from a message"""
    import re
    
    phone_pattern = r'(\+?\d{1,3}[-.\s]?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}|\d{10})'
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    
    phone_match = re.search(phone_pattern, message)
    email_match = re.search(email_pattern, message)
    
    return {
        'phone': phone_match.group(1) if phone_match else None,
        'email': email_match.group(1) if email_match else None
    }


def normalize_category(category: str, synonyms: Dict[str, str]) -> str:
    """Normalize part category using synonyms and fuzzy matching"""
    if not category:
        return ""
    
    category_lower = category.lower().strip()
    
    # First check exact match in synonyms
    if category_lower in synonyms:
        return synonyms[category_lower]
    
    # Use fuzzy matching for typos with score cutoff
    synonym_keys = list(synonyms.keys())
    if synonym_keys:
        match = process.extractOne(category_lower, synonym_keys, scorer=fuzz.ratio, score_cutoff=70)
        if match:
            return synonyms[match[0]]
    
    # Fallback to cleaned original category
    cleaned = category_lower.title().replace(" parts", "").replace(" Parts", "")
    return cleaned


def normalize_make(make_input: str, vehicle_synonyms: Dict[str, str]) -> Optional[str]:
    """Normalize vehicle make with fuzzy matching for typos"""
    if not make_input:
        return None
    
    make_lower = make_input.lower().strip()
    
    # First check exact match in synonyms
    if make_lower in vehicle_synonyms:
        return vehicle_synonyms[make_lower]
    
    # Use fuzzy matching against synonym keys
    synonym_keys = list(vehicle_synonyms.keys())
    if synonym_keys:
        match = process.extractOne(make_lower, synonym_keys, scorer=fuzz.ratio, score_cutoff=70)
        if match:
            return vehicle_synonyms[match[0]]
    
    return None


def extract_vehicle_and_part(message: str, vehicle_synonyms: Dict[str, str], synonyms: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Extract vehicle make and part category from message"""
    message_lower = message.lower().strip()
    words = message_lower.split()
    
    # Extract vehicle make with fuzzy matching
    vehicle_make = None
    for word in words:
        if len(word) >= 4:
            normalized_make = normalize_make(word, vehicle_synonyms)
            if normalized_make:
                vehicle_make = normalized_make
                break
    
    # If no match with length >= 4, try exact matches for shorter words
    if not vehicle_make:
        for word in words:
            if word in vehicle_synonyms:
                vehicle_make = vehicle_synonyms[word]
                break
    
    # Check for unsupported but recognizable vehicle makes
    if not vehicle_make:
        unsupported_makes = ['ferrari', 'lamborghini', 'maserati', 'bugatti', 'mclaren', 'porsche', 'tesla']
        for word in words:
            if word.lower() in unsupported_makes:
                vehicle_make = word.title()
                break
    
    # Extract part category
    part_category = None
    
    # First try exact synonym matches
    for word in words:
        if word in synonyms:
            part_category = synonyms[word]
            break
    
    # Then try fuzzy matching for typos
    if not part_category:
        for word in words:
            if len(word) > 3:
                synonym_keys = list(synonyms.keys())
                if synonym_keys:
                    match = process.extractOne(word, synonym_keys, scorer=fuzz.ratio, score_cutoff=70)
                    if match:
                        part_category = synonyms[match[0]]
                        break
    
    # Guard against keyword collisions
    if part_category and 'starter' in part_category.lower():
        if not any(word == 'starter' for word in words):
            part_category = None
    
    return vehicle_make, part_category


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


def is_valid_phone(phone: str) -> bool:
    """Validate phone number format"""
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
    return bool(re.match(r'^\+?\d{10,}$', clean_phone))


def is_absurd_or_nonsense(message: str) -> bool:
    """Detect absurd or nonsensical requests"""
    message_lower = message.lower().strip()
    
    absurd_patterns = [
        r'eat.*battery', r'battery.*eat', r'hungry.*battery',
        r'are you.*gpt', r'are you.*chat', r'chat.*gpt',
        r'son.*playing', r'keyboard.*playing',
        r'my son.*wants', r'child.*wants.*eat'
    ]
    
    for pattern in absurd_patterns:
        if re.search(pattern, message_lower):
            return True
    
    if len(message_lower.strip()) < 3:
        return True
    
    if re.match(r'^[a-z]{8,}$', message_lower) and not any(word in message_lower for word in ['battery', 'tire', 'brake', 'honda', 'toyota']):
        return True
    
    return False


def detect_intent(message: str) -> str:
    """Detect user intent with proper priority and abuse detection"""
    message_lower = message.lower().strip()
    
    # Check for gibberish/unknown
    words = [w for w in message_lower.split() if len(w) > 1]
    if len(words) == 0:
        return 'unknown'
    
    # Toxic/Abuse detection (HIGHEST priority)
    if is_toxic(message):
        return 'abuse'
    
    # FAQ patterns (HIGH priority)
    faq_keywords = ['hours', 'open', 'close', 'return', 'refund', 'ship', 'payment', 'warranty', 'call', 'phone', 'contact', 'pay']
    if any(keyword in message_lower for keyword in faq_keywords):
        return 'faq'
    
    # Installation/Service intent
    install_keywords = ['install', 'installation', 'fit', 'fitting', 'replace', 'service', 'how long', 'appointment', 'booking', 'how do i put', 'do you do the install', 'how to install', 'install myself', 'when can i', 'arrange']
    if any(keyword in message_lower for keyword in install_keywords):
        return 'installation'
    
    # Car sales intent
    sales_keywords = ['buy a new car', 'purchase vehicle', 'new car', 'buying a car', 'car dealership']
    if any(keyword in message_lower for keyword in sales_keywords):
        return 'car_sales'
    
    # Callback request detection (HIGH priority)
    callback_patterns = ['call me', 'can you call', 'request.*call', 'phone me', 'ring me', 'callback']
    if any(re.search(pattern, message_lower) for pattern in callback_patterns):
        return 'callback_request'
    
    # Promotions/Specials detection (HIGH priority)
    promo_keywords = ['special', 'discount', 'deal', 'offer', 'promotion', 'sale', 'cheap', 'best price']
    if any(keyword in message_lower for keyword in promo_keywords):
        return 'promotions'
    
    # Enhanced Chitchat patterns (EXPANDED)
    chitchat_patterns = [
        'who are you', 'what are you', 'how are you', 'how is your day', 'how is you day',
        "how's your day", 'how is the weather', "how's the weather", "how's your week",
        'how is your week', 'how are things', "how's it going", "what's up", 'whats up',
        "what's the weather", 'weather', 'thanks', 'thank you', 'sorry',
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 
        'how is', 'nice to meet', 'goodbye', 'bye', 'good', 'great', 'awesome', 
        'nice', 'cool', 'perfect', 'excellent', 'not bad', 'sounds good', "that's fine", 'thats fine', 'no worries',
        'why are you', 'other questions', 'are you', 'chat gpt', 'chatgpt',
        # NEW: Friendship/tone requests
        'speak.*friend', 'talk.*friend', 'be.*friend', 'friend', 'cold', 'warm', 'friendly',
        'does that mean', 'teach me', 'will you teach', 'respect',
        # NEW: Emotional expressions
        'mean', 'other parts'
    ]
    
    # Check for exact word matches for short chitchat
    short_chitchat = ['ok', 'kk', 'hi', 'hey', 'thanks', 'bye', 'good', 'great', 'nice', 'cool', 'sorry', '?', 'hmm']
    if message_lower in short_chitchat:
        return 'chitchat'
    
    # Check for longer chitchat patterns
    if any(re.search(pattern, message_lower) for pattern in chitchat_patterns):
        return 'chitchat'
    
    # Product queries (check for vehicle or part mentions)
    # This should be checked after specific intents but before unknown
    return 'product'


def detect_multi_query(message: str) -> bool:
    """Detect if message contains multiple vehicle/part queries"""
    separators = [' or ', ' OR ', ' and ', ' AND ', ' & ', ', ']
    return any(sep in message for sep in separators)


def split_multi_query(message: str) -> List[str]:
    """Split multi-query message into individual queries"""
    parts = re.split(r'\s+(?:or|OR|and|AND|&|,)\s+', message)
    return [part.strip() for part in parts if part.strip()]


def search_parts(products_df, vehicle_make: str, part_category: str, synonyms: Dict[str, str]) -> List[Dict]:
    """Search for parts in the products database"""
    if products_df.empty:
        return []
    
    try:
        # Normalize category using fuzzy matching
        canon_category = normalize_category(part_category, synonyms)
        
        # Strategy 1: Exact match
        matches = products_df[
            (products_df['VehicleMake'].str.lower() == vehicle_make.lower()) &
            (products_df['Category'].str.lower() == canon_category.lower())
        ]
        
        # Strategy 2: Startswith match
        if matches.empty:
            matches = products_df[
                (products_df['VehicleMake'].str.lower() == vehicle_make.lower()) &
                (products_df['Category'].str.lower().str.startswith(canon_category.lower()))
            ]
        
        # Strategy 3: Category contains canon_category
        if matches.empty:
            matches = products_df[
                (products_df['VehicleMake'].str.lower() == vehicle_make.lower()) &
                (products_df['Category'].str.contains(canon_category, case=False, na=False))
            ]
        
        # Strategy 4: Fuzzy match on category names
        if matches.empty:
            vehicle_parts = products_df[
                products_df['VehicleMake'].str.lower() == vehicle_make.lower()
            ]
            
            if not vehicle_parts.empty:
                categories = vehicle_parts['Category'].unique()
                fuzzy_match = process.extractOne(canon_category.lower(), 
                                               [cat.lower() for cat in categories], 
                                               scorer=fuzz.ratio, score_cutoff=60)
                if fuzzy_match:
                    matched_category = categories[[cat.lower() for cat in categories].index(fuzzy_match[0])]
                    matches = vehicle_parts[
                        vehicle_parts['Category'].str.lower() == matched_category.lower()
                    ]
        
        return matches.to_dict('records')
    except Exception as e:
        print(f"Error in search_parts: {e}")
        return []


def check_faq(message: str, faq_data: List[Dict]) -> Optional[str]:
    """Check FAQ for matching answer"""
    message_lower = message.lower()
    
    best_match = None
    highest_score = 0
    
    for faq in faq_data:
        score = 0
        
        # Check keywords with priority weighting
        if 'keywords' in faq:
            for keyword in faq['keywords']:
                if keyword in message_lower:
                    weight = 2 if faq.get('priority') == 'high' else 1
                    score += weight
        
        # Direct question matching
        if any(word in faq['question'].lower() for word in message_lower.split()):
            score += 1
        
        if score > highest_score:
            highest_score = score
            best_match = faq
    
    return best_match['answer'] if best_match and highest_score > 0 else None


def call_groq_api(groq_api_key: str, message: str, context: str = "") -> str:
    """Call Groq API for LLM responses"""
    # Return mock response during testing
    if not groq_api_key:
        return "I'm here to help with auto parts. What can I find for you?"
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {groq_api_key}"
    }
    
    system_prompt = """You are a helpful auto parts store assistant. Be concise and professional (max 2 sentences). 
    Always guide customers to provide vehicle make and part type for searches.
    Available makes: Honda, Toyota, Ford, BMW, Nissan, Chevrolet, Subaru, Audi, Volkswagen, Jeep, Mercedes-Benz
    Common parts: battery, tires, brakes, oil, filters, spark plugs, suspension, lights"""
    
    if context:
        system_prompt += f"\n\n{context}"
    
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "max_tokens": 100,
        "temperature": 0.5
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return "I'm having trouble connecting right now. Please try again or contact us directly at our store."
    except Exception as e:
        return "I'm experiencing technical difficulties. Please contact our store directly for assistance."


def format_parts_with_llm(groq_api_key: str, parts: List[Dict], vehicle: str, part_type: str) -> str:
    """Use LLM to create friendly summary of search results"""
    if not parts:
        return "No parts found matching your criteria."
    
    # Sort by availability
    availability_order = {'In Stock': 0, 'Limited': 1, 'Out of Stock': 2}
    sorted_parts = sorted(parts, key=lambda x: availability_order.get(x['Availability'], 3))
    
    # Create compact JSON payload for LLM
    parts_data = []
    for part in sorted_parts[:3]:
        parts_data.append({
            "name": part['PartName'],
            "sku": part['SKU'],
            "price": part['Price'],
            "availability": part['Availability'],
            "vehicle": f"{part['VehicleMake']} {part['VehicleModel']}",
            "years": part['YearRange']
        })
    
    # LLM context with structured data
    context = f"""Customer searched for {part_type} parts for {vehicle}. 
    Found {len(sorted_parts)} results. Here are the top matches:
    {json.dumps(parts_data, indent=2)}
    
    Create a friendly, helpful response that:
    1. Mentions we found parts for their {vehicle}
    2. Highlights the best available option
    3. Includes key details (price, availability, SKU)
    4. Keeps it concise (2-3 sentences max)"""
    
    llm_response = call_groq_api(groq_api_key, f"Summarize these {part_type} parts for {vehicle}", context)
    
    # Add structured details after LLM summary
    details = "\n\n📋 **Details:**\n"
    for part in sorted_parts[:3]:
        availability = part['Availability']
        status_emoji = "✅" if availability == "In Stock" else "⚠️" if availability == "Limited" else "❌"
        details += f"{status_emoji} {part['PartName']} - SKU: {part['SKU']} | ${part['Price']} | {availability}\n"
    
    if len(sorted_parts) > 3:
        details += f"\n... and {len(sorted_parts) - 3} more available."
    
    return llm_response + details


def format_parts_response(parts: List[Dict]) -> str:
    """Fallback formatting without LLM"""
    if not parts:
        return "No parts found matching your criteria."
    
    # Sort by availability
    availability_order = {'In Stock': 0, 'Limited': 1, 'Out of Stock': 2}
    sorted_parts = sorted(parts, key=lambda x: availability_order.get(x['Availability'], 3))
    
    response = f"Found {len(sorted_parts)} part(s):\n\n"
    
    for part in sorted_parts[:5]:
        availability = part['Availability']
        status_emoji = "✅" if availability == "In Stock" else "⚠️" if availability == "Limited" else "❌"
        
        response += f"{status_emoji} **{part['PartName']}**\n"
        response += f"   SKU: {part['SKU']} | Price: ${part['Price']} | {availability}\n"
        response += f"   Fits: {part['VehicleMake']} {part['VehicleModel']} ({part['YearRange']})\n\n"
    
    if len(sorted_parts) > 5:
        response += f"... and {len(sorted_parts) - 5} more parts available.\n"
    
    return response
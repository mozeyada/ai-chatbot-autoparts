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
    if re.match(r'^[a-zA-Z\s\-\']{2,30}$', name.strip()):
        return True
    
    return False


def extract_contact_details(message: str) -> dict:
    """Extract phone and email from a message"""
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
    
    # Check common makes not in synonyms
    common_makes = {
        'hyundai': 'Hyundai', 'kia': 'Kia', 'mazda': 'Mazda', 'mitsubishi': 'Mitsubishi',
        'lexus': 'Lexus', 'acura': 'Acura', 'infiniti': 'Infiniti', 'volvo': 'Volvo'
    }
    if make_lower in common_makes:
        return common_makes[make_lower]
    
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
    
    # Common vehicle makes (expand beyond synonyms)
    all_makes = {
        'honda': 'Honda', 'toyota': 'Toyota', 'ford': 'Ford', 'bmw': 'BMW', 'nissan': 'Nissan',
        'chevrolet': 'Chevrolet', 'chevy': 'Chevrolet', 'subaru': 'Subaru', 'audi': 'Audi', 
        'volkswagen': 'Volkswagen', 'vw': 'Volkswagen', 'jeep': 'Jeep', 'mercedes': 'Mercedes-Benz',
        'hyundai': 'Hyundai', 'kia': 'Kia', 'mazda': 'Mazda', 'mitsubishi': 'Mitsubishi',
        'lexus': 'Lexus', 'acura': 'Acura', 'infiniti': 'Infiniti', 'volvo': 'Volvo'
    }
    
    # Check if the entire message is just a vehicle make
    if message_lower in all_makes:
        return all_makes[message_lower], None
    
    # Extract vehicle make
    vehicle_make = None
    for word in words:
        if word in all_makes:
            vehicle_make = all_makes[word]
            break
        elif word in vehicle_synonyms:
            vehicle_make = vehicle_synonyms[word]
            break
    
    # Common part patterns (expand beyond synonyms)
    part_patterns = {
        'battery': 'Battery', 'tire': 'Tires', 'tires': 'Tires', 'brake': 'Brakes', 'brakes': 'Brakes',
        'oil': 'Engine Oil', 'filter': 'Filters', 'filters': 'Filters', 'spark': 'Spark Plugs',
        'suspension': 'Suspension', 'light': 'Lighting', 'lights': 'Lighting', 'headlight': 'Lighting',
        'mirror': 'Accessories', 'mirrors': 'Accessories', 'bumper': 'Accessories', 'fender': 'Accessories',
        'windshield': 'Accessories', 'door': 'Accessories', 'window': 'Accessories',
        'rear': 'Accessories', 'front': 'Accessories', 'side': 'Accessories',
        'wiper': 'Accessories', 'wipers': 'Accessories', 'mat': 'Accessories', 'mats': 'Accessories',
        'seat': 'Accessories', 'seats': 'Accessories', 'cover': 'Accessories', 'covers': 'Accessories',
        'bulb': 'Lighting', 'bulbs': 'Lighting', 'lamp': 'Lighting', 'lamps': 'Lighting',
        'sensor': 'Electrical', 'sensors': 'Electrical', 'switch': 'Electrical', 'switches': 'Electrical'
    }
    
    # Extract part category
    part_category = None
    
    # Check for specific compound parts
    compound_parts = {
        'rear mirror': 'Accessories',
        'side mirror': 'Accessories',
        'front mirror': 'Accessories',
        'rear light': 'Lighting',
        'side light': 'Lighting',
        'front light': 'Lighting',
        'rear bumper': 'Accessories',
        'front bumper': 'Accessories',
        'side bumper': 'Accessories',
        'oil filter': 'Filters',
        'air filter': 'Filters',
        'fuel filter': 'Filters',
        'cabin filter': 'Filters',
        'spark plug': 'Spark Plugs'
    }
    
    # Check for compound parts in the full message
    for compound, category in compound_parts.items():
        if compound in message_lower:
            part_category = category
            break
    
    # If no match yet, check for adjacent words
    if not part_category:
        message_parts = message_lower.replace('-', ' ').split()
        for i, word in enumerate(message_parts):
            # Check compound parts like "rear mirror", "side mirror", etc.
            if word in ['rear', 'side', 'front'] and i + 1 < len(message_parts):
                next_word = message_parts[i + 1]
                if next_word in ['mirror', 'light', 'bumper']:
                    if next_word == 'mirror':
                        part_category = 'Accessories'
                    elif next_word == 'light':
                        part_category = 'Lighting'
                    else:
                        part_category = 'Accessories'
                    break
    
    # Single word part matching
    if not part_category:
        for word in words:
            if word in part_patterns:
                part_category = part_patterns[word]
                break
            elif word in synonyms:
                part_category = synonyms[word]
                break
    
    # Fuzzy matching as fallback
    if not part_category:
        for word in words:
            if len(word) > 3:
                synonym_keys = list(synonyms.keys())
                if synonym_keys:
                    match = process.extractOne(word, synonym_keys, scorer=fuzz.ratio, score_cutoff=70)
                    if match:
                        part_category = synonyms[match[0]]
                        break
    
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
    
    # Common greetings should not be flagged as nonsense
    common_greetings = ['hi', 'hey', 'hello', 'yo', 'hola']
    if message_lower in common_greetings:
        return False
    
    # Common auto parts should not be flagged as nonsense
    common_parts = ['battery', 'batteries', 'tire', 'tires', 'brake', 'brakes', 'oil', 'filter', 'filters', 
                    'spark', 'plugs', 'light', 'lights', 'mirror', 'mirrors', 'bumper', 'bumpers']
    
    # Check for common parts with fuzzy matching for typos
    for part in common_parts:
        if part in message_lower or fuzz.ratio(message_lower, part) > 80:
            return False
    
    absurd_patterns = [
        r'eat.*battery', r'battery.*eat', r'hungry.*battery',
        r'are you.*gpt', r'are you.*chat', r'chat.*gpt',
        r'son.*playing', r'keyboard.*playing',
        r'my son.*wants', r'child.*wants.*eat'
    ]
    
    for pattern in absurd_patterns:
        if re.search(pattern, message_lower):
            return True
    
    # Only flag very short messages that aren't common greetings
    if len(message_lower) < 2 and message_lower not in ['a', 'i', 'q']:
        return True
    
    if re.match(r'^[a-z]{8,}$', message_lower) and not any(word in message_lower for word in ['battery', 'tire', 'brake', 'honda', 'toyota']):
        return True
    
    return False


def is_negation(message: str) -> bool:
    """Detect negative responses"""
    message_lower = message.lower().strip()
    
    # Simple exact negations
    simple_negations = ['no', 'nope', 'no thanks', 'not now', 'no thank you', 'nah']
    if message_lower in simple_negations:
        return True
    
    # Negation at start of message
    if message_lower.startswith('no ') or message_lower.startswith('not '):
        return True
    
    # Common negative phrases
    negative_phrases = ['don\'t want', 'do not want', 'not interested', 'no need', 'not needed']
    if any(phrase in message_lower for phrase in negative_phrases):
        return True
    
    return False


def detect_intent(message: str, groq_api_key: str = None) -> str:
    """Detect user intent using a hybrid approach (rules + LLM)"""
    message_lower = message.lower().strip()
    
    # Fast path for simple cases
    # Toxic/abuse detection
    if is_toxic(message_lower):
        return 'abuse'
    
    # Nonsense/absurd detection
    if is_absurd_or_nonsense(message_lower):
        return 'nonsense'
    
    # Simple chitchat patterns for quick responses
    simple_chitchat = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay']
    if message_lower in simple_chitchat:
        return 'chitchat'
    
    # Try LLM-based intent detection for complex queries
    if groq_api_key and len(message.split()) > 2:
        try:
            system_prompt = """You are an auto parts store assistant. Classify the user's message into EXACTLY ONE of these intents:
            - product: User is asking about auto parts or mentioning a vehicle make/model
            - faq: User is asking about store policies, hours, location, etc.
            - installation: User is asking about installing parts or service
            - lead: User wants to be contacted or provide contact info
            - chitchat: General conversation, greetings, thanks
            - car_sales: User wants to buy a car (not parts)
            - promotions: User is asking about deals or discounts
            - unknown: Can't determine intent
            
            Reply with ONLY the intent name, nothing else."""
            
            llm_response = call_groq_api(groq_api_key, message, system_prompt)
            intent = llm_response.strip().lower()
            
            # Validate the intent
            valid_intents = ['product', 'faq', 'installation', 'lead', 'chitchat', 'car_sales', 'promotions', 'unknown']
            if intent in valid_intents:
                print(f"DEBUG: LLM detected intent: {intent}")
                return intent
        except Exception as e:
            print(f"LLM intent detection failed: {e}")
    
    # Fallback to rule-based detection
    # FAQ patterns
    faq_patterns = [
        'hours', 'open', 'close', 'location', 'address', 'phone', 'contact',
        'return', 'warranty', 'policy', 'shipping', 'delivery', 'payment'
    ]
    if any(pattern in message_lower for pattern in faq_patterns):
        return 'faq'
    
    # Installation patterns
    install_patterns = [
        'install', 'installation', 'how to', 'diy', 'service', 'appointment',
        'book', 'schedule', 'mechanic', 'professional'
    ]
    if any(pattern in message_lower for pattern in install_patterns):
        return 'installation'
    
    # Lead capture patterns
    lead_patterns = [
        'call me', 'callback', 'contact me', 'reach out', 'get back',
        'phone number', 'email', '@', 'notify', 'let me know', 'call',
        'contact', 'reach', 'get in touch', 'get a hold', 'call back'
    ]
    
    # Check for lead patterns with higher priority
    if any(pattern in message_lower for pattern in lead_patterns):
        # Special case for "call" to avoid false positives
        if 'call' in message_lower and len(message_lower.split()) <= 3:
            return 'lead'
        elif 'call' not in message_lower or ('call' in message_lower and any(word in message_lower for word in ['me', 'us', 'back'])):
            return 'lead'
    
    # Chitchat patterns
    chitchat_patterns = [
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'how are you',
        'thanks', 'thank you', 'weather', 'who are you', 'what are you',
        'friend', 'cold', 'warm', 'does that mean', 'doing good', 'am good', 'fine'
    ]
    if any(pattern in message_lower for pattern in chitchat_patterns):
        return 'chitchat'
    
    # Car sales (out of scope)
    car_sales_patterns = [
        'buy car', 'new car', 'used car', 'car dealer', 'car lot',
        'financing', 'lease', 'trade in'
    ]
    if any(pattern in message_lower for pattern in car_sales_patterns):
        return 'car_sales'
    
    # Promotions patterns
    promo_patterns = [
        'special', 'deal', 'discount', 'sale', 'promotion', 'offer',
        'coupon', 'price', 'cheap', 'best price'
    ]
    if any(pattern in message_lower for pattern in promo_patterns):
        return 'promotions'
    
    # Product patterns (vehicle makes and parts)
    vehicle_makes = [
        'honda', 'toyota', 'ford', 'bmw', 'nissan', 'chevrolet', 'chevy',
        'subaru', 'audi', 'volkswagen', 'vw', 'jeep', 'mercedes', 'hyundai',
        'kia', 'mazda', 'mitsubishi', 'lexus', 'acura', 'infiniti', 'volvo'
    ]
    part_names = [
        'battery', 'tire', 'tires', 'brake', 'brakes', 'oil', 'filter',
        'spark', 'suspension', 'light', 'lights', 'mirror', 'bumper', 'rear',
        'front', 'side', 'wiper', 'sensor', 'bulb', 'lamp'
    ]
    
    has_vehicle = any(make in message_lower for make in vehicle_makes)
    has_part = any(part in message_lower for part in part_names)
    
    if has_vehicle or has_part:
        return 'product'
    
    # Check for compound parts like "rear mirror"
    compound_parts = ['rear mirror', 'side mirror', 'front mirror', 'rear light', 'side light']
    if any(part in message_lower for part in compound_parts):
        return 'product'
    
    return 'unknown'


def enhanced_intent_detection(message: str, context: dict, groq_api_key: str) -> dict:
    """Enhanced intent detection with chain-of-thought reasoning"""
    # Fast path for simple cases
    message_lower = message.lower().strip()
    
    # Handle simple cases without LLM
    if is_toxic(message_lower):
        return {
            "primary_intent": "abuse",
            "secondary_intent": None,
            "entities": {},
            "confidence": 0.9,
            "reasoning": "Detected toxic language"
        }
    
    if is_absurd_or_nonsense(message_lower):
        return {
            "primary_intent": "nonsense",
            "secondary_intent": None,
            "entities": {},
            "confidence": 0.9,
            "reasoning": "Detected nonsensical query"
        }
    
    # Simple chitchat patterns for quick responses
    simple_chitchat = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay']
    if message_lower in simple_chitchat:
        return {
            "primary_intent": "chitchat",
            "secondary_intent": None,
            "entities": {},
            "confidence": 0.9,
            "reasoning": "Simple greeting or acknowledgment"
        }
    
    # Use LLM for complex queries
    system_prompt = """You are an auto parts store assistant analyzing customer queries.
    
    First, identify ALL entities in the query:
    - Vehicle makes (Honda, Toyota, etc.)
    - Part categories (battery, tires, etc.)
    - Service requests (installation, warranty, etc.)
    - Contact information (phone, email, etc.)
    
    Then, determine the PRIMARY intent from these categories:
    - product: Customer wants to find specific auto parts
    - faq: Customer is asking about store policies or information
    - installation: Customer needs help with part installation
    - lead: Customer wants to be contacted or provide contact info
    - chitchat: General conversation, greetings, thanks
    - car_sales: Customer wants to buy a car (not parts)
    - promotions: Customer is asking about deals or discounts
    - unknown: Can't determine intent
    
    Finally, identify any SECONDARY intents that may be present.
    
    Format your response as JSON:
    {
      "primary_intent": "intent_name",
      "secondary_intent": "intent_name",
      "entities": {
        "vehicle_make": "detected_make",
        "part_category": "detected_part",
        "service_type": "detected_service"
      },
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }
    """
    
    try:
        # Include context in the user message for better understanding
        context_str = ""
        if context.get('vehicle_make'):
            context_str += f"Previously mentioned vehicle: {context['vehicle_make']}. "
        if context.get('part_category'):
            context_str += f"Previously mentioned part: {context['part_category']}. "
        
        enhanced_message = f"{context_str}User message: {message}"
        
        # Call LLM with enhanced prompt
        llm_response = call_groq_api(groq_api_key, enhanced_message, system_prompt)
        
        # Parse JSON response
        try:
            result = json.loads(llm_response)
            print(f"DEBUG: Enhanced intent detection: {result}")
            return result
        except json.JSONDecodeError:
            print(f"Failed to parse LLM response as JSON: {llm_response}")
            # Fallback to basic intent detection
            basic_intent = detect_intent(message, groq_api_key)
            return {
                "primary_intent": basic_intent,
                "secondary_intent": None,
                "entities": {},
                "confidence": 0.5,
                "reasoning": "Fallback to basic detection"
            }
            
    except Exception as e:
        print(f"Enhanced intent detection failed: {e}")
        # Fallback to basic intent detection
        basic_intent = detect_intent(message, groq_api_key)
        return {
            "primary_intent": basic_intent,
            "secondary_intent": None,
            "entities": {},
            "confidence": 0.5,
            "reasoning": "Error in LLM processing"
        }


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
        print("Warning: No GROQ_API_KEY provided. Using mock response.")
        return "I'm here to help with auto parts. What can I find for you?"
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {groq_api_key}"
    }
    
    # If context is provided, use it as the system prompt
    if context:
        system_prompt = context
    else:
        system_prompt = """You are a helpful auto parts store assistant. Be concise and professional (max 2 sentences). 
        Always guide customers to provide vehicle make and part type for searches.
        Available makes: Honda, Toyota, Ford, BMW, Nissan, Chevrolet, Subaru, Audi, Volkswagen, Jeep, Mercedes-Benz, Hyundai, Kia
        Common parts: battery, tires, brakes, oil, filters, spark plugs, suspension, lights, mirrors, bumpers
        Accessories include: mirrors, bumpers, trim pieces, floor mats, etc.
        Lighting includes: headlights, tail lights, turn signals, etc."""
    
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "max_tokens": 150,
        "temperature": 0.3
    }
    
    try:
        print(f"Calling Groq API with message: {message[:30]}...")
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"Groq API response received: {content[:30]}...")
            return content
        else:
            print(f"Groq API error: {response.status_code} - {response.text}")
            return "I'm having trouble connecting right now. Please try again or contact us directly at our store."
    except Exception as e:
        print(f"Groq API exception: {str(e)}")
        return "I'm experiencing technical difficulties. Please contact our store directly for assistance."


def generate_contextual_response(groq_api_key: str, message: str, intent: str, context: dict, parts_data=None) -> str:
    """Generate natural responses with full context awareness"""
    # Build rich context for the LLM
    context_str = ""
    
    # Add conversation context
    if context.get('vehicle_make'):
        context_str += f"Customer's vehicle: {context['vehicle_make']}. "
    if context.get('part_category'):
        context_str += f"Customer is interested in: {context['part_category']}. "
    
    # Add intent-specific context
    if intent == 'product' and parts_data:
        # Format parts data for the LLM
        parts_summary = []
        for part in parts_data[:3]:
            parts_summary.append({
                "name": part['PartName'],
                "sku": part['SKU'],
                "price": part['Price'],
                "availability": part['Availability']
            })
        context_str += f"Available parts: {json.dumps(parts_summary)}. "
    
    # Add entity memory if available
    if context.get('entity_memory'):
        for key, value in context['entity_memory'].items():
            context_str += f"{key}: {value}. "
    
    # Create system prompt based on intent
    if intent == 'product':
        system_prompt = f"""You are a helpful auto parts store assistant. 
        
        CONTEXT: {context_str}
        
        Create a friendly, conversational response about the available parts.
        - Highlight the best option first
        - Mention price and availability
        - Keep your response concise (2-3 sentences)
        - End with a question about installation if appropriate
        
        DO NOT include SKU numbers in your main response."""
    
    elif intent == 'installation':
        system_prompt = f"""You are a helpful auto parts store assistant.
        
        CONTEXT: {context_str}
        
        Create a friendly response about installation services:
        - Mention the estimated time for installation
        - Offer both DIY guidance and professional service
        - Keep your response concise (2-3 sentences)
        - End with a question about booking an appointment
        
        DO NOT make up any specific times or prices."""
    
    else:
        system_prompt = f"""You are a helpful auto parts store assistant.
        
        CONTEXT: {context_str}
        
        Create a friendly, conversational response that:
        - Directly addresses the customer's question
        - Uses the context information appropriately
        - Keeps your response concise (2-3 sentences)
        - Maintains a helpful, professional tone
        
        DO NOT make up any information not provided in the context."""
    
    # Call LLM with enhanced prompt
    return call_groq_api(groq_api_key, message, system_prompt)


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
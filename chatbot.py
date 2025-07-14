import gradio as gr
import pandas as pd
import json
import csv
import requests
from datetime import datetime
import re
import os
from typing import Dict, List, Tuple, Optional
from rapidfuzz import process, fuzz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AutoPartsChatbot:
    def __init__(self):
        try:
            self.products_df = pd.read_csv('data/products.csv')
        except FileNotFoundError:
            print("Error: products.csv not found. Please ensure data files exist.")
            self.products_df = pd.DataFrame()
        
        self.faq_data = self.load_faq()
        self.synonyms = self.load_synonyms()
        self.vehicle_synonyms = self.load_vehicle_synonyms()
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is required. Please set it in your .env file or environment.")
        self.leads_file = 'data/leads.csv'
        self.init_leads_file()
        self.install_tips = self.load_install_tips()
        self.install_times = self.load_install_times()
        self.pending_install_lead = False
        self.pending_action = None
        # Session state for conversation context
        self.session_vehicle = None
        self.session_part = None
        self.awaiting_lead_capture = False
        self.lead_capture_step = None  # 'name', 'contact', or None
        self.lead_name = None
        self.conversation_handled = False
        self.invalid_turns = 0
        self.help_shown = False
        self.last_response_type = None
        
        # Advanced conversation context system
        # Enhanced context memory
        self.slot_memory = {
            'vehicle_make': None,
            'part_category': None,
            'last_sku': None,
            'last_search_successful': False
        }
        self.last_recommended_part = None
        self.oops_count = 0
        self.help_shown = False
        self.clf_conf = 0.0
        self.consecutive_fallbacks = 0
        self.turns_since_valid_context = 0
        self.pending_part_category = None
        self.pending_part_count = 0
    
    def reset_session(self):
        """Reset conversation session"""
        self.session_vehicle = None
        self.session_part = None
        self.awaiting_lead_capture = False
        self.lead_capture_step = None
        self.lead_name = None
        self.conversation_handled = False
        self.invalid_turns = 0
        self.help_shown = False
        self.last_response_type = None
        
        # Clear enhanced context memory
        self.slot_memory = {
            'vehicle_make': None,
            'part_category': None,
            'last_sku': None,
            'last_search_successful': False
        }
        self.last_recommended_part = None
        self.pending_install_lead = False
        self.oops_count = 0
        self.help_shown = False
        self.consecutive_fallbacks = 0
        self.turns_since_valid_context = 0
        self.pending_part_category = None
        self.pending_part_count = 0
        
    def resolve_coref(self, text: str, ctx: dict) -> str:
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
    
    def is_toxic(self, message: str) -> bool:
        """Check for toxic language using simple keyword detection"""
        toxic_keywords = [
            'fuck', 'shit', 'damn', 'bitch', 'asshole', 'stupid', 'idiot', 
            'moron', 'dumb', 'retard', 'hate', 'kill', 'die'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in toxic_keywords)
    
    def get_dynamic_stock_alternatives(self, part_category: str) -> List[str]:
        """Get real makes with inventory for given category"""
        if self.products_df.empty:
            return []
        
        canon_category = self.normalize_category(part_category)
        available_makes = self.products_df[
            (self.products_df['Category'].str.lower() == canon_category.lower()) &
            (self.products_df['Availability'].isin(['In Stock', 'Limited']))
        ]['VehicleMake'].unique().tolist()
        
        return available_makes[:5]  # Return first 5 makes with stock
    
    def load_faq(self) -> List[Dict]:
        try:
            with open('data/faq.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load FAQ data: {e}")
            return []
    
    def load_synonyms(self) -> Dict[str, str]:
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
    
    def load_install_tips(self) -> Dict:
        try:
            with open('data/install_tips.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load install tips: {e}")
            return {}
    
    def load_install_times(self) -> Dict:
        try:
            times_df = pd.read_csv('data/install_times.csv')
            return dict(zip(times_df['Category'], times_df['Minutes']))
        except (FileNotFoundError, pd.errors.EmptyDataError) as e:
            print(f"Warning: Could not load install times: {e}")
            return {}
    
    def get_available_makes(self) -> List[str]:
        """Get available vehicle makes from products data"""
        if self.products_df.empty:
            return ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan', 'Chevrolet', 'Subaru', 'Audi', 'Volkswagen', 'Jeep', 'Mercedes-Benz']
        return sorted(self.products_df['VehicleMake'].unique().tolist())
    
    def load_vehicle_synonyms(self) -> Dict[str, str]:
        """Load vehicle make synonyms for typo correction"""
        # Common typos and abbreviations (avoid short ambiguous words)
        vehicle_synonyms = {
            'hond': 'Honda',
            'honda': 'Honda',
            'toyta': 'Toyota', 
            'toyota': 'Toyota',
            'ford': 'Ford',  # Keep but handle carefully
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
    
    def init_leads_file(self):
        try:
            pd.read_csv(self.leads_file)
        except FileNotFoundError:
            try:
                df = pd.DataFrame(columns=['timestamp', 'name', 'phone', 'email', 'vehicle_make', 'part_category', 'message'])
                df.to_csv(self.leads_file, index=False)
            except Exception as e:
                print(f"Warning: Could not create leads file: {e}")
    
    def normalize_category(self, category: str) -> str:
        if not category:
            return ""
        
        category_lower = category.lower().strip()
        
        # First check exact match in synonyms
        if category_lower in self.synonyms:
            canon_name = self.synonyms[category_lower]
            # Return canonical category name (already clean)
            return canon_name
        
        # Use fuzzy matching for typos with score cutoff
        synonym_keys = list(self.synonyms.keys())
        if synonym_keys:
            match = process.extractOne(category_lower, synonym_keys, scorer=fuzz.ratio, score_cutoff=70)
            if match:
                canon_name = self.synonyms[match[0]]
                # Return canonical category name (already clean)
                return canon_name
        
        # Fallback to cleaned original category
        cleaned = category_lower.title().replace(" parts", "").replace(" Parts", "")
        return cleaned
    
    def get_available_categories_for_vehicle(self, vehicle_make: str) -> List[str]:
        """Get list of available part categories for a specific vehicle"""
        if self.products_df.empty:
            return []
        
        vehicle_parts = self.products_df[self.products_df['VehicleMake'].str.lower() == vehicle_make.lower()]
        categories = vehicle_parts['Category'].unique().tolist()
        
        # Convert to display names
        display_categories = []
        for cat in categories:
            display_name = self.get_display_category(cat)
            if display_name not in display_categories:
                display_categories.append(display_name)
        
        return sorted(display_categories)
    
    def get_install_time_minutes(self, part_category: str) -> int:
        """Get installation time in minutes from CSV data"""
        part_lower = part_category.lower()
        
        # Check install times from CSV
        for category, minutes in self.install_times.items():
            if category.lower() in part_lower or part_lower in category.lower():
                return minutes
        
        # Fallback logic
        if 'battery' in part_lower:
            return 30
        elif 'tire' in part_lower:
            return 45
        elif 'brake' in part_lower:
            return 90
        elif 'light' in part_lower:
            return 20
        else:
            return 45  # Default
    
    def handle_installation_request(self, message: str) -> str:
        """Handle installation-related queries with context preservation"""
        message_lower = message.lower()
        
        # Check current session context first
        if self.session_vehicle and self.session_part:
            minutes = self.get_install_time_minutes(self.session_part)
            response = f"For {self.session_vehicle} {self.session_part.lower()} installation, the estimated time is {minutes} minutes.\n\n"
            response += "Would you like to book an appointment or get a quote? I can arrange professional installation."
            self.pending_install_lead = True
            return response
        
        # Check slot memory context
        elif self.slot_memory['vehicle_make'] and self.slot_memory['part_category']:
            vehicle = self.slot_memory['vehicle_make']
            part = self.slot_memory['part_category']
            minutes = self.get_install_time_minutes(part)
            response = f"For {vehicle} {part.lower()} installation, the estimated time is {minutes} minutes.\n\n"
            response += "Would you like to book an appointment or get a quote?"
            self.pending_install_lead = True
            return response
        
        # Generic installation query without context
        return "I'd be happy to help with installation! What part are you looking to install? I can provide timing estimates and arrange professional installation."
    
    def get_display_category(self, category: str) -> str:
        """Get user-friendly display name for category"""
        canon = self.normalize_category(category)
        
        # Map internal categories to user-friendly names
        display_map = {
            'Spark Plugs': 'spark plugs',
            'Electrical': 'electrical parts',
            'Engine Oil': 'engine oil',
            'Fuel System': 'fuel system parts',
            'Accessories': 'accessories',
            'Lighting': 'lights',
            'Performance': 'performance parts'
        }
        
        return display_map.get(canon, canon.lower())
    
    def normalize_make(self, make_input: str) -> Optional[str]:
        """Normalize vehicle make with fuzzy matching for typos"""
        if not make_input:
            return None
        
        make_lower = make_input.lower().strip()
        
        # First check exact match in synonyms
        if make_lower in self.vehicle_synonyms:
            return self.vehicle_synonyms[make_lower]
        
        # Use fuzzy matching against synonym keys (includes typos)
        synonym_keys = list(self.vehicle_synonyms.keys())
        if synonym_keys:
            match = process.extractOne(make_lower, synonym_keys, 
                                    scorer=fuzz.ratio, score_cutoff=70)
            if match:
                return self.vehicle_synonyms[match[0]]
        
        return None
    
    def detect_multi_query(self, message: str) -> bool:
        """Detect if message contains multiple vehicle/part queries"""
        separators = [' or ', ' OR ', ' and ', ' AND ', ' & ', ', ']
        return any(sep in message for sep in separators)
    
    def split_multi_query(self, message: str) -> List[str]:
        """Split multi-query message into individual queries"""
        import re
        # Split on common separators
        parts = re.split(r'\s+(?:or|OR|and|AND|&|,)\s+', message)
        return [part.strip() for part in parts if part.strip()]
    
    def extract_vehicle_and_part(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        message_lower = message.lower().strip()
        words = message_lower.split()
        
        # Extract vehicle make with fuzzy matching (skip very short words)
        vehicle_make = None
        for word in words:
            if len(word) >= 4:  # Skip short words like "my", "for", "the"
                normalized_make = self.normalize_make(word)
                if normalized_make:
                    vehicle_make = normalized_make
                    break
        
        # If no match with length >= 4, try exact matches for shorter words
        if not vehicle_make:
            for word in words:
                if word in self.vehicle_synonyms:
                    vehicle_make = self.vehicle_synonyms[word]
                    break
        
        # Also check for unsupported but recognizable vehicle makes
        if not vehicle_make:
            unsupported_makes = ['ferrari', 'lamborghini', 'maserati', 'bugatti', 'mclaren', 'porsche', 'tesla']
            for word in words:
                if word.lower() in unsupported_makes:
                    vehicle_make = word.title()  # Return as-is for unsupported make handling
                    break
        
        # Extract part category with improved matching
        part_category = None
        
        # First try exact synonym matches
        for word in words:
            if word in self.synonyms:
                part_category = self.synonyms[word]
                break
        
        # Then try fuzzy matching for typos
        if not part_category:
            for word in words:
                if len(word) > 3:  # Skip very short words
                    synonym_keys = list(self.synonyms.keys())
                    if synonym_keys:
                        match = process.extractOne(word, synonym_keys, scorer=fuzz.ratio, score_cutoff=70)
                        if match:
                            part_category = self.synonyms[match[0]]
                            break
        
        # Guard against keyword collisions (e.g., "starter parts" -> "start")
        if part_category and 'starter' in part_category.lower():
            # Only match if "starter" appears as whole word, not substring
            if not any(word == 'starter' for word in words):
                part_category = None
        
        return vehicle_make, part_category
    
    def search_parts(self, vehicle_make: str, part_category: str) -> List[Dict]:
        if self.products_df.empty:
            return []
        
        try:
            # Normalize category using fuzzy matching
            canon_category = self.normalize_category(part_category)
            
            # Strategy 1: Exact match
            matches = self.products_df[
                (self.products_df['VehicleMake'].str.lower() == vehicle_make.lower()) &
                (self.products_df['Category'].str.lower() == canon_category.lower())
            ]
            
            # Strategy 2: Startswith match (handles pluralization)
            if matches.empty:
                matches = self.products_df[
                    (self.products_df['VehicleMake'].str.lower() == vehicle_make.lower()) &
                    (self.products_df['Category'].str.lower().str.startswith(canon_category.lower()))
                ]
            
            # Strategy 3: Category contains canon_category
            if matches.empty:
                matches = self.products_df[
                    (self.products_df['VehicleMake'].str.lower() == vehicle_make.lower()) &
                    (self.products_df['Category'].str.contains(canon_category, case=False, na=False))
                ]
            
            # Strategy 4: Fuzzy match on category names
            if matches.empty:
                vehicle_parts = self.products_df[
                    self.products_df['VehicleMake'].str.lower() == vehicle_make.lower()
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
    
    def detect_intent(self, message: str) -> str:
        """Detect user intent with proper priority after lead capture"""
        message_lower = message.lower().strip()
        
        # Check for gibberish/unknown (very short or meaningless)
        words = [w for w in message_lower.split() if len(w) > 1]
        if len(words) == 0:
            return 'unknown'
        
        # FAQ patterns (HIGHEST priority - always check first)
        faq_keywords = ['hours', 'open', 'close', 'return', 'refund', 'ship', 'payment', 'warranty', 'call', 'phone', 'contact', 'pay']
        if any(keyword in message_lower for keyword in faq_keywords):
            return 'faq'
        
        # Installation/Service intent (HIGH priority)
        install_keywords = ['install', 'installation', 'fit', 'fitting', 'replace', 'service', 'how long', 'appointment', 'booking', 'how do i put', 'do you do the install', 'how to install', 'install myself', 'when can i']
        if any(keyword in message_lower for keyword in install_keywords):
            return 'installation'
        
        # Car sales intent (out of scope)
        sales_keywords = ['buy a new car', 'purchase vehicle', 'new car', 'buying a car', 'car dealership']
        if any(keyword in message_lower for keyword in sales_keywords):
            return 'car_sales'
        
        # Chitchat patterns (HIGH priority - before lead capture)
        chitchat_patterns = [
            'who are you', 'what are you', 'how are you', 'how is your day', 'how is you day',
            'how\'s your day', 'how is the weather', 'how\'s the weather', 'how\'s your week',
            'how is your week', 'how are things', 'how\'s it going', 'what\'s up', 'whats up',
            'what\'s the weather', 'weather', 'thanks', 'thank you',
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 
            'how is', 'nice to meet', 'goodbye', 'bye', 'good', 'great', 'awesome', 
            'nice', 'cool', 'perfect', 'excellent', 'not bad', 'sounds good', 'that\'s fine', 'thats fine', 'no worries'
        ]
        
        # Check for exact word matches for short chitchat
        short_chitchat = ['ok', 'kk', 'hi', 'hey', 'thanks', 'bye', 'good', 'great', 'nice', 'cool']
        if message_lower in short_chitchat:
            return 'chitchat'
        
        # Check for longer chitchat patterns
        if any(pattern in message_lower for pattern in chitchat_patterns):
            return 'chitchat'
        
        # Product queries (HIGH priority - before lead capture)
        vehicle, part = self.extract_vehicle_and_part(message)
        if vehicle or part:
            return 'product'
        
        # Lead capture patterns (LOWER priority - only if actively in lead flow)
        if self.awaiting_lead_capture or self.lead_capture_step or self.pending_install_lead:
            # Check for installation booking responses
            if self.pending_install_lead and any(word in message_lower for word in ['yes', 'ok', 'sure', 'book', 'arrange', 'contact']):
                return 'lead'
            elif self.awaiting_lead_capture or self.lead_capture_step:
                return 'lead'
        
        # If no meaningful content found
        return 'unknown'
    
    def check_faq(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        
        # Enhanced FAQ matching with modern structure
        best_match = None
        highest_score = 0
        
        for faq in self.faq_data:
            score = 0
            
            # Check keywords with priority weighting
            if 'keywords' in faq:
                for keyword in faq['keywords']:
                    if keyword in message_lower:
                        # Higher score for high-priority FAQs
                        weight = 2 if faq.get('priority') == 'high' else 1
                        score += weight
            
            # Direct question matching
            if any(word in faq['question'].lower() for word in message_lower.split()):
                score += 1
            
            if score > highest_score:
                highest_score = score
                best_match = faq
        
        return best_match['answer'] if best_match and highest_score > 0 else None
    
    def extract_contact_info(self, contact_text: str) -> tuple[str, str]:
        """Extract phone and email from contact text"""
        phone = ''
        email = ''
        
        # Handle "both" or combined responses
        if 'both' in contact_text.lower():
            return '', ''  # Will trigger re-ask
        
        # Extract phone number patterns
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}|\d{10})', contact_text)
        if phone_match:
            phone = phone_match.group(1)
        
        # Extract email patterns
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', contact_text)
        if email_match:
            email = email_match.group(1)
        
        return phone, email
    
    def save_lead_with_service(self, name: str, contact: str, vehicle_make: str, part_category: str, original_message: str, service_requested: bool = False):
        try:
            phone, email = self.extract_contact_info(contact)
            
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
            
            df = pd.read_csv(self.leads_file)
            new_row = pd.DataFrame([lead_data])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(self.leads_file, index=False)
            
            # CRITICAL: Clear ALL lead capture state after successful save
            self.awaiting_lead_capture = False
            self.lead_capture_step = None
            self.lead_name = None
            self.conversation_handled = True
            self.last_response_type = None
            
        except Exception as e:
            print(f"Warning: Could not save lead: {e}")
    
    def save_lead(self, name: str, contact: str, vehicle_make: str, part_category: str, original_message: str):
        """Backward compatibility wrapper"""
        self.save_lead_with_service(name, contact, vehicle_make, part_category, original_message, False)
    
    def call_groq_api(self, message: str, context: str = "") -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_api_key}"
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
    
    def format_parts_with_llm(self, parts: List[Dict], vehicle: str, part_type: str) -> str:
        """Use LLM to create friendly summary of search results"""
        if not parts:
            return "No parts found matching your criteria."
        
        # Sort by availability
        availability_order = {'In Stock': 0, 'Limited': 1, 'Out of Stock': 2}
        sorted_parts = sorted(parts, key=lambda x: availability_order.get(x['Availability'], 3))
        
        # Create compact JSON payload for LLM
        parts_data = []
        for part in sorted_parts[:3]:  # Limit to top 3 for LLM
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
        
        llm_response = self.call_groq_api(f"Summarize these {part_type} parts for {vehicle}", context)
        
        # Add structured details after LLM summary
        details = "\n\n📋 **Details:**\n"
        for part in sorted_parts[:3]:
            availability = part['Availability']
            status_emoji = "✅" if availability == "In Stock" else "⚠️" if availability == "Limited" else "❌"
            details += f"{status_emoji} {part['PartName']} - SKU: {part['SKU']} | ${part['Price']} | {availability}\n"
        
        if len(sorted_parts) > 3:
            details += f"\n... and {len(sorted_parts) - 3} more available."
        
        return llm_response + details
    
    def format_parts_response(self, parts: List[Dict]) -> str:
        """Fallback formatting without LLM"""
        if not parts:
            return "No parts found matching your criteria."
        
        # Sort by availability (In Stock first, then Limited, then Out of Stock)
        availability_order = {'In Stock': 0, 'Limited': 1, 'Out of Stock': 2}
        sorted_parts = sorted(parts, key=lambda x: availability_order.get(x['Availability'], 3))
        
        response = f"Found {len(sorted_parts)} part(s):\n\n"
        
        for part in sorted_parts[:5]:  # Limit to 5 results
            availability = part['Availability']
            status_emoji = "✅" if availability == "In Stock" else "⚠️" if availability == "Limited" else "❌"
            
            response += f"{status_emoji} **{part['PartName']}**\n"
            response += f"   SKU: {part['SKU']} | Price: ${part['Price']} | {availability}\n"
            response += f"   Fits: {part['VehicleMake']} {part['VehicleModel']} ({part['YearRange']})\n\n"
        
        if len(sorted_parts) > 5:
            response += f"... and {len(sorted_parts) - 5} more parts available.\n"
        
        return response
    
    def process_message(self, message: str, history: List) -> str:
        if not message.strip():
            return "How can I help you find auto parts today?"
        
        # Handle toxic language with de-escalation while preserving context
        if self.is_toxic(message):
            if self.session_vehicle and self.session_part:
                return f"I'm here to help with auto parts - let's keep our conversation respectful. I was helping you with {self.session_vehicle} {self.session_part.lower()}. Do you need installation help or have other questions?"
            elif self.session_part:
                return f"I'm here to help with auto parts - let's keep our conversation respectful. You were looking for {self.session_part.lower()}. Which vehicle make do you need?"
            return "I'm here to help with auto parts - let's keep our conversation respectful. What vehicle and part can I help you find?"
        
        # Check for multi-item queries first
        if self.detect_multi_query(message):
            queries = self.split_multi_query(message)
            if len(queries) > 1:
                # Handle multiple queries
                query_summaries = []
                for query in queries[:2]:  # Limit to 2 queries
                    vehicle, part = self.extract_vehicle_and_part(query)
                    if vehicle and part:
                        query_summaries.append(f"{vehicle} {part}")
                    elif vehicle:
                        query_summaries.append(f"{vehicle} parts")
                    elif part:
                        query_summaries.append(f"{part}")
                
                if len(query_summaries) > 1:
                    return f"I see you're asking about multiple items: {' and '.join(query_summaries)}. Which one would you like me to help with first?"
        
        # Resolve coreferences before processing
        resolved_message = self.resolve_coref(message, self.slot_memory)
        
        # Detect intent on resolved message
        intent = self.detect_intent(resolved_message)
        
        # Handle unknown with escalation safety
        if intent == 'unknown':
            self.oops_count += 1
            self.consecutive_fallbacks += 1
            
            # Double fallback escalation
            if self.consecutive_fallbacks >= 2:
                self.consecutive_fallbacks = 0
                self.awaiting_lead_capture = True
                return "I'm still having trouble. Let me get a human to help – could I have your email or phone?"
            
            # After 2 consecutive unknowns, show help menu once
            if self.oops_count >= 2 and not self.help_shown:
                self.help_shown = True
                self.oops_count = 0
                return "I'm having trouble understanding. Here are some examples:\n\n• 'Honda battery' - Find parts\n• 'What are your hours?' - Store info\n• 'Call me back' - Contact request\n\nWhat would you like to try?"
            
            # Use LLM for polite off-scope redirect if confidence is low
            if self.clf_conf < 0.4:
                try:
                    system_prompt = "If user's request is outside auto-parts (weather, politics, etc.), reply politely in ≤2 sentences, then steer back: 'I can help you find parts or store info—just tell me make + part.'"
                    llm_response = self.call_groq_api(message, system_prompt)
                    return llm_response
                except:
                    pass
            
            return "I didn't catch that. Could you try asking about a specific car part or store information?"
        
        # Reset counters on recognized intent
        if intent != 'unknown':
            self.oops_count = 0
            self.consecutive_fallbacks = 0
        
        # Handle chitchat with proper responses (don't count as invalid)
        if intent == 'chitchat':
            self.conversation_handled = True
            self.last_response_type = 'chitchat'
            # Don't increment invalid_turns for chitchat
            message_lower = message.lower()
            
            # Handle thanks and end session
            if any(word in message_lower for word in ['thanks', 'thank you', 'cheers']):
                self.reset_session()
                return "You're welcome! Feel free to come back anytime you need auto parts help."
            
            # Handle typos in common chitchat (fuzzy matching)
            if any(pattern in message_lower for pattern in ['how is you day', 'how is your day', 'how\'s your day']):
                return "Thanks for asking! I'm here and ready to help. What auto parts can I find for you today?"
            elif 'weather' in message_lower:
                return "I don't have live weather info, but I can help with parts. What vehicle and part are you looking for?"
            elif 'who are you' in message_lower or 'what are you' in message_lower:
                return "I'm your auto parts assistant! I help customers find the right parts for their vehicles. What can I help you find?"
            elif 'how are you' in message_lower:
                return "I'm doing great, thanks for asking! How can I help you with auto parts today?"
            elif any(phrase in message_lower for phrase in ['how\'s your week', 'how is your week', 'how are things', 'how\'s it going', 'what\'s up', 'whats up']):
                return "Things are going well, thanks for asking! I'm here to help you find the right auto parts. What can I help you with?"
            elif any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
                return "Hello! Welcome to our auto parts store. I can help you find parts for your vehicle. Just tell me your car make and what part you need (e.g., 'Honda battery' or 'Toyota tires')."
            elif message_lower in ['ok', 'kk']:
                return "Sure! Let me know if you need anything."
            # Handle casual acknowledgements
            elif any(phrase in message_lower for phrase in ['good', 'great', 'awesome', 'nice', 'cool', 'perfect', 'excellent', 'that\'s fine', 'thats fine', 'no worries', 'sounds good', 'not bad']):
                return "Glad to help—anything else?"
            else:
                return "How can I help you today?"
        
        # Handle car sales (out of scope) with lead capture
        if intent == 'car_sales':
            self.awaiting_lead_capture = True
            return "I'm happy to help you with that! However, I'm an auto parts store assistant, so I'm more knowledgeable about vehicle components rather than buying a new car. If you're in the market for a new ride, I recommend researching online or visiting a local dealership. Can I have your contact so our partner dealership can reach out to help you find the perfect car?"
        
        # Handle installation intent
        if intent == 'installation':
            self.pending_action = 'installation'
            return self.handle_installation_request(resolved_message)
        
        # Handle FAQ
        if intent == 'faq':
            self.conversation_handled = True
            self.last_response_type = 'faq'
            faq_answer = self.check_faq(message)
            if faq_answer:
                # Don't immediately ask for parts after FAQ - wait for user's next input
                return faq_answer
        
        # Handle lead capture with 3-step flow
        if intent == 'lead':
            # Step 1: User agrees to lead capture (stock notification or installation)
            if (self.awaiting_lead_capture or self.pending_install_lead) and not self.lead_capture_step:
                if any(word in message.lower() for word in ['yes', 'ok', 'sure', 'yeah', 'book', 'arrange']):
                    self.lead_capture_step = 'name'
                    return "May I have your name?"
                else:
                    self.awaiting_lead_capture = False
                    self.pending_install_lead = False
                    # Check if this is actually a new product query
                    new_vehicle, new_part = self.extract_vehicle_and_part(resolved_message)
                    if new_vehicle or new_part:
                        # Handle as product query instead of generic response
                        if new_vehicle:
                            self.session_vehicle = new_vehicle
                        if new_part:
                            self.session_part = new_part
                        # Continue to product query handling below
                    else:
                        return "No problem! Is there anything else I can help you find?"
            
            # Step 2: Collect name
            elif self.lead_capture_step == 'name':
                self.lead_name = message.strip()
                self.lead_capture_step = 'contact'
                return f"Thanks, {self.lead_name}. Phone or email so we can reach you?"
            
            # Step 3: Collect contact and save
            elif self.lead_capture_step == 'contact':
                contact = message.strip()
                
                # Handle "both" or insufficient contact info
                if 'both' in contact.lower() and not re.search(r'\d{10}|@', contact):
                    return "I'd be happy to use both! Please provide your phone number and email address. For example: '0410 123 456 and john@email.com'"
                
                phone, email = self.extract_contact_info(contact)
                
                # If neither phone nor email captured, ask again
                if not phone and not email:
                    return "I need either a phone number or email address to contact you. Could you provide one of those?"
                
                # Save the lead (preserve name before clearing state)
                name_to_thank = self.lead_name
                part_name = self.session_part or self.last_recommended_part or 'parts'
                
                # Determine lead type and save with service flag
                if self.pending_install_lead:
                    lead_message = f"Installation service for {part_name}"
                    response_message = f"✅ Perfect! Thanks {name_to_thank}, we'll have a certified technician contact you about {part_name} installation."
                    self.save_lead_with_service(self.lead_name, contact, self.session_vehicle or "", part_name, lead_message, True)
                    self.pending_install_lead = False
                else:
                    lead_message = f"Requested {self.session_part} for {self.session_vehicle}"
                    response_message = f"✅ Perfect! Thanks {name_to_thank}, we'll reach out soon about {part_name} availability."
                    self.save_lead_with_service(self.lead_name, contact, self.session_vehicle or "", part_name, lead_message, False)
                return response_message
            
            # If awaiting lead capture but user asks about different part, handle as product query
            if self.awaiting_lead_capture:
                new_vehicle, new_part = self.extract_vehicle_and_part(resolved_message)
                if new_part and new_part != self.session_part:
                    # User asking about different part - reset lead capture and search
                    self.awaiting_lead_capture = False
                    self.lead_capture_step = None
                    if new_vehicle:
                        self.session_vehicle = new_vehicle
                    if new_part:
                        self.session_part = new_part
                    # Continue to product query handling
                else:
                    return "I'd be happy to help you with lead capture. Please let me know if you'd like to be notified about part availability."
        
        # Handle product queries with improved context management
        current_vehicle, current_part = self.extract_vehicle_and_part(resolved_message)
        
        # Reset lead capture on any new product query
        if current_vehicle or current_part:
            self.awaiting_lead_capture = False
            self.lead_capture_step = None
            self.lead_name = None
        
        # Enhanced slot persistence with context tracking
        if current_vehicle or current_part:
            self.turns_since_valid_context = 0
        else:
            self.turns_since_valid_context += 1
            
        # Timeout old context after 5 turns
        if self.turns_since_valid_context >= 5:
            self.reset_session()
            return "Let's start fresh! What vehicle and part can I help you find?"
        
        # Slot persistence logic - merge new with existing, never wipe unless new value
        if current_vehicle:
            self.session_vehicle = current_vehicle
            self.slot_memory['vehicle_make'] = current_vehicle
        elif self.slot_memory['vehicle_make']:
            self.session_vehicle = self.slot_memory['vehicle_make']
        
        if current_part:
            self.session_part = current_part
            self.slot_memory['part_category'] = current_part
        elif self.slot_memory['part_category']:
            self.session_part = self.slot_memory['part_category']
        
        # Check if we have both vehicle and part (single-turn or accumulated)
        if self.session_vehicle and self.session_part:
            # Check if vehicle make is supported
            supported_makes = ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan', 'Chevrolet', 'Subaru', 'Audi', 'Volkswagen', 'Jeep', 'Mercedes-Benz']
            if self.session_vehicle not in supported_makes:
                return f"I'd love to help, but we don't currently stock parts for {self.session_vehicle}. We specialize in parts for: {', '.join(supported_makes[:5])}, and others. Would you like to check parts for a different vehicle?"
            
            parts = self.search_parts(self.session_vehicle, self.session_part)
            if parts:
                # Use hybrid orchestrator: LLM for friendly summary + structured data
                try:
                    response = self.format_parts_with_llm(parts, self.session_vehicle, self.session_part)
                except Exception as e:
                    # Fallback to deterministic formatting if LLM fails
                    print(f"LLM formatting failed, using fallback: {e}")
                    response = self.format_parts_response(parts)
                
                response += "\n\n💡 Need help with installation or have questions? Just ask!"
                
                # Update slot memory with SKU
                self.slot_memory['last_search_successful'] = True
                if parts:
                    self.slot_memory['last_sku'] = parts[0].get('SKU', '')
                self.last_recommended_part = self.session_part
                self.reset_session()
                return response
            else:
                # Graceful stock-out handling with alternatives
                canon_category = self.get_display_category(self.session_part)
                
                # Check if we have this category for other vehicles (suggest alternatives)
                alternative_parts = []
                for make in supported_makes[:3]:  # Check top 3 makes
                    if make != self.session_vehicle:
                        alt_parts = self.search_parts(make, self.session_part)
                        if alt_parts:
                            alternative_parts.append(make)
                
                response = f"Sorry, we don't currently have {canon_category} for {self.session_vehicle} in stock."
                
                if alternative_parts:
                    response += f"\n\n🔄 However, we do have {canon_category} available for: {', '.join(alternative_parts)}."
                
                response += f"\n\n📞 Would you like us to notify you when {self.session_vehicle} {canon_category} become available?"
                
                # Dynamic stock-out alternatives (single list)
                alternatives = self.get_dynamic_stock_alternatives(self.session_part)
                if alternatives:
                    response += f"\n\n🔄 However, we do have {canon_category} for: {', '.join(alternatives)}."
                
                self.slot_memory['last_search_successful'] = False
                self.awaiting_lead_capture = True
                self.lead_capture_step = None
                return response
        
        # If we have part but no vehicle, ask for vehicle with loop guard
        if self.session_part and not self.session_vehicle:
            # Check for repeated part requests without vehicle
            if self.pending_part_category == self.session_part:
                self.pending_part_count += 1
                if self.pending_part_count >= 2:
                    # Reset and offer lead capture after 2 repetitions
                    self.pending_part_category = None
                    self.pending_part_count = 0
                    self.awaiting_lead_capture = True
                    return f"I see you need {self.session_part.lower()} but I need to know your vehicle make to find the right fit. Would you like me to have someone call you to help find the perfect {self.session_part.lower()} for your car?"
            else:
                self.pending_part_category = self.session_part
                self.pending_part_count = 1
            
            # Check if the part category is something we actually stock
            canon_category = self.get_display_category(self.session_part)
            
            # Check if we have any parts in this category across all vehicles
            has_category = False
            for make in ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan']:
                if self.search_parts(make, self.session_part):
                    has_category = True
                    break
            
            if not has_category:
                return f"I'd love to help with {canon_category}, but that's not a category we currently stock. We specialize in: battery, tires, brakes, filters, oil, spark plugs, suspension, and lighting.\n\nWhat type of part can I help you find instead?"
            
            makes = self.get_available_makes()
            return f"I can help you find {canon_category} for various vehicles! Which make do you need them for?\n\nAvailable makes: {', '.join(makes)}"
        
        # If we have vehicle but no part, ask for part or show available categories
        if self.session_vehicle and not self.session_part:
            # Check if user asked "what else" - show categories available for this vehicle
            if 'what else' in resolved_message.lower() or 'what other' in resolved_message.lower():
                available_categories = self.get_available_categories_for_vehicle(self.session_vehicle)
                if available_categories:
                    return f"Here are the parts we have available for your {self.session_vehicle}:\n\n{', '.join(available_categories)}\n\nWhich category interests you?"
            
            parts = sorted(['battery', 'tires', 'brakes', 'oil', 'filters', 'spark plugs', 'suspension', 'lights'])
            return f"Perfect! I can help you find parts for your {self.session_vehicle}. What type of part do you need?\n\nPopular parts: {', '.join(parts)}"
        
        # Enhanced default guidance with better context
        current_vehicle_final, current_part_final = self.extract_vehicle_and_part(resolved_message)
        if current_vehicle_final and not current_part_final:
            # User mentioned a vehicle but no recognizable part
            return f"I can help you find parts for your {current_vehicle_final}! What type of part do you need?\n\nPopular categories: battery, tires, brakes, oil, filters, spark plugs, suspension, lights"
        elif current_part_final and not current_vehicle_final:
            # User mentioned a part but no recognizable vehicle
            canon_category = self.get_display_category(current_part_final)
            return f"I can help you find {canon_category}! Which vehicle make do you need them for?\n\nSupported makes: Honda, Toyota, Ford, BMW, Nissan, Chevrolet, Subaru, Audi, Volkswagen, Jeep, Mercedes-Benz"
        
        # Default guidance (only if not handled by other intents)
        return "I'd be happy to help you find auto parts! Please tell me:\n1. Your vehicle make (Honda, Toyota, etc.)\n2. What part you need (battery, tires, brakes, etc.)\n\nFor example: 'Honda battery' or 'Toyota tires'"

# Initialize chatbot
chatbot = AutoPartsChatbot()

# Remove old chat_interface function as it's now handled in the Blocks layout

def format_response_with_copyable_skus(response):
    """Make SKUs copyable by wrapping in backticks"""
    import re
    sku_pattern = r'SKU: ([A-Za-z0-9-]+)'
    return re.sub(sku_pattern, r'SKU: `\1`', response)

def chat_interface(message, history):
    response = chatbot.process_message(message, history)
    return format_response_with_copyable_skus(response)

# Modern chat widget
theme = gr.themes.Soft(primary_hue="orange")

demo = gr.ChatInterface(
    fn=chat_interface,
    theme=theme,
    title="Auto Parts Assistant",
    description="Find live stock, prices & policies for automotive parts",
    examples=[
        "Honda battery",
        "Toyota tires", 
        "Opening hours?",
        "Return policy"
    ],
    textbox=gr.Textbox(
        placeholder="Type your message here... (e.g., 'Honda battery', 'What are your hours?')",
        container=False
    ),
    chatbot=gr.Chatbot(
        show_copy_button=True,
        bubble_full_width=False
    ),
    additional_inputs=[],
    css=".contain { max-width: 800px !important; }"
)

# Add footer via CSS injection
with demo:
    gr.HTML("""
        <script>
        setTimeout(() => {
            const footer = document.createElement('div');
            footer.className = 'footer';
            footer.innerHTML = '☎️ 1800-AUTO-PARTS | ✉️ support@autoparts.com.au';
            footer.style.cssText = 'position: fixed; bottom: 0; left: 0; right: 0; background: var(--background-fill-primary); padding: 8px; text-align: center; border-top: 1px solid var(--border-color-primary); font-size: 14px; z-index: 1000;';
            document.body.appendChild(footer);
        }, 1000);
        </script>
    """, visible=False)

if __name__ == "__main__":
    demo.launch(share=True, show_error=True)
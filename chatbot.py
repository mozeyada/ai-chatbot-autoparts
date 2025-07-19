"""
Main AutoPartsChatbot class for the AI Auto Parts Chatbot.
Coordinates between data loading, intent processing, and conversation management.
"""

import os
import re
from typing import Dict, List
from dotenv import load_dotenv
from data_loader import (
    load_products, load_faq, load_synonyms, load_install_tips, 
    load_install_times, load_vehicle_synonyms, init_leads_file,
    save_lead_with_service, save_lead
)
from intent import (
    resolve_coref, is_toxic, detect_intent, extract_vehicle_and_part,
    search_parts, check_faq, call_groq_api, format_parts_with_llm,
    format_parts_response, detect_multi_query, split_multi_query,
    normalize_category, is_valid_name, extract_contact_details,
    is_valid_email, is_valid_phone, is_absurd_or_nonsense, is_negation
)

# Load environment variables
load_dotenv()


class AutoPartsChatbot:
    def __init__(self):
        # Load all data
        self.products_df = load_products()
        self.faq_data = load_faq()
        self.synonyms = load_synonyms()
        self.vehicle_synonyms = load_vehicle_synonyms()
        self.install_tips = load_install_tips()
        self.install_times = load_install_times()
        
        # API key setup
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        if not self.groq_api_key and not os.environ.get("PYTEST_CURRENT_TEST"):
            raise ValueError("GROQ_API_KEY environment variable is required. Please set it in your .env file or environment.")
        
        # Initialize leads file
        self.leads_file = 'data/leads.csv'
        init_leads_file(self.leads_file)
        
        # Session state for conversation context
        self.session_vehicle = None
        self.session_part = None
        self.awaiting_lead_capture = False
        self.lead_capture_step = None
        self.lead_name = None
        self.conversation_handled = False
        self.invalid_turns = 0
        self.help_shown = False
        self.last_response_type = None
        self.pending_install_lead = False
        self.pending_action = None
        
        # Enhanced context memory
        self.slot_memory = {
            'vehicle_make': None,
            'part_category': None,
            'last_sku': None,
            'last_search_successful': False
        }
        self.last_recommended_part = None
        self.oops_count = 0
        self.clf_conf = 0.8  # Start with high confidence
        self.consecutive_fallbacks = 0
        self.turns_since_valid_context = 0
        self.pending_part_category = None
        self.pending_part_count = 0
        self.booking_attempts = 0
        self.last_response = None
        self.friendly_mode = False
        self.last_sku_shown = None
        
        # Intent history tracking
        self.previous_intents = []  # Store last 3 intents
        self.last_intent = None
        
        # Advanced context tracking
        self.entity_memory = {}  # Store additional entities
        self.conversation_state = 'initial'  # For state machine
        self.state_history = []  # Track conversation flow
    
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
        self.pending_install_lead = False
        self.pending_action = None
        
        # Clear enhanced context memory
        self.slot_memory = {
            'vehicle_make': None,
            'part_category': None,
            'last_sku': None,
            'last_search_successful': False
        }
        self.last_recommended_part = None
        self.oops_count = 0
        self.consecutive_fallbacks = 0
        self.turns_since_valid_context = 0
        self.pending_part_category = None
        self.pending_part_count = 0
        self.booking_attempts = 0
        self.last_response = None
        self.friendly_mode = False
        self.last_sku_shown = None
        
        # Reset intent history
        self.previous_intents = []
        self.last_intent = None
        
        # Reset advanced context
        self.entity_memory = {}
        self.conversation_state = 'initial'
        
    def update_context_memory(self, intent_data: dict, message: str):
        """Update context memory with enhanced entity tracking"""
        # Extract entities from intent data
        entities = intent_data.get('entities', {})
        
        # Update vehicle make if detected
        if entities.get('vehicle_make'):
            self.session_vehicle = entities['vehicle_make']
            self.slot_memory['vehicle_make'] = entities['vehicle_make']
            self.turns_since_valid_context = 0
        
        # Update part category if detected
        if entities.get('part_category'):
            self.session_part = entities['part_category']
            self.slot_memory['part_category'] = entities['part_category']
            self.turns_since_valid_context = 0
        
        # Store any additional entities
        for key, value in entities.items():
            if key not in ['vehicle_make', 'part_category'] and value:
                self.entity_memory[key] = value
        
        # Update confidence based on LLM confidence
        self.clf_conf = intent_data.get('confidence', 0.8)
        
        # Reset counters on high confidence
        if self.clf_conf > 0.7:
            self.oops_count = 0
            self.consecutive_fallbacks = 0
            
    def manage_conversation_flow(self, intent_data: dict, message: str) -> None:
        """Manage conversation flow using a state machine approach"""
        current_state = self.conversation_state
        primary_intent = intent_data.get('primary_intent')
        
        # Define state transitions
        transitions = {
            'initial': {
                'product': 'product_search',
                'faq': 'information',
                'installation': 'installation_inquiry',
                'lead': 'lead_capture',
                'chitchat': 'initial'
            },
            'product_search': {
                'product': 'product_search',
                'installation': 'installation_inquiry',
                'lead': 'lead_capture',
                'faq': 'information',
                'chitchat': 'product_search'
            },
            'installation_inquiry': {
                'lead': 'lead_capture',
                'product': 'product_search',
                'installation': 'installation_inquiry',
                'chitchat': 'installation_inquiry'
            },
            'lead_capture': {
                # Lead capture has its own state management
                'lead': 'lead_capture',
                'negation': 'initial'
            },
            'information': {
                'product': 'product_search',
                'faq': 'information',
                'installation': 'installation_inquiry',
                'chitchat': 'initial'
            }
        }
        
        # Get next state based on intent
        if primary_intent in transitions.get(current_state, {}):
            next_state = transitions[current_state][primary_intent]
        else:
            # Default transition
            next_state = current_state
        
        # Update state
        self.conversation_state = next_state
        
        # Special state actions
        if next_state == 'lead_capture' and not self.awaiting_lead_capture:
            self.awaiting_lead_capture = True
        
        # Track state history
        self.state_history.append(next_state)
        
    def process_multi_intent(self, intent_data: dict, message: str, history: List) -> str:
        """Handle messages with multiple intents"""
        primary_intent = intent_data.get('primary_intent')
        secondary_intent = intent_data.get('secondary_intent')
        
        # Process primary intent first
        primary_response = self.process_single_intent(primary_intent, message, history)
        
        # If there's a secondary intent, process it too
        if secondary_intent and secondary_intent != primary_intent:
            # Special handling for common combinations
            if primary_intent == 'product' and secondary_intent == 'installation':
                # Combine product search with installation info
                vehicle = self.session_vehicle or intent_data.get('entities', {}).get('vehicle_make')
                part = self.session_part or intent_data.get('entities', {}).get('part_category')
                
                if vehicle and part:
                    minutes = self.get_install_time_minutes(part)
                    install_info = f"\n\n⚙️ Installation: {minutes} minutes for professional installation. Would you like to book a service appointment?"
                    self.pending_install_lead = True
                    return primary_response + install_info
            
            elif primary_intent == 'faq' and secondary_intent == 'product':
                # Add product suggestion after FAQ
                return primary_response + "\n\nCan I help you find specific parts for your vehicle?"
        
        return primary_response
        
    def process_single_intent(self, intent: str, message: str, history: List) -> str:
        """Process a single intent with enhanced context"""
        # This will be implemented in the next step
        # For now, return a placeholder
        return f"Processing intent: {intent}"
    
    def get_available_makes(self) -> List[str]:
        """Get available vehicle makes from products data"""
        if self.products_df.empty:
            return ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan', 'Chevrolet', 'Subaru', 'Audi', 'Volkswagen', 'Jeep', 'Mercedes-Benz']
        return sorted(self.products_df['VehicleMake'].unique().tolist())
    
    def get_dynamic_stock_alternatives(self, part_category: str) -> List[str]:
        """Get real makes with inventory for given category"""
        if self.products_df.empty:
            return []
        
        canon_category = normalize_category(part_category, self.synonyms)
        available_makes = self.products_df[
            (self.products_df['Category'].str.lower() == canon_category.lower()) &
            (self.products_df['Availability'].isin(['In Stock', 'Limited']))
        ]['VehicleMake'].unique().tolist()
        
        return available_makes[:5]
    
    def get_display_category(self, category: str) -> str:
        """Get user-friendly display name for category"""
        canon = normalize_category(category, self.synonyms)
        
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
    
    def get_available_categories_for_vehicle(self, vehicle_make: str) -> List[str]:
        """Get list of available part categories for a specific vehicle"""
        if self.products_df.empty:
            return []
        
        vehicle_parts = self.products_df[self.products_df['VehicleMake'].str.lower() == vehicle_make.lower()]
        categories = vehicle_parts['Category'].unique().tolist()
        
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
            return 45
    
    def handle_installation_request(self, message: str) -> str:
        """Handle installation-related queries with context preservation"""
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
    
    def process_message(self, message: str, history: List) -> str:
        """Main message processing function"""
        if not message.strip():
            return "How can I help you find auto parts today?"

        # Resolve coreferences before processing
        resolved_message = resolve_coref(message, self.slot_memory)
        
        # Detect intent on resolved message using LLM
        intent = detect_intent(resolved_message, self.groq_api_key)
        print(f"DEBUG: Intent detected: '{intent}' for message: '{message[:30]}...'" if len(message) > 30 else f"DEBUG: Intent detected: '{intent}' for message: '{message}'")
        
        # Store intent history
        self.last_intent = intent
        self.previous_intents.insert(0, intent)
        if len(self.previous_intents) > 3:
            self.previous_intents = self.previous_intents[:3]
        
        # Handle negation responses - don't reset context
        if is_negation(message):
            print("DEBUG: Negation detected, preserving context")
            # If we were in lead capture, cancel it but preserve context
            if self.awaiting_lead_capture or self.lead_capture_step:
                self.awaiting_lead_capture = False
                self.lead_capture_step = None
                return "No problem. Is there anything else I can help you with?"
            # Otherwise just acknowledge and continue
            return "Understood. Is there something else I can help you with?"
        
        # Handle abuse with proper de-escalation (no product fallback)
        if intent == 'abuse':
            return "I'm here to assist with auto parts. Let's keep our conversation respectful and professional. How can I help you find the right parts for your vehicle?"
        
        # Handle nonsense/absurd requests (no product extraction)
        if intent == 'nonsense':
            return "I'm here to help with auto parts for your vehicle. Could you let me know what specific part you're looking for?"
        
        # Handle callback requests
        if intent == 'callback_request':
            self.awaiting_lead_capture = True
            return "I'd be happy to arrange a callback for you! May I have your name and phone number so our team can reach out?"
        
        # Handle promotions/specials requests
        if intent == 'promotions':
            vehicle_context = f" for your {self.session_vehicle}" if self.session_vehicle else ""
            return f"Great question! We currently have special pricing on lighting and suspension parts{vehicle_context}. What specific part are you interested in?"
        
        # Handle unknown with escalation safety
        if intent == 'unknown':
            self.oops_count += 1
            self.consecutive_fallbacks += 1
            
            # Check if message might be a part name without vehicle make
            common_parts = ['battery', 'batteries', 'tire', 'tires', 'brake', 'brakes', 'oil', 'filter', 'filters', 
                           'spark', 'plugs', 'light', 'lights', 'mirror', 'mirrors', 'bumper', 'bumpers']
            
            message_lower = message.lower().strip()
            for part in common_parts:
                if part in message_lower or fuzz.ratio(message_lower, part) > 80:
                    # This is likely a part name without vehicle make
                    normalized_part = part
                    if part == 'batteries': normalized_part = 'Battery'
                    elif part in ['tires', 'tire']: normalized_part = 'Tires'
                    elif part in ['brakes', 'brake']: normalized_part = 'Brakes'
                    elif part in ['filters', 'filter']: normalized_part = 'Filters'
                    elif part in ['lights', 'light']: normalized_part = 'Lighting'
                    elif part in ['mirrors', 'mirror']: normalized_part = 'Accessories'
                    elif part in ['bumpers', 'bumper']: normalized_part = 'Accessories'
                    
                    self.session_part = normalized_part
                    self.slot_memory['part_category'] = normalized_part
                    
                    makes = self.get_available_makes()
                    return f"I can help you find {part} for various vehicles! Which make do you need them for?\n\nAvailable makes: {', '.join(makes)}"
            
            # Double fallback escalation - only if truly unknown
            if self.consecutive_fallbacks >= 3:
                self.consecutive_fallbacks = 0
                self.awaiting_lead_capture = True
                return "I'm still having trouble. Let me get a human to help – could I have your email or phone?"
            
            # After 2 consecutive unknowns, show help menu once
            if self.oops_count >= 2 and not self.help_shown:
                self.help_shown = True
                self.oops_count = 0
                return "I'm having trouble understanding. Here are some examples:\n\n• 'Honda battery' - Find parts\n• 'What are your hours?' - Store info\n• 'Call me back' - Contact request\n\nWhat would you like to try?"
            
            # Check if message contains car-related terms but no specific make/part
            car_terms = ['car', 'vehicle', 'auto', 'automobile', 'ride']
            if any(term in message.lower() for term in car_terms):
                from handle_vague_vehicle_query import handle_vague_vehicle_query
                return handle_vague_vehicle_query(message, self.groq_api_key)
            
            # Always use LLM for unknown intents to provide a more natural response
            try:
                system_prompt = """You are a helpful auto parts store assistant. 
                The user has sent a message that doesn't clearly specify a vehicle make or part.
                
                Respond naturally to their message, then gently guide them to provide:
                1. Their vehicle make (Honda, Toyota, etc.)
                2. What part they need (battery, tires, brakes, etc.)
                
                Keep your response friendly, conversational, and under 2 sentences.
                """
                llm_response = call_groq_api(self.groq_api_key, message, system_prompt)
                return llm_response
            except Exception as e:
                print(f"LLM fallback error: {e}")
                return "I didn't catch that. Could you try asking about a specific car part or store information?"
        
        # Reset counters on recognized intent
        if intent != 'unknown':
            self.oops_count = 0
            self.consecutive_fallbacks = 0
        
        # Handle chitchat with enhanced friendly responses
        if intent == 'chitchat':
            self.conversation_handled = True
            self.last_response_type = 'chitchat'
            message_lower = message.lower()
            
            # Handle friendship/tone requests
            if any(pattern in message_lower for pattern in ['friend', 'speak.*friend', 'talk.*friend', 'cold', 'warm']):
                self.friendly_mode = True
                return "You got it! I'm here to help you out with whatever you need for your ride. What's going on with your car today? 😊"
            
            # Handle "does that mean" questions
            if 'does that mean' in message_lower:
                if self.friendly_mode:
                    return "Yeah, I'm all good and ready to help! What can I find for your car?"
                else:
                    return "Yes, I'm ready to help! What auto parts do you need?"
            
            # Handle thanks and end session
            if any(word in message_lower for word in ['thanks', 'thank you', 'cheers']):
                # Don't reset session immediately to maintain context
                response = "You're welcome!" if not self.friendly_mode else "No worries, buddy!"
                return f"{response} Feel free to ask if you need anything else."
            
            # Handle common chitchat patterns with friendly mode
            if any(pattern in message_lower for pattern in ['how is you day', 'how is your day', "how's your day"]):
                if self.friendly_mode:
                    return "Thanks for asking! I'm doing great and ready to help you out. What's your car needing today?"
                else:
                    return "Thanks for asking! I'm here and ready to help. What auto parts can I find for you today?"
            elif 'weather' in message_lower:
                return "I don't have live weather info, but I can help with parts. What vehicle and part are you looking for?"
            elif 'who are you' in message_lower or 'what are you' in message_lower:
                if self.friendly_mode:
                    return "I'm your auto parts buddy! I help find the perfect parts for your ride. What do you need?"
                else:
                    return "I'm your auto parts assistant! I help customers find the right parts for their vehicles. What can I help you find?"
            elif 'how are you' in message_lower:
                if self.friendly_mode:
                    return "I'm doing awesome, thanks for asking! How can I help with your car today?"
                else:
                    return "I'm doing great, thanks for asking! How can I help you with auto parts today?"
            elif any(phrase in message_lower for phrase in ["how's your week", 'how is your week', 'how are things', "how's it going", "what's up", 'whats up']):
                if self.friendly_mode:
                    return "Things are going great, thanks! Ready to help you get your car sorted. What's up?"
                else:
                    return "Things are going well, thanks for asking! I'm here to help you find the right auto parts. What can I help you with?"
            elif any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
                if self.friendly_mode:
                    return "Hey there! What's your car needing today? Just tell me the make and part (like 'Honda battery')."
                else:
                    return "Hello! Welcome to our auto parts store. I can help you find parts for your vehicle. Just tell me your car make and what part you need (e.g., 'Honda battery' or 'Toyota tires')."
            elif message_lower in ['ok', 'kk', '?', 'hmm']:
                return "Sure! Let me know if you need anything."
            elif any(phrase in message_lower for phrase in ['good', 'great', 'awesome', 'nice', 'cool', 'perfect', 'excellent', "that's fine", 'thats fine', 'no worries', 'sounds good', 'not bad']):
                return "Glad to help—anything else?"
            elif 'why are you' in message_lower or 'cold' in message_lower:
                return "I'm here to help you find auto parts. Is there something specific I can assist you with?"
            elif 'other questions' in message_lower or 'other parts' in message_lower:
                if self.session_vehicle:
                    return f"Sure! I can show you other parts for your {self.session_vehicle}, or help with store info, installation services, etc. What interests you?"
                else:
                    return "Sure! I can help with parts searches, store information, installation services, or any other auto parts questions. What would you like to know?"
            elif 'teach me' in message_lower or 'respect' in message_lower:
                return "I'm just here to help with auto parts. What can I find for your vehicle today?"
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
            faq_answer = check_faq(message, self.faq_data)
            if faq_answer:
                return faq_answer
        
        # Handle product intent explicitly
        if intent == 'product':
            # This will fall through to the product query handling below
            pass
        
        # Special handling for "call me" phrases that might be missed by intent detection
        if "call me" in message.lower() and intent != "lead":
            print("DEBUG: Special case - 'call me' detected, overriding intent to lead")
            intent = "lead"
            self.awaiting_lead_capture = True
        
        # Handle lead capture with 3-step flow
        # Check if this is a lead intent or if we're already in lead capture flow
        if intent == 'lead' or self.awaiting_lead_capture or self.lead_capture_step or self.pending_install_lead:
            # Step 1: User agrees to lead capture
            if (self.awaiting_lead_capture or self.pending_install_lead) and not self.lead_capture_step:
                if any(word in message.lower() for word in ['yes', 'ok', 'sure', 'yeah', 'book', 'arrange']):
                    self.lead_capture_step = 'name'
                    return "May I have your name?"
                else:
                    self.awaiting_lead_capture = False
                    self.pending_install_lead = False
                    new_vehicle, new_part = extract_vehicle_and_part(resolved_message, self.vehicle_synonyms, self.synonyms)
                    if new_vehicle or new_part:
                        if new_vehicle:
                            self.session_vehicle = new_vehicle
                        if new_part:
                            self.session_part = new_part
                    else:
                        return "No problem! Is there anything else I can help you find?"
            
            # Step 2: Collect name with validation
            elif self.lead_capture_step == 'name':
                name = message.strip()
                if not is_valid_name(name):
                    return "I need your name to proceed. Could you please provide your first and last name?"
                self.lead_name = name
                self.lead_capture_step = 'contact'
                return f"Thanks, {self.lead_name}. Phone or email so we can reach you?"
            
            # Step 3: Collect contact and save with better validation
            elif self.lead_capture_step == 'contact':
                contact = message.strip()
                
                # Handle "both" request
                if 'both' in contact.lower() and not re.search(r'\d{10}|@', contact):
                    return "I'd be happy to use both! Please provide your phone number and email address. For example: '0410 123 456 and john@email.com'"
                
                # Extract contact details
                contact_info = extract_contact_details(contact)
                phone = contact_info['phone']
                email = contact_info['email']
                
                # Validate contact details
                valid_phone = phone and is_valid_phone(phone)
                valid_email = email and is_valid_email(email)
                
                if not valid_phone and not valid_email:
                    # Increment booking attempts to prevent infinite loops
                    if not hasattr(self, 'booking_attempts'):
                        self.booking_attempts = 0
                    self.booking_attempts += 1
                    
                    if self.booking_attempts >= 3:
                        # Reset booking flow after too many failed attempts
                        self.awaiting_lead_capture = False
                        self.lead_capture_step = None
                        self.lead_name = None
                        self.booking_attempts = 0
                        return "It seems we're having trouble collecting your contact information. Would you like to start over or try a different approach?"
                    
                    return "I need a valid phone number or email address to contact you. Please provide a phone number (like 0410 123 456) or email address (like name@email.com)."
                
                # Save the lead with proper context preservation
                name_to_thank = self.lead_name
                part_name = self.session_part or self.last_recommended_part or 'parts'
                vehicle_name = self.session_vehicle or 'your vehicle'
                
                # Reset booking attempts on success
                self.booking_attempts = 0
                
                if self.pending_install_lead:
                    lead_message = f"Installation service for {part_name}"
                    response_message = f"✅ Perfect! Thanks {name_to_thank}, we'll have a certified technician contact you about {part_name} installation."
                    save_lead_with_service(self.leads_file, self.lead_name, contact, self.session_vehicle or "", part_name, lead_message, True)
                    self.pending_install_lead = False
                else:
                    lead_message = f"Requested {part_name} for {vehicle_name}"
                    response_message = f"✅ Perfect! Thanks {name_to_thank}, we'll reach out soon about {part_name} availability."
                    save_lead_with_service(self.leads_file, self.lead_name, contact, self.session_vehicle or "", part_name, lead_message, False)
                
                # Clear lead capture state
                self.awaiting_lead_capture = False
                self.lead_capture_step = None
                self.lead_name = None
                self.conversation_handled = True
                self.last_response_type = None
                
                return response_message
        
        # Handle product queries with improved context management
        # This handles both explicit 'product' intent and fallthrough cases
        current_vehicle, current_part = extract_vehicle_and_part(resolved_message, self.vehicle_synonyms, self.synonyms)
        
        # If message contains "car" or "vehicle" but no specific make or part
        if ('car' in resolved_message.lower() or 'vehicle' in resolved_message.lower()) and not current_vehicle and not current_part:
            from handle_vague_vehicle_query import handle_vague_vehicle_query
            return handle_vague_vehicle_query(resolved_message, self.groq_api_key)
        
        # Use LLM for complex part extraction if we have a vehicle but no part detected
        if current_vehicle and not current_part and len(resolved_message.split()) > 3:
            try:
                # Check for common phrases that indicate looking for parts
                looking_for_phrases = ['looking for', 'need', 'want', 'searching for', 'find', 'get']
                is_looking_for_part = any(phrase in resolved_message.lower() for phrase in looking_for_phrases)
                
                # Use LLM to extract part information with more context
                system_prompt = f"""Extract the auto part category from this message. The user has a {current_vehicle}.
                Valid categories: Battery, Tires, Brakes, Oil, Filters, Spark Plugs, Suspension, Lighting, Accessories.
                
                Important mappings:
                - If you detect 'mirror', 'rear mirror', 'side mirror', etc., classify it as 'Accessories'
                - If you detect 'light', 'headlight', 'lamp', etc., classify it as 'Lighting'
                - If you detect 'bumper', 'fender', etc., classify it as 'Accessories'
                
                The user is likely looking for a specific part. Analyze the message carefully.
                Reply ONLY with the category name, nothing else."""
                
                llm_response = call_groq_api(self.groq_api_key, resolved_message, system_prompt)
                
                # Clean up response and check if it's a valid category
                llm_part = llm_response.strip()
                valid_categories = ['Battery', 'Tires', 'Brakes', 'Oil', 'Filters', 'Spark Plugs', 'Suspension', 'Lighting', 'Accessories']
                
                # Check if the LLM response matches a valid category (case-insensitive)
                for category in valid_categories:
                    if category.lower() == llm_part.lower():
                        current_part = category
                        self.session_part = category  # Important: Set the session part
                        self.slot_memory['part_category'] = category  # Update slot memory
                        break
                
                print(f"DEBUG: LLM extracted part='{llm_part}' from message='{resolved_message}'")
            except Exception as e:
                print(f"DEBUG: LLM part extraction failed: {e}")
                
                # Special case for common phrases
                if 'mirror' in resolved_message.lower():
                    current_part = 'Accessories'
                    self.session_part = 'Accessories'
                    self.slot_memory['part_category'] = 'Accessories'
                    print("DEBUG: Special case detected 'mirror' -> Accessories")
                elif 'light' in resolved_message.lower():
                    current_part = 'Lighting'
                    self.session_part = 'Lighting'
                    self.slot_memory['part_category'] = 'Lighting'
                    print("DEBUG: Special case detected 'light' -> Lighting")
        
        # Debug logging
        if current_vehicle or current_part:
            print(f"DEBUG: Extracted vehicle='{current_vehicle}', part='{current_part}' from message='{resolved_message}'")
        
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
        
        # Slot persistence logic with debug
        if current_vehicle:
            print(f"DEBUG: Setting session_vehicle to '{current_vehicle}'")
            self.session_vehicle = current_vehicle
            self.slot_memory['vehicle_make'] = current_vehicle
        elif self.slot_memory['vehicle_make']:
            print(f"DEBUG: Using stored vehicle '{self.slot_memory['vehicle_make']}'")
            self.session_vehicle = self.slot_memory['vehicle_make']
        
        if current_part:
            print(f"DEBUG: Setting session_part to '{current_part}'")
            self.session_part = current_part
            self.slot_memory['part_category'] = current_part
        elif self.slot_memory['part_category']:
            print(f"DEBUG: Using stored part '{self.slot_memory['part_category']}'")
            self.session_part = self.slot_memory['part_category']
        
        print(f"DEBUG: Final state - vehicle='{self.session_vehicle}', part='{self.session_part}'")
        
        # Check if we have both vehicle and part
        if self.session_vehicle and self.session_part:
            print(f"DEBUG: Searching for {self.session_vehicle} {self.session_part}")
            supported_makes = ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan', 'Chevrolet', 'Subaru', 'Audi', 'Volkswagen', 'Jeep', 'Mercedes-Benz', 'Hyundai', 'Kia', 'Mazda']
            if self.session_vehicle not in supported_makes:
                return f"I'd love to help, but we don't currently stock parts for {self.session_vehicle}. We specialize in parts for: {', '.join(supported_makes[:5])}, and others. Would you like to check parts for a different vehicle?"
            
            parts = search_parts(self.products_df, self.session_vehicle, self.session_part, self.synonyms)
            print(f"DEBUG: Found {len(parts)} parts")
            if parts:
                try:
                    response = format_parts_with_llm(self.groq_api_key, parts, self.session_vehicle, self.session_part)
                except Exception as e:
                    print(f"LLM formatting failed, using fallback: {e}")
                    response = format_parts_response(parts)
                
                response += "\n\n💡 Need help with installation or have questions? Just ask!"
                
                # Check for repetitive SKU display
                current_sku = parts[0].get('SKU', '') if parts else ''
                if current_sku == self.last_sku_shown:
                    return f"You already saw our top {self.session_part.lower()} option. Would you like to see other {self.session_part.lower()} choices or different parts for your {self.session_vehicle}?"
                
                # Update slot memory
                self.slot_memory['last_search_successful'] = True
                if parts:
                    self.slot_memory['last_sku'] = current_sku
                    self.last_sku_shown = current_sku
                self.last_recommended_part = self.session_part
                # Don't reset session immediately - keep context for follow-up questions
                return response
            else:
                # Graceful stock-out handling
                canon_category = self.get_display_category(self.session_part)
                
                # Dynamic stock-out alternatives
                alternatives = self.get_dynamic_stock_alternatives(self.session_part)
                
                # Use LLM for a more natural stock-out response
                try:
                    alt_text = ", ".join(alternatives) if alternatives else "none"
                    system_prompt = f"""You are a helpful auto parts store assistant. 
                    The customer is looking for {canon_category} for their {self.session_vehicle}, but we don't have any in stock.
                    Alternative makes that have this part in stock: {alt_text}
                    
                    Create a friendly, helpful response (2-3 sentences) that:
                    1. Apologizes for not having the part in stock
                    2. Mentions the alternative makes if available
                    3. Offers to notify them when the part becomes available
                    
                    Be conversational and helpful."""
                    
                    llm_response = call_groq_api(self.groq_api_key, f"{self.session_vehicle} {canon_category} out of stock", system_prompt)
                    
                    self.slot_memory['last_search_successful'] = False
                    self.awaiting_lead_capture = True
                    self.lead_capture_step = None
                    return llm_response
                except Exception as e:
                    print(f"LLM stock-out response failed: {e}")
                    
                    # Fallback to template response
                    response = f"Sorry, we don't currently have {canon_category} for {self.session_vehicle} in stock."
                    
                    if alternatives:
                        response += f"\n\n🔄 However, we do have {canon_category} for: {', '.join(alternatives)}."
                    
                    response += f"\n\n📞 Would you like us to notify you when {self.session_vehicle} {canon_category} become available?"
                    
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
                    self.pending_part_category = None
                    self.pending_part_count = 0
                    self.awaiting_lead_capture = True
                    return f"I see you need {self.session_part.lower()} but I need to know your vehicle make to find the right fit. Would you like me to have someone call you to help find the perfect {self.session_part.lower()} for your car?"
            else:
                self.pending_part_category = self.session_part
                self.pending_part_count = 1
            
            # Check if the part category is something we stock
            canon_category = self.get_display_category(self.session_part)
            
            has_category = False
            for make in ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan']:
                if search_parts(self.products_df, make, self.session_part, self.synonyms):
                    has_category = True
                    break
            
            if not has_category:
                return f"I'd love to help with {canon_category}, but that's not a category we currently stock. We specialize in: battery, tires, brakes, filters, oil, spark plugs, suspension, and lighting.\n\nWhat type of part can I help you find instead?"
            
            makes = self.get_available_makes()
            return f"I can help you find {canon_category} for various vehicles! Which make do you need them for?\n\nAvailable makes: {', '.join(makes)}"
        
        # If we have vehicle but no part, ask for part
        if self.session_vehicle and not self.session_part:
            if 'what else' in resolved_message.lower() or 'what other' in resolved_message.lower():
                available_categories = self.get_available_categories_for_vehicle(self.session_vehicle)
                if available_categories:
                    return f"Here are the parts we have available for your {self.session_vehicle}:\n\n{', '.join(available_categories)}\n\nWhich category interests you?"
            
            # Use LLM for a more natural response
            try:
                parts = sorted(['battery', 'tires', 'brakes', 'oil', 'filters', 'spark plugs', 'suspension', 'lights', 'mirrors', 'accessories'])
                parts_list = ', '.join(parts)
                
                system_prompt = f"""You are a helpful auto parts store assistant. The customer has a {self.session_vehicle} but hasn't specified what part they need.
                Create a friendly, helpful response (2-3 sentences) asking what specific part they need for their {self.session_vehicle}.
                Include this list of popular parts: {parts_list}
                Be conversational but concise."""
                
                llm_response = call_groq_api(self.groq_api_key, f"I have a {self.session_vehicle}", system_prompt)
                return llm_response
            except Exception as e:
                print(f"LLM part request failed: {e}")
                parts = sorted(['battery', 'tires', 'brakes', 'oil', 'filters', 'spark plugs', 'suspension', 'lights'])
                return f"Perfect! I can help you find parts for your {self.session_vehicle}. What type of part do you need?\n\nPopular parts: {', '.join(parts)}"
        
        # Enhanced default guidance
        current_vehicle_final, current_part_final = extract_vehicle_and_part(resolved_message, self.vehicle_synonyms, self.synonyms)
        
        # Try LLM-based part detection for complex queries
        if current_vehicle_final and not current_part_final and len(resolved_message.split()) > 3:
            try:
                system_prompt = f"""Extract the auto part category from this message. The user has a {current_vehicle_final}.
                Valid categories: Battery, Tires, Brakes, Oil, Filters, Spark Plugs, Suspension, Lighting, Accessories.
                If you detect a part like 'mirror', 'bumper', etc., classify it as 'Accessories'.
                If you detect 'light', 'headlight', etc., classify it as 'Lighting'.
                Reply ONLY with the category name, nothing else."""
                
                llm_response = call_groq_api(self.groq_api_key, resolved_message, system_prompt)
                
                # Clean up response and check if it's a valid category
                llm_part = llm_response.strip()
                valid_categories = ['Battery', 'Tires', 'Brakes', 'Oil', 'Filters', 'Spark Plugs', 'Suspension', 'Lighting', 'Accessories']
                
                # Check if the LLM response matches a valid category (case-insensitive)
                for category in valid_categories:
                    if category.lower() == llm_part.lower():
                        current_part_final = category
                        self.session_part = category
                        self.slot_memory['part_category'] = category
                        print(f"DEBUG: LLM detected part='{category}' from message='{resolved_message}'")
                        break
            except Exception as e:
                print(f"DEBUG: LLM part detection failed: {e}")
        
        if current_vehicle_final and not current_part_final:
            # Check if this is a supported make
            supported_makes = ['Honda', 'Toyota', 'Ford', 'BMW', 'Nissan', 'Chevrolet', 'Subaru', 'Audi', 'Volkswagen', 'Jeep', 'Mercedes-Benz', 'Hyundai', 'Kia', 'Mazda']
            if current_vehicle_final not in supported_makes:
                return f"I'd love to help with {current_vehicle_final} parts, but we currently only stock parts for: {', '.join(supported_makes[:5])}, and others. Would you like to check parts for one of these vehicles instead?"
            
            parts = sorted(['battery', 'tires', 'brakes', 'oil', 'filters', 'spark plugs', 'suspension', 'lights'])
            return f"I can help you find parts for your {current_vehicle_final}! What type of part do you need?\n\nPopular categories: {', '.join(parts)}"
        elif current_part_final and not current_vehicle_final:
            canon_category = self.get_display_category(current_part_final)
            return f"I can help you find {canon_category}! Which vehicle make do you need them for?\n\nSupported makes: Honda, Toyota, Ford, BMW, Nissan, Chevrolet, Subaru, Audi, Volkswagen, Jeep, Mercedes-Benz, Hyundai"
        
        # Default guidance (avoid repetitive product responses)
        if intent == 'unknown' and self.last_response_type == 'product':
            return "I'm not sure I understand. Could you clarify what you're looking for? I can help with parts searches, store info, or installation services."
        
        return "I'd be happy to help you find auto parts! Please tell me:\n1. Your vehicle make (Honda, Toyota, etc.)\n2. What part you need (battery, tires, brakes, etc.)\n\nFor example: 'Honda battery' or 'Toyota tires'"


#!/usr/bin/env python3

if __name__ == "__main__":
    from ui import launch_app
    launch_app()
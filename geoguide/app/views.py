import os
import json
import requests
import re
import google.generativeai as genai
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import time
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
from dotenv import load_dotenv

#create an environment variable file .env and add your API keys there
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

print("DEBUG: GeoGuide AI Assistant starting...")
print(f"DEBUG: Google Maps API Key loaded")
genai.configure(api_key=GEMINI_API_KEY)



# Configure Gemini AI with updated model name
try:
    # Try to list available models
    models = genai.list_models()
    model_names = [m.name for m in models]
    print(f"DEBUG: Available models: {model_names}")
    
    # Try common model names in order of preference
    model_attempts = [
        'models/gemini-1.5-flash-latest',  # Most likely available
        'models/gemini-1.5-pro-latest',    # Pro version
        'models/gemini-1.0-pro-latest',    # Older pro
        'models/gemini-pro',               # Generic name
    ]
    
    # Check which models are actually available
    available_model = None
    for model_name in model_attempts:
        if any(model_name in name for name in model_names):
            available_model = model_name
            print(f"DEBUG: Found available model: {available_model}")
            break
    
    if available_model:
        # Store the model in gemini_model
        gemini_model = genai.GenerativeModel(available_model)
        print(f"DEBUG: Gemini AI configured with {available_model}")
    else:
        print("DEBUG: No suitable Gemini model found in available models")
        # Fallback to trying a common model directly
        try:
            gemini_model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            print("DEBUG: Gemini AI configured with fallback model")
        except Exception as e:
            print(f"DEBUG: Fallback model configuration failed: {e}")
            gemini_model = None

except Exception as e:
    print(f"DEBUG: Gemini AI configuration failed: {e}")
    gemini_model = None

    


def home(request):
    """Render the main page with API keys"""
    return render(request, 'home.html', {
        'GOOGLE_MAPS_API_KEY': GOOGLE_MAPS_API_KEY
    })


@csrf_exempt
@require_http_methods(["POST"])
def get_user_location_greeting(request):
    """
    Get user's location and generate personalized greeting WITH AI
    """
    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lng = data.get('longitude')
        username = data.get('username', 'Traveler')
        
        print(f"DEBUG: Location greeting request - lat: {lat}, lng: {lng}, username: {username}")
        
        # Get location name from coordinates
        location_name = get_location_name_google(lat, lng)
        print(f"DEBUG: Location name: {location_name}")
        
        # Generate greeting with AI
        greeting = generate_ai_greeting(username, location_name)
        
        print(f"DEBUG: Generated greeting: {greeting[:50]}...")
        
        return JsonResponse({
            'success': True,
            'greeting': greeting,
            'location': location_name,
            'coordinates': {'lat': lat, 'lng': lng},
            'ai_used': True
        })
        
    except Exception as e:
        print(f"ERROR in get_user_location_greeting: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def chat_with_ai(request):
    """
    Handle conversational AI requests with REAL Gemini AI responses
    """
    try:
        print(f"DEBUG: ====== CHAT REQUEST START ======")
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        lat = data.get('latitude')
        lng = data.get('longitude')
        conversation_history = data.get('conversation_history', [])
        current_places = data.get('current_places', [])  # GET CURRENT PLACES FROM FRONTEND
        
        print(f"DEBUG: Chat request - message: '{user_message}', lat: {lat}, lng: {lng}")
        print(f"DEBUG: Current places from frontend: {len(current_places)}")
        
        # Get location context
        location_name = get_location_name_google(lat, lng)
        print(f"DEBUG: Location for chat: {location_name}")
        
        # CHECK IF THIS IS A "TELL ME MORE" QUERY
        user_lower = user_message.lower()
        is_detail_query = any(phrase in user_lower for phrase in [
            'tell me more about', 'more about', 'details about', 
            'info about', 'information about', 'tell me about'
        ])
        
        if is_detail_query and current_places:
            # This is a detail query - don't search, just respond about existing places
            print(f"DEBUG: Detail query detected!")
            
            # Extract place name from message - FIXED VERSION WITH ERROR HANDLING
            place_name = user_message.strip()
            
            # Use regex for reliable extraction
            pattern = r'(?:tell me more about|more about|details about|info about|information about|tell me about)\s+(.+)'
            match = re.search(pattern, user_lower, re.IGNORECASE)
            
            if match:
                place_name = match.group(1).strip()
                print(f"DEBUG: Extracted via regex: '{place_name}'")
            else:
                # Fallback: try phrase removal
                for phrase in ['tell me more about', 'more about', 'details about', 'info about', 'information about', 'tell me about']:
                    if phrase in user_lower:
                        place_name = user_lower.replace(phrase, '').strip()
                        print(f"DEBUG: Extracted via phrase removal: '{place_name}'")
                        break
            
            print(f"DEBUG: Place name to search: '{place_name}'")
            
            # Find matching place in current_places - IMPROVED MATCHING
            matching_place = None
            place_name_lower = place_name.lower()
            
            for place in current_places:
                place_lower = place['name'].lower()
                
                # Try multiple matching strategies
                if (place_name_lower in place_lower or 
                    place_lower in place_name_lower or
                    place_name_lower.replace(' ', '') in place_lower.replace(' ', '') or
                    any(word in place_lower for word in place_name_lower.split() if len(word) > 2)):
                    
                    matching_place = place
                    print(f"DEBUG: Matched place: {place['name']}")
                    break
            
            if matching_place:
                # Generate AI-powered detailed response about this place
                ai_response = generate_ai_place_description(matching_place, location_name)
                
                return JsonResponse({
                    'success': True,
                    'message': ai_response,
                    'places': current_places,  # Return same places
                    'search_params': {'is_detail_query': True, 'query': place_name},
                    'intent_analysis': {'intent_type': 'place_details'},
                    'ai_used': True
                })
            else:
                # Place not found in current list
                place_names = [p['name'] for p in current_places[:3]]
                ai_response = f"I don't have **{place_name}** in the current list. "
                if place_names:
                    ai_response += f"The places I showed you are: {', '.join(place_names)}. "
                ai_response += "Would you like details about any of these?"
                
                return JsonResponse({
                    'success': True,
                    'message': ai_response,
                    'places': current_places,
                    'search_params': {'is_detail_query': True, 'query': place_name},
                    'intent_analysis': {'intent_type': 'place_details'},
                    'ai_used': True
                })
        
        # NOT a detail query - proceed with normal search
        # Analyze user intent with smart detection
        intent_analysis = analyze_user_intent_smart(user_message)
        print(f"DEBUG: Intent analysis: {intent_analysis}")
        
        # Extract search parameters
        search_params = extract_search_params_from_intent(intent_analysis)
        
        # Search for places based on intent
        places = []
        if search_params.get('should_search', True):
            places = search_places_smart(
                lat=lat,
                lng=lng,
                search_params=search_params
            )
            print(f"DEBUG: Found {len(places)} places")
        
        # Generate AI-powered smart response
        ai_response = generate_ai_response_with_context(
            user_message=user_message,
            location_name=location_name,
            places=places,
            search_params=search_params,
            conversation_history=conversation_history
        )
        
        print(f"DEBUG: AI Response: {ai_response[:100]}...")
        
        return JsonResponse({
            'success': True,
            'message': ai_response,
            'places': places,
            'search_params': search_params,
            'intent_analysis': intent_analysis,
            'ai_used': True
        })
        
    except Exception as e:
        print(f"ERROR in chat_with_ai: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
    
@csrf_exempt
@require_http_methods(["POST"])
def get_place_details_with_navigation(request):
    """
    Get detailed place information including navigation URLs
    """
    try:
        data = json.loads(request.body)
        place_id = data.get('place_id')
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        if not place_id:
            return JsonResponse({'success': False, 'error': 'Missing place_id'}, status=400)
        
        # Get detailed place information
        place_details = get_place_details(place_id)
        
        if place_details:
            # Generate navigation URLs
            place_lat = place_details.get('geometry', {}).get('location', {}).get('lat')
            place_lng = place_details.get('geometry', {}).get('location', {}).get('lng')
            
            navigation_urls = generate_navigation_urls(lat, lng, place_lat, place_lng)
            
            # Format the response
            response = {
                'success': True,
                'place': {
                    'name': place_details.get('name', ''),
                    'address': place_details.get('formatted_address', ''),
                    'phone': place_details.get('formatted_phone_number', 'Not available'),
                    'website': place_details.get('website', ''),
                    'rating': place_details.get('rating', 0),
                    'total_ratings': place_details.get('user_ratings_total', 0),
                    'price_level': place_details.get('price_level'),
                    'price_text': get_price_text(place_details.get('price_level')),
                    'opening_hours': place_details.get('opening_hours', {}).get('weekday_text', []),
                    'photos': place_details.get('photos', []),
                    'location': {
                        'lat': place_lat,
                        'lng': place_lng
                    },
                    'navigation': navigation_urls
                }
            }
        else:
            response = {'success': False, 'error': 'Place not found'}
        
        return JsonResponse(response)
        
    except Exception as e:
        print(f"ERROR in get_place_details_with_navigation: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ==================== GEMINI AI FUNCTIONS ====================

def generate_ai_greeting(username, location_name):
    """Generate AI-powered greeting with local insights"""
    try:
        if gemini_model:
            # Get current time for context
            hour = datetime.now().hour
            if hour < 12:
                time_of_day = "morning"
            elif hour < 17:
                time_of_day = "afternoon"
            elif hour < 21:
                time_of_day = "evening"
            else:
                time_of_day = "night"
            
            prompt = f"""
            You are a friendly travel assistant. Create a warm, engaging welcome message for:
            
            Traveler name: {username}
            Location: {location_name}
            Time of day: {time_of_day}
            
            Requirements:
            1. Start with a time-appropriate greeting
            2. Mention the location in a positive way
            3. Include one interesting fact about {location_name} if you know any
            4. Express excitement about helping them explore
            5. Use 1-2 relevant emojis naturally
            6. Keep it under 80 words
            7. Sound enthusiastic but not overly formal
            
            Example style: "Good morning Sarah! 🌟 Welcome to Chennai - the cultural capital of South India! Did you know it's famous for its beautiful beaches and filter coffee? I'm excited to help you explore this amazing city!"
            
            Now create your greeting:
            """
            
            response = gemini_model.generate_content(prompt)
            greeting = response.text.strip()
            
            # Ensure username is included
            if username and username.lower() not in greeting.lower():
                greeting = f"Hello {username}! {greeting}"
                
            return greeting
    except Exception as e:
        print(f"DEBUG: AI greeting failed, using fallback: {e}")
    
    # Fallback to rule-based greeting
    return generate_smart_greeting_fallback(username, location_name)

def generate_ai_place_description(place, location_name):
    """Generate AI description of a place"""
    try:
        if gemini_model:
            # Prepare place details
            place_details = {
                'name': place.get('name', 'Unknown Place'),
                'address': place.get('address', 'Address not available'),
                'rating': place.get('rating', 'Not rated'),
                'total_ratings': place.get('total_ratings', 0),
                'price': place.get('price_text', 'Price information not available'),
                'distance': place.get('distance_text', 'Distance not available'),
                'status': 'Open 🟢' if place.get('open_now') else 'Closed 🔴' if place.get('open_now') is not None else 'Hours not available',
                'phone': place.get('phone', 'Not available'),
                'website': place.get('website', 'Not available')
            }
            
            prompt = f"""
            You are a knowledgeable local guide in {location_name}. A traveler is asking for more information about:
            
            Place: {place_details['name']}
            
            Details:
            - Address: {place_details['address']}
            - Rating: {place_details['rating']}/5 stars ({place_details['total_ratings']} reviews)
            - Price: {place_details['price']}
            - Distance: {place_details['distance']} away
            - Status: {place_details['status']}
            - Phone: {place_details['phone']}
            - Website: {place_details['website']}
            
            Create a helpful, engaging description with:
            1. A friendly introduction to the place
            2. Key highlights (rating, price, distance)
            3. Practical information (status, contact)
            4. A recommendation or tip about visiting
            5. End with an open-ended question to continue conversation
            6. Use natural language with occasional emojis
            7. Keep it conversational (150-200 words)
            
            Make it sound like you're personally recommending this place to a friend!
            """
            
            response = gemini_model.generate_content(prompt)
            return response.text.strip()
    except Exception as e:
        print(f"DEBUG: AI place description failed: {e}")
        # Fallback to rule-based description
        return generate_place_description_fallback(place)

def generate_ai_response_with_context(user_message, location_name, places, search_params, conversation_history):
    """Generate AI response using Gemini with full context"""
    try:
        if gemini_model:
            # Prepare places information
            places_info = ""
            if places:
                places_info = "**Places I found for you:**\n\n"
                for i, place in enumerate(places[:5], 1):
                    places_info += f"{i}. **{place['name']}**\n"
                    places_info += f"   ⭐ Rating: {place.get('rating', 'N/A')}/5"
                    if place.get('total_ratings'):
                        places_info += f" ({place.get('total_ratings')} reviews)"
                    places_info += f"\n   📍 Distance: {place.get('distance_text', 'N/A')}"
                    if place.get('price_text'):
                        places_info += f"\n   💰 Price: {place.get('price_text')}"
                    places_info += "\n\n"
            
            # Prepare conversation context
            convo_context = ""
            if conversation_history and len(conversation_history) > 0:
                convo_context = "**Recent conversation history:**\n"
                # Get last 2-3 exchanges
                for msg in conversation_history[-4:]:
                    role = "Traveler" if msg.get('role') == 'user' else "You"
                    convo_context += f"{role}: {msg.get('content', '')[:100]}...\n"
            
            # Prepare search context
            search_context = f"""
            **Search Context:**
            - User is in: {location_name}
            - Looking for: {search_params.get('query', 'places')}
            - Category: {search_params.get('category', 'general')}
            - Price preference: {search_params.get('price_preference', 'any')}
            - Number of places found: {len(places)}
            """
            
            prompt = f"""
            You are GeoGuide, a friendly and knowledgeable AI travel assistant. You're helping a traveler in {location_name}.
            
            {convo_context}
            
            **Traveler's current request:** "{user_message}"
            
            {search_context}
            
            {places_info if places else "**No specific places found for this query.**"}
            
            **Your response should:**
            1. Acknowledge the traveler's request naturally
            2. If places were found: highlight 2-3 top recommendations with brief reasons why they're good
            3. If no places found: suggest alternatives or ask clarifying questions
            4. Include practical tips (distance, price, current status if available)
            5. Use a warm, enthusiastic tone with occasional emojis
            6. Ask a follow-up question to keep the conversation going
            7. Keep it concise but informative (150-250 words)
            8. Sound like a local friend giving advice
            
            **Important:** Reference specific places by name if available. Don't just list facts - explain why they're good options!
            
            Your response:
            """
            
            response = gemini_model.generate_content(prompt)
            ai_response = response.text.strip()
            
            # Add a note about clicking for more info if we have places
            if places and len(places) > 0:
                ai_response += "\n\n💡 *Click on any place in the sidebar or map for detailed information and directions!*"
            
            return ai_response
    except Exception as e:
        print(f"DEBUG: AI response generation failed: {e}")
        # Fallback to rule-based response
        return generate_smart_response_fallback(user_message, location_name, places, search_params)

# ==================== FALLBACK FUNCTIONS ====================

def generate_smart_greeting_fallback(username, location_name):
    """Fallback greeting function when AI fails"""
    import random
    
    hour = datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 17:
        time_greeting = "Good afternoon"
    elif hour < 21:
        time_greeting = "Good evening"
    else:
        time_greeting = "Good night"
    
    location_tips = {
        'Punjaipuliampatti': "a lovely town in Tamil Nadu",
        'Chennai': "the cultural capital of South India",
        'Bangalore': "India's Silicon Valley",
        'Mumbai': "the city that never sleeps",
        'Delhi': "the heart of India",
        'Kolkata': "the City of Joy",
        'Hyderabad': "famous for its biryani and pearls"
    }
    
    location_desc = location_tips.get(location_name, "your location")
    
    greetings = [
        f"{time_greeting} {username}! 🌟 Welcome to {location_name}, {location_desc}. Ready to explore?",
        f"Hello {username}! 👋 Great to have you in {location_name}. How can I assist you today?",
        f"{time_greeting}! Welcome to {location_name}, {username}. 🗺️ What would you like to discover?",
        f"Hey {username}! 😊 Enjoying {location_name}? Let me help you find amazing local spots!",
        f"{time_greeting} {username}! 🎉 Welcome to {location_name} - let's start your adventure!"
    ]
    
    return random.choice(greetings)

def generate_place_description_fallback(place):
    """Fallback place description function when AI fails"""
    details = [f"**{place['name']}** is located at {place['address']}."]
    
    if place.get('rating'):
        details.append(f"It has a rating of **{place['rating']}/5 ⭐** from {place.get('total_ratings', 0)} reviews.")
    
    if place.get('price_text'):
        details.append(f"Price range: **{place['price_text']}**")
    
    if place.get('open_now') is not None:
        status = "**currently open 🟢**" if place['open_now'] else "**currently closed 🔴**"
        details.append(f"Status: {status}")
    
    if place.get('phone') and place.get('phone') != 'Not available':
        details.append(f"📞 Phone: {place['phone']}")
    
    if place.get('website'):
        details.append(f"🌐 Website: {place['website']}")
    
    if place.get('distance_text'):
        details.append(f"📍 Distance: {place['distance_text']}")
    
    return " ".join(details) + "\n\nWould you like to know about any other place?"

def generate_smart_response_fallback(user_message, location_name, places, search_params):
    """Fallback response function when AI fails"""
    # Get user intent for contextual response
    user_lower = user_message.lower()
    category = search_params.get('category', 'general')
    query = search_params.get('query', '')
    
    # Prepare emoji and tone based on category
    category_emojis = {
        'food': '🍽️',
        'drink': '☕',
        'accommodation': '🏨',
        'entertainment': '🎬',
        'shopping': '🛍️',
        'health': '🏥',
        'services': '🏦',
        'transport': '🚗',
        'recreation': '🌳',
        'recommendation': '⭐',
        'general': '📍'
    }
    
    emoji = category_emojis.get(category, '📍')
    
    if not places:
        # No places found
        no_results_responses = {
            'food': f"{emoji} I couldn't find specific food places in {location_name}. Try searching for 'restaurants' or ask for local cuisine suggestions.",
            'drink': f"{emoji} No specific drink spots found in {location_name}. You might find cafes in restaurants or try asking for 'cafes'.",
            'accommodation': f"{emoji} Couldn't find hotels right in {location_name}. Try searching in nearby towns or increase search radius.",
            'entertainment': f"{emoji} No entertainment venues found in {location_name}. You might find options in larger nearby cities.",
            'shopping': f"{emoji} Couldn't find shopping centers in {location_name}. Try local markets or general stores.",
            'general': f"{emoji} I couldn't find specific places for '{query}' in {location_name}. Try more specific terms like 'restaurants', 'hotels', or 'shops'."
        }
        
        return no_results_responses.get(category, no_results_responses['general'])
    
    # We have places - create detailed response
    num_places = len(places)
    
    # Get top places for recommendation
    top_places = places[:3]  # Top 3 places
    
    # Build response based on number of places found
    if num_places == 1:
        place = places[0]
        rating = place.get('rating', 0)
        distance = place.get('distance_text', 'N/A')
        price = place.get('price_text', '')
        
        response = f"{emoji} Found **{place['name']}** in {location_name}!\n\n"
        response += f"⭐ Rating: {rating}/5\n"
        response += f"📍 Distance: {distance}\n"
        if price:
            response += f"💰 Price: {price}\n"
        response += f"🏠 Address: {place['address']}\n\n"
        response += f"🔗 [Get Directions](javascript:showDirections('{place['place_id']}')) | "
        response += f"📞 [Call](tel:{place.get('phone', '')})\n\n"
        response += "Click on the map marker for more details!"
        
    elif num_places <= 3:
        place_names = [f"**{p['name']}**" for p in top_places]
        names_text = ", ".join(place_names)
        
        response = f"{emoji} Found {num_places} great places in {location_name}!\n\n"
        response += f"**Top recommendations:** {names_text}\n\n"
        
        # Add brief details for each top place
        for i, place in enumerate(top_places, 1):
            rating = place.get('rating', 0)
            distance = place.get('distance_text', 'N/A')
            response += f"{i}. {place['name']} - {rating}/5 ⭐ - {distance} away\n"
        
        response += "\nClick any place on the map or in the sidebar for directions!"
        
    else:  # More than 3 places
        place_names = [f"**{p['name']}**" for p in top_places[:2]]
        names_text = " and ".join(place_names)
        
        response = f"{emoji} Found {num_places} places in {location_name}!\n\n"
        response += f"**Top picks:** {names_text}\n\n"
        
        # Show table of top places
        response += "**Top Recommendations:**\n"
        response += "| Name | Rating | Distance | Price |\n"
        response += "|------|--------|----------|-------|\n"
        
        for place in top_places:
            name = place['name'][:20] + "..." if len(place['name']) > 20 else place['name']
            rating = place.get('rating', 0)
            distance = place.get('distance_text', 'N/A')
            price = place.get('price_text', 'N/A')[:10]
            
            response += f"| {name} | {rating}/5 | {distance} | {price} |\n"
        
        response += f"\n**And {num_places - 3} more options...**\n\n"
        response += "Click any place on the map for directions and details!"
    
    # Add price context if searching for budget
    if search_params.get('price_preference') == 'budget':
        response += "\n\n💰 *Note: Showing budget-friendly options as requested*"
    
    return response

# ==================== HELPER FUNCTIONS ====================

def generate_navigation_urls(user_lat, user_lng, place_lat, place_lng):
    """Generate navigation URLs for different platforms"""
    if not all([user_lat, user_lng, place_lat, place_lng]):
        return {}
    
    # Google Maps URLs
    google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lng}&destination={place_lat},{place_lng}&travelmode=driving"
    google_maps_walking_url = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lng}&destination={place_lat},{place_lng}&travelmode=walking"
    
    # Apple Maps URL
    apple_maps_url = f"http://maps.apple.com/?daddr={place_lat},{place_lng}&saddr={user_lat},{user_lng}"
    
    # Waze URL
    waze_url = f"https://waze.com/ul?ll={place_lat},{place_lng}&navigate=yes"
    
    # OpenStreetMap URL
    osm_url = f"https://www.openstreetmap.org/directions?engine=graphhopper_foot&route={user_lat}%2C{user_lng}%3B{place_lat}%2C{place_lng}"
    
    # Embedded Google Maps iframe URL
    embedded_map_url = f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_API_KEY}&origin={user_lat},{user_lng}&destination={place_lat},{place_lng}&mode=driving"
    
    # Calculate distance and time
    distance_km = calculate_distance(user_lat, user_lng, place_lat, place_lng)
    estimated_time_car = calculate_estimated_time(distance_km, 'driving')
    estimated_time_walk = calculate_estimated_time(distance_km, 'walking')
    
    return {
        'google_maps_drive': google_maps_url,
        'google_maps_walk': google_maps_walking_url,
        'apple_maps': apple_maps_url,
        'waze': waze_url,
        'openstreetmap': osm_url,
        'embedded_map': embedded_map_url,
        'distance_km': round(distance_km, 1),
        'estimated_time': {
            'driving': estimated_time_car,
            'walking': estimated_time_walk
        },
        'directions_text': f"{round(distance_km, 1)} km away • {estimated_time_car} by car • {estimated_time_walk} walking"
    }

def calculate_estimated_time(distance_km, mode='driving'):
    """Calculate estimated travel time"""
    if mode == 'driving':
        # Average speed 40 km/h in city
        minutes = (distance_km / 40) * 60
    elif mode == 'walking':
        # Average walking speed 5 km/h
        minutes = (distance_km / 5) * 60
    else:
        # Default to driving
        minutes = (distance_km / 40) * 60
    
    if minutes < 1:
        return "Less than 1 min"
    elif minutes < 60:
        return f"{int(minutes)} mins"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{hours}h"

def analyze_user_intent_smart(user_message):
    """Smart intent analysis with better keyword matching"""
    user_lower = user_message.lower()
    
    # Expanded intent detection
    intents = {
        # Food & Drink
        'biryani': {'type': 'restaurant', 'query': 'biryani', 'category': 'food'},
        'biriyani': {'type': 'restaurant', 'query': 'biriyani', 'category': 'food'},
        'pizza': {'type': 'restaurant', 'query': 'pizza', 'category': 'food'},
        'coffee': {'type': 'cafe', 'query': 'coffee', 'category': 'drink'},
        'tea': {'type': 'cafe', 'query': 'tea', 'category': 'drink'},
        'restaurant': {'type': 'restaurant', 'query': 'restaurant', 'category': 'food'},
        'food': {'type': 'restaurant', 'query': 'food', 'category': 'food'},
        'dinner': {'type': 'restaurant', 'query': 'dinner', 'category': 'food'},
        'lunch': {'type': 'restaurant', 'query': 'lunch', 'category': 'food'},
        'breakfast': {'type': 'restaurant', 'query': 'breakfast', 'category': 'food'},
        
        # Accommodation
        'hotel': {'type': 'lodging', 'query': 'hotel', 'category': 'accommodation'},
        'stay': {'type': 'lodging', 'query': 'hotel', 'category': 'accommodation'},
        'lodging': {'type': 'lodging', 'query': 'lodging', 'category': 'accommodation'},
        
        # Entertainment
        'movie': {'type': 'movie_theater', 'query': 'cinema', 'category': 'entertainment'},
        'theater': {'type': 'movie_theater', 'query': 'theater', 'category': 'entertainment'},
        'cinema': {'type': 'movie_theater', 'query': 'cinema', 'category': 'entertainment'},
        
        # Recreation
        'park': {'type': 'park', 'query': 'park', 'category': 'recreation'},
        'garden': {'type': 'park', 'query': 'garden', 'category': 'recreation'},
        
        # Shopping
        'mall': {'type': 'shopping_mall', 'query': 'shopping mall', 'category': 'shopping'},
        'shopping': {'type': 'shopping_mall', 'query': 'shopping', 'category': 'shopping'},
        'market': {'type': 'shopping_mall', 'query': 'market', 'category': 'shopping'},
        
        # Health
        'pharmacy': {'type': 'pharmacy', 'query': 'pharmacy', 'category': 'health'},
        'hospital': {'type': 'hospital', 'query': 'hospital', 'category': 'health'},
        'doctor': {'type': 'hospital', 'query': 'hospital', 'category': 'health'},
        
        # Services
        'atm': {'type': 'atm', 'query': 'atm', 'category': 'services'},
        'bank': {'type': 'bank', 'query': 'bank', 'category': 'services'},
        
        # Transportation
        'gas': {'type': 'gas_station', 'query': 'petrol pump', 'category': 'transport'},
        'petrol': {'type': 'gas_station', 'query': 'petrol pump', 'category': 'transport'},
        'bus': {'type': 'bus_station', 'query': 'bus station', 'category': 'transport'},
        
        # General
        'best': {'type': '', 'query': 'popular places', 'category': 'recommendation'},
        'top': {'type': '', 'query': 'best places', 'category': 'recommendation'},
        'recommend': {'type': '', 'query': 'recommended places', 'category': 'recommendation'},
        'popular': {'type': '', 'query': 'popular places', 'category': 'recommendation'},
        'nearby': {'type': '', 'query': 'nearby places', 'category': 'general'},
        'near': {'type': '', 'query': 'places', 'category': 'general'},
        'around': {'type': '', 'query': 'places', 'category': 'general'},
        'places': {'type': '', 'query': 'places', 'category': 'general'},
    }
    
    # Check for intent keywords
    detected_intent = None
    for keyword, intent in intents.items():
        if keyword in user_lower:
            detected_intent = intent
            break
    
    # If no specific intent, extract main words
    if not detected_intent:
        # Remove common words
        common_words = ['find', 'search', 'look', 'for', 'me', 'i', 'want', 'to', 'go', 'the', 'a', 'an', 'and', 'or', 'please', 'can', 'you', 'help', 'show', 'tell']
        words = user_lower.split()
        filtered_words = [word for word in words if word not in common_words and len(word) > 2]
        
        if filtered_words:
            query = ' '.join(filtered_words[:3])  # Take first 3 meaningful words
        else:
            query = 'places'  # Default query
        
        detected_intent = {'type': '', 'query': query, 'category': 'general'}
    
    # Check for price preferences
    price_preference = None
    if any(word in user_lower for word in ['cheap', 'budget', 'low price', 'affordable', 'under', 'less than']):
        price_preference = 'budget'
    elif any(word in user_lower for word in ['expensive', 'luxury', 'premium', 'high end']):
        price_preference = 'expensive'
    
    # Check for distance preferences
    radius_preference = None
    if any(word in user_lower for word in ['nearby', 'close', 'walking', 'within walking']):
        radius_preference = 'nearby'
    elif any(word in user_lower for word in ['far', 'distant', 'drive']):
        radius_preference = 'far'
    
    return {
        'intent_type': 'search_places',
        'place_type': detected_intent['type'],
        'search_query': detected_intent['query'],
        'category': detected_intent['category'],
        'price_preference': price_preference,
        'radius_preference': radius_preference,
        'additional_context': f"looking for {detected_intent['category']} options",
        'should_search': True
    }

def extract_search_params_from_intent(intent_analysis):
    """Convert intent analysis to search parameters"""
    # Map place types to Google Places types
    google_place_types = {
        'restaurant': 'restaurant',
        'cafe': 'cafe',
        'lodging': 'lodging',
        'park': 'park',
        'shopping_mall': 'shopping_mall',
        'movie_theater': 'movie_theater',
        'pharmacy': 'pharmacy',
        'hospital': 'hospital',
        'atm': 'atm',
        'bank': 'bank',
        'gas_station': 'gas_station',
        'bus_station': 'bus_station',
        '': ''  # Empty for general search
    }
    
    place_type = intent_analysis.get('place_type', '')
    google_type = google_place_types.get(place_type, '')
    
    # Set radius based on preference
    radius_mapping = {
        'nearby': 2000,      # 2km
        'far': 20000,        # 20km
        None: 10000          # 10km default
    }
    radius = radius_mapping.get(intent_analysis.get('radius_preference'), 10000)
    
    return {
        'query': intent_analysis.get('search_query', ''),
        'type': google_type,
        'place_type': place_type,
        'category': intent_analysis.get('category', 'general'),
        'price_preference': intent_analysis.get('price_preference'),
        'radius': radius,
        'additional_context': intent_analysis.get('additional_context', ''),
        'should_search': True
    }

def search_places_smart(lat, lng, search_params):
    """Smart place search with better filtering and results"""
    try:
        query = search_params.get('query', '')
        place_type = search_params.get('type', '')
        radius = search_params.get('radius', 50000)
        category = search_params.get('category', 'general')
        
        print(f"DEBUG: Smart search - lat: {lat}, lng: {lng}, query: '{query}', type: '{place_type}', category: '{category}'")
        
        # Build Google Places API request
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        params = {
            'location': f'{lat},{lng}',
            'radius': min(radius, 50000),  # Max 50km
            'key': GOOGLE_MAPS_API_KEY,
            'rankby': 'prominence'
        }
        
        # Add type if specified
        if place_type:
            params['type'] = place_type
        
        # Add keyword if provided and not too generic
        if query and query not in ['places', 'popular places', 'best places', 'recommended places', 'nearby places']:
            params['keyword'] = query
        
        print(f"DEBUG: Places API params: {params}")
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        print(f"DEBUG: Places API status: {data.get('status')}")
        print(f"DEBUG: Initial results: {len(data.get('results', []))}")
        
        places = []
        
        for place in data.get('results', [])[:20]:  # Get more results for better filtering
            place_id = place.get('place_id')
            
            # Get detailed place information
            place_details = get_place_details(place_id) if place_id else {}
            
            # Get price level (handle None)
            price_level = place.get('price_level')
            if price_level is None:
                price_level = place_details.get('price_level')
            
            # Calculate distance
            place_lat = place['geometry']['location']['lat']
            place_lng = place['geometry']['location']['lng']
            distance = calculate_distance(lat, lng, place_lat, place_lng)
            
            # Filter by distance (max 30km for practicality)
            if distance > 30:
                continue
            
            # Get photo URL if available
            photo_url = None
            if place.get('photos'):
                try:
                    photo_reference = place['photos'][0]['photo_reference']
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
                except:
                    pass
            
            # Get rating (handle None)
            rating = place.get('rating')
            if rating is None:
                rating = place_details.get('rating', 0)
            
            # Get total ratings
            total_ratings = place.get('user_ratings_total', 0)
            if total_ratings == 0:
                total_ratings = place_details.get('user_ratings_total', 0)
            
            # Check if open
            open_now = place_details.get('opening_hours', {}).get('open_now')
            
            # Get price text
            price_text = get_price_text(price_level)
            
            # Apply price filter if specified in search params
            price_preference = search_params.get('price_preference')
            if price_preference == 'budget' and price_level is not None and price_level > 2:
                continue  # Skip expensive places for budget search
            
            # Build place info
            place_info = {
                'name': place.get('name', 'Unnamed Place'),
                'address': place.get('vicinity', 'Address not available'),
                'rating': rating,
                'total_ratings': total_ratings,
                'price_level': price_level,
                'price_text': price_text,
                'location': place['geometry']['location'],
                'place_id': place_id,
                'types': place.get('types', []),
                'photo_url': photo_url,
                'open_now': open_now,
                'phone': place_details.get('formatted_phone_number', 'Not available'),
                'website': place_details.get('website', ''),
                'distance_km': round(distance, 2),
                'distance_text': get_distance_text(distance),
                'popularity_score': calculate_popularity_score(rating, total_ratings, distance, category),
                'navigation_url': generate_navigation_urls(lat, lng, place_lat, place_lng)
            }
            
            places.append(place_info)
        
        # Sort by popularity score (combination of rating, reviews, and distance)
        places.sort(key=lambda x: x.get('popularity_score', 0), reverse=True)
        
        # Return top results (with variety)
        filtered_places = []
        seen_names = set()
        
        for place in places:
            name = place['name'].lower()
            if name not in seen_names and len(filtered_places) < 8:
                seen_names.add(name)
                filtered_places.append(place)
        
        print(f"DEBUG: Returning {len(filtered_places)} filtered places")
        return filtered_places
        
    except Exception as e:
        print(f"ERROR in search_places_smart: {e}")
        import traceback
        traceback.print_exc()
        return []

def calculate_popularity_score(rating, total_ratings, distance_km, category='general'):
    """Calculate a popularity score for sorting"""
    # Handle None values safely
    if rating is None:
        rating = 0
    if total_ratings is None:
        total_ratings = 0
    
    # Normalize rating (0-5 scale)
    rating_score = (rating / 5.0) * 40  # Max 40 points
    
    # Normalize review count (log scale since reviews vary widely)
    if total_ratings > 0:
        review_score = min(30, (total_ratings ** 0.5))  # Square root scaling
    else:
        review_score = 0
    
    # Distance penalty (closer is better)
    if distance_km < 1:
        distance_score = 30
    elif distance_km < 3:
        distance_score = 25
    elif distance_km < 5:
        distance_score = 20
    elif distance_km < 10:
        distance_score = 15
    elif distance_km < 20:
        distance_score = 10
    else:
        distance_score = 5
    
    # Category bonus (prefer places matching the search category)
    category_bonus = 0
    if category in ['food', 'restaurant'] and 'restaurant' in category:
        category_bonus = 5
    
    return rating_score + review_score + distance_score + category_bonus

def get_location_name_google(lat, lng):
    """Get location name from coordinates"""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f'{lat},{lng}',
            'key': GOOGLE_MAPS_API_KEY,
            'language': 'en'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == 'OK' and data.get('results'):
            result = data['results'][0]
            
            # Try to get locality first
            for component in result['address_components']:
                if 'locality' in component['types']:
                    return component['long_name']
                if 'administrative_area_level_2' in component['types']:
                    return component['long_name']
                if 'administrative_area_level_1' in component['types']:
                    return component['long_name']
            
            # Fallback to formatted address
            formatted_address = result.get('formatted_address', '')
            if formatted_address:
                # Take first part of address
                return formatted_address.split(',')[0].strip()
        
        return "your location"
        
    except Exception as e:
        print(f"ERROR in get_location_name_google: {e}")
        return "your location"

def get_place_details(place_id):
    """Get detailed information for a specific place"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'key': GOOGLE_MAPS_API_KEY,
            'fields': 'name,formatted_address,formatted_phone_number,website,price_level,rating,user_ratings_total,opening_hours,geometry,photos,types'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == 'OK':
            return data.get('result', {})
        
        return {}
        
    except Exception as e:
        print(f"ERROR in get_place_details: {e}")
        return {}

def get_price_text(price_level):
    """Convert price level to text"""
    if price_level is None:
        return 'Price not available'
    
    price_map = {
        0: 'Free',
        1: 'Very affordable (under ₹200)',
        2: 'Moderate (₹200-500)',
        3: 'Expensive (₹500-1000)',
        4: 'Premium (₹1000+)'
    }
    return price_map.get(price_level, 'Price varies')

def get_distance_text(distance_km):
    """Convert distance to readable text"""
    if distance_km < 1:
        meters = int(distance_km * 1000)
        return f"{meters}m"
    elif distance_km < 10:
        return f"{round(distance_km, 1)}km"
    else:
        return f"{int(distance_km)}km"

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate approximate distance between two coordinates in kilometers"""
    # Convert to radians
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    
    # Haversine formula
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Earth's radius in kilometers
    R = 6371
    return R * c

# ==================== TEST ENDPOINTS ====================

@csrf_exempt
def test_api_status(request):
    """Test if APIs are working"""
    results = {
        'server': 'Running',
        'google_maps': 'Testing...',
        'gemini_ai': 'Testing...',
        'version': '2.0.0',
        'features': ['AI-Powered Chat', 'Smart Search', 'Location Detection', 'Place Recommendations', 'Navigation']
    }
    
    # Test Google Maps
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': 'Punjaipuliampatti',
            'key': GOOGLE_MAPS_API_KEY
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        results['google_maps'] = {
            'status': data.get('status'),
            'working': data.get('status') == 'OK'
        }
    except Exception as e:
        results['google_maps'] = {
            'status': 'Error',
            'error': str(e)
        }
    
    # Test Gemini AI
    try:
        if gemini_model:
            test_prompt = "Say 'Gemini AI is working!' in a friendly way."
            response = gemini_model.generate_content(test_prompt)
            results['gemini_ai'] = {
                'status': 'Working',
                'response': response.text[:100],
                'model': 'gemini-pro'
            }
        else:
            results['gemini_ai'] = {
                'status': 'Not configured',
                'error': 'Gemini model not initialized'
            }
    except Exception as e:
        results['gemini_ai'] = {
            'status': 'Error',
            'error': str(e)
        }
    
    # Test sample search
    try:
        test_lat, test_lng = 11.336198, 77.149347
        location_name = get_location_name_google(test_lat, test_lng)
        results['sample_search'] = {
            'location': location_name,
            'coordinates': f"{test_lat}, {test_lng}"
        }
    except Exception as e:
        results['sample_search'] = {'error': str(e)}
    
    return JsonResponse(results)

# Clear conversation endpoint
@csrf_exempt
def clear_conversation(request):
    """Clear conversation history (placeholder)"""
    return JsonResponse({
        'success': True,
        'message': 'Conversation cleared',
        'timestamp': time.time()
    })

# Enhanced search endpoint
@csrf_exempt
@require_http_methods(["POST"])
def enhanced_search(request):
    """Enhanced search with better query handling"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        if not query or not lat or not lng:
            return JsonResponse({'success': False, 'error': 'Missing data'}, status=400)
        
        location_name = get_location_name_google(lat, lng)
        
        # Use the smart intent analysis
        intent_analysis = analyze_user_intent_smart(query)
        search_params = extract_search_params_from_intent(intent_analysis)
        
        # Perform the search
        places = search_places_smart(lat, lng, search_params)
        
        # Generate AI response
        response_text = generate_ai_response_with_context(
            user_message=query,
            location_name=location_name,
            places=places,
            search_params=search_params,
            conversation_history=[]
        )
        
        return JsonResponse({
            'success': True,
            'message': response_text,
            'places': places,
            'location': location_name,
            'count': len(places),
            'query': query
        })
        
    except Exception as e:
        print(f"ERROR in enhanced_search: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# Test Gemini endpoint
@csrf_exempt
def test_gemini(request):
    """Test Gemini AI directly"""
    try:
        if not gemini_model:
            return JsonResponse({
                'success': False,
                'error': 'Gemini AI not configured'
            })
        
        prompt = "Hello! I'm testing the Gemini AI integration. Can you respond with a friendly greeting and tell me you're ready to help travelers explore new places?"
        
        response = gemini_model.generate_content(prompt)
        
        return JsonResponse({
            'success': True,
            'response': response.text,
            'model': 'gemini-pro',
            'timestamp': time.time()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
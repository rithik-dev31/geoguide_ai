# GeoGuide AI - Complete README

## Project Overview

**GeoGuide AI** is a Django-based web application that combines Google Maps integration with AI-powered place recommendations using Google's Gemini API. The application provides an interactive chat interface where users can ask about nearby places, and the AI assistant delivers intelligent recommendations based on location and context.

## Features

- **Interactive Map Integration**: Real-time Google Maps display with geolocation support
- **AI-Powered Chat**: Conversational interface powered by Google Gemini API
- **Smart Place Discovery**: Intelligent place recommendations based on user queries
- **Location-Based Services**: Automatic user location detection and place search
- **Responsive UI**: Modern, user-friendly interface with real-time updates
- **Chat History**: Test and clear functionality for chat management

## Technology Stack

### Backend
- **Framework**: Django 5.2.10
- **Language**: Python 3.7+
- **Database**: SQLite3 (development)
- **API Integration**: Google Gemini AI, Google Places API, Google Maps API

### Frontend
- **Markup**: HTML5
- **Styling**: CSS3
- **Scripting**: Vanilla JavaScript
- **Mapping**: Google Maps JavaScript API

### Dependencies
See [requirements.txt](requriments.txt) for complete package list including:
- `google-generativeai`: Gemini API client
- `django`: Web framework
- `google-api-client`: Google API integration
- `pydantic`: Data validation

## Project Structure

```
geoguide/
├── manage.py                 # Django management utility
├── db.sqlite3               # Development database
├── geoguide/                # Project configuration
│   ├── settings.py          # Django settings & configuration
│   ├── urls.py              # Root URL routing
│   ├── wsgi.py              # WSGI deployment entry point
│   └── asgi.py              # ASGI deployment entry point
└── app/                     # Main application
    ├── admin.py             # Admin panel configuration
    ├── apps.py              # App configuration
    ├── models.py            # Database models
    ├── views.py             # Business logic & API endpoints
    ├── urls.py              # App-level URL routing
    ├── tests.py             # Unit tests
    └── templates/
        └── home.html        # Main UI with maps & chat
```

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Step 1: Clone & Navigate
```bash
git clone https://github.com/rithik-dev31/caremate.git
cd geoguide
```

### Step 2: Create Virtual Environment
```bash
# On Windows
python -m venv env
env\Scripts\activate

# On macOS/Linux
python3 -m venv env
source env/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requriments.txt
```

### Step 4: Configure API Keys

Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

### Step 5: Initialize Database
```bash
python manage.py migrate
python manage.py createsuperuser  # Create admin user (optional)
```

### Step 6: Run Development Server
```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

## API Endpoints

### Chat Endpoint
```
POST /api/chat/
```
**Request Body:**
```json
{
  "message": "Find coffee shops near me",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

**Response:**
```json
{
  "response": "Here are some great coffee shops near you...",
  "places": [
    {
      "name": "Coffee Shop Name",
      "address": "123 Main St",
      "rating": 4.5
    }
  ]
}
```

### Enhanced Search Endpoint
```
POST /api/search/
```
**Request Body:**
```json
{
  "query": "restaurants",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "radius": 5000
}
```

### Place Details Endpoint
```
GET /api/place/<place_id>/
```

### Location Greeting Endpoint
```
POST /api/location-greeting/
```
**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

## Usage Guide

### For Users
1. **Allow Location Access**: Grant browser permission to access your location
2. **Interact with Chat**: Type questions about nearby places
3. **View Results**: See recommended places displayed on the map
4. **Explore Details**: Click on places for more information

### Example Queries
- "Find me a good restaurant"
- "Show me nearby parks"
- "What coffee shops are around here?"
- "Find museums in walking distance"

## Configuration

### Django Settings

Key settings in `geoguide/settings.py`:
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',  # Your app
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Accessing Admin Panel
```
URL: http://localhost:8000/admin
```

## Deployment

### Using Gunicorn + Nginx
```bash
# Install Gunicorn
pip install gunicorn

# Run application
gunicorn geoguide.wsgi:application --bind 0.0.0.0:8000
```

### Environment Variables for Production
```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
SECRET_KEY=your_secret_key_here
DATABASE_URL=postgresql://user:password@host:port/dbname
```

## Troubleshooting

### Issue: "API key not found"
**Solution**: Ensure `.env` file is properly configured with all required API keys

### Issue: "Location permission denied"
**Solution**: Check browser permissions and ensure HTTPS is used in production

### Issue: "Database errors"
**Solution**: Run migrations again:
```bash
python manage.py migrate
```

## Performance Optimization

- **Caching**: Implement Redis for chat history and frequently accessed places
- **API Rate Limiting**: Configure rate limiting for API endpoints
- **Database Indexing**: Add indexes on frequently queried fields
- **Static Files**: Collect and serve static files efficiently

## Security Considerations

- ✅ CSRF protection enabled
- ✅ SQL injection prevention through Django ORM
- ✅ XSS protection in templates
- ✅ API key validation on server-side
- ⚠️ Always use HTTPS in production
- ⚠️ Keep SECRET_KEY secure and unique per environment

## License

This project is licensed under the GPLv3 License - see the [licence](licence) file for details.

## Support & Contribution

### Reporting Issues
Please report bugs and feature requests through the project's issue tracker.

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Changelog

### Version 1.0.0
- Initial release with core features
- Google Maps integration
- Gemini AI chat interface
- Place recommendations
- Location-based services

## Contact & Support

For questions, suggestions, or support, please create an issue in the repository or contact the development team.

---

**Happy exploring with GeoGuide AI! 🗺️✨**

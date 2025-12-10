🍕 FoodExpress WhatsApp Order Chatbot

AI-Powered Food Ordering System via WhatsApp with Voice Recognition & Location-Based Routing

https://img.shields.io/badge/Python-3.12.10-blue.svg

https://img.shields.io/badge/FastAPI-0.104.1-green.svg

https://img.shields.io/badge/WhatsApp-GREEN--API-success.svg

https://img.shields.io/badge/License-MIT-yellow.svg

🎯 What is FoodExpress?
FoodExpress is an intelligent WhatsApp chatbot that allows customers to order food naturally using text, voice messages, or interactive buttons. The system automatically detects customer locations, finds the nearest restaurant branch, processes orders using AI, and provides real-time updates - all within WhatsApp!

✨ Key Features
🗣️ Multiple Ordering Methods
Text Messages: Type orders naturally (e.g., "2 chai 1 samosa")

Voice Messages: Speak your order - AI converts speech to text

Interactive Buttons: Quick replies for faster ordering

🧠 AI-Powered Intelligence
Natural Language Processing (NLP) to understand food orders

Multilingual support (English, Urdu, Hindi, Roman Urdu)

Fuzzy matching for menu items and quantities

Intent detection for order tracking, menu requests, etc.

📍 Smart Location Services
Automatic location detection from WhatsApp

Find nearest restaurant branch using Haversine formula

Geocoding via OpenStreetMap (100% free)

Nearby restaurant discovery

🎤 Voice Order System
Free HuggingFace Wav2Vec2 voice recognition

Google Speech Recognition fallback

Audio recording via Streamlit interface

Voice order confirmation flow

📱 Complete Management System
Customer order history and tracking

Restaurant branch management

Menu management with categories

Real-time order dashboard

Conversation analytics

🚀 Quick Start
Prerequisites
Python 3.12.10

WhatsApp Business Account

GREEN-API Account (free tier available)

Installation
Clone the repository

bash
git clone https://github.com/yourusername/foodexpress-whatsapp-bot.git
cd foodexpress-whatsapp-bot
Install dependencies

bash
pip install -r requirements.txt
Setup environment variables

bash
cp .env.example .env
# Edit .env with your credentials
Initialize database

bash
python setup_database.py
Run the servers

bash
# Terminal 1: FastAPI Backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit Admin Interface
streamlit run streamlit_app.py
Access Points
🌐 API Server: http://localhost:8000

📚 API Documentation: http://localhost:8000/docs

🎛️ Admin Dashboard: http://localhost:8501

📱 How to Use
For Customers
Save the bot number in your WhatsApp contacts

Send "Hello" to start the conversation

Place order via text or voice message

Share location when prompted

Confirm order and track status

For Restaurant Managers
Access Streamlit Dashboard at http://localhost:8501

Manage menu items and prices

View live orders and assign branches

Monitor customer conversations

Track order statistics and analytics

🏗️ Architecture
text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WhatsApp      │────▶   FastAPI       │────▶   NLP Engine    │
│   Customer      │    │   Webhook       │    │   (HuggingFace) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                            │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │────▶   Database      │◀───▶   Order         │
│   Admin Panel   │    │   (SQLite)      │    │   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                            │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GREEN-API     │◀───▶   Location      │◀───▶   Voice         │
│   WhatsApp API  │    │   Service       │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
🔧 Technology Stack
Component	Technology	Purpose
Backend	FastAPI, Python 3.12.10	High-performance API server
Database	SQLite/PostgreSQL	Data storage and management
NLP	HuggingFace Transformers	Understanding customer messages
Voice	Wav2Vec2, Whisper, Google Speech	Speech-to-text conversion
Location	OpenStreetMap, Haversine	Geocoding and distance calculation
WhatsApp	GREEN-API	WhatsApp Business API integration
Frontend	Streamlit	Admin dashboard and demo interface
Maps	OpenStreetMap, Folium	Interactive maps and location display
📁 Project Structure
text
foodexpress-whatsapp-bot/
├── app/                          # FastAPI Application
│   ├── main.py                   # Entry point
│   ├── models/                   # Database models
│   ├── services/                 # Business logic
│   ├── routers/                  # API endpoints
│   └── utils/                    # Helper functions
├── streamlit_app.py              # Admin dashboard
├── requirements.txt              # Python dependencies
├── setup_database.py             # Database initialization
├── run_app.py                    # Launch script
├── .env                          # Environment variables
├── README.md                     # This file
└── data/                         # Data storage
    ├── scraped_menu.json         # Menu data
    └── whatsapp_food.db          # SQLite database
🔌 Integrations
WhatsApp Integration
GREEN-API for WhatsApp Business

Real-time message webhooks

Interactive button messages

Location sharing support

Media message handling

AI & ML Services
HuggingFace Models for NLP and speech

OpenStreetMap for geocoding

Google Speech Recognition (fallback)

Payment Gateways (Future)
Stripe/PayPal integration planned

Local payment methods (EasyPaisa/JazzCash)

📊 Database Schema
text
┌──────────┐      ┌──────────┐      ┌────────────┐
│  Users   │─────▶│  Orders  │─────▶│ OrderItems │
└──────────┘      └──────────┘      └────────────┘
      │                 │
      ▼                 ▼
┌──────────┐      ┌──────────┐
│Conversa- │      │ Branches │
│  tions   │      └──────────┘
└──────────┘            │
                   ┌──────────┐
                   │ MenuItems│
                   └──────────┘
🛠️ API Endpoints
Core Endpoints
POST /api/v1/webhook - WhatsApp webhook handler

GET /api/v1/conversations/{phone} - Get conversation history

GET /api/v1/orders/{phone} - Get order history

POST /api/v1/voice/transcribe - Voice processing

Health Checks
GET /health - Basic health check

GET /system-health - Detailed system status

GET /api-status - API status and endpoints

🎮 Demo Scenarios
Scenario 1: Text Order
text
Customer: "2 zinger burger 1 coke"
Bot: "Great! Please share your location"
Customer: [Shares location]
Bot: "Nearest branch: FoodExpress Karachi (1.2km). Total: Rs. 1100. Confirm?"
Customer: "confirm"
Bot: "Order confirmed! ETA: 30 minutes"
Scenario 2: Voice Order
text
Customer: [Records voice: "2 chai 1 samosa"]
Bot: "Voice order received! Please provide delivery address"
Customer: [Enters address in Streamlit]
Bot: "Order confirmed! Your tea and samosa will arrive in 25 minutes"
Scenario 3: Nearby Restaurants
text
Customer: "restaurants near me"
Bot: "📍 Restaurants near Gulshan-e-Iqbal:
      1. FoodExpress Tariq Road (1.2km)
      2. Cafe Wagera (0.8km)
      3. Pizza Hut (2.1km)
      Type number to order"
🔒 Security Features
Environment variables for sensitive data

Input validation and sanitization

SQL injection prevention via SQLAlchemy

Rate limiting for API endpoints

Secure credentials management

🚀 Deployment Options
Local Development
bash
python -m uvicorn app.main:app --reload
streamlit run streamlit_app.py
Docker Deployment
bash
docker build -t foodexpress-bot .
docker run -p 8000:8000 -p 8501:8501 foodexpress-bot
Cloud Deployment (AWS/Azure/GCP)
Use Docker containers

Configure environment variables

Setup database (PostgreSQL recommended)

Configure SSL certificates

Setup monitoring and logging

🐛 Troubleshooting
Common Issues
WhatsApp not connecting

Check GREEN-API credentials in .env

Verify WhatsApp Business account setup

Ensure webhook URL is accessible

Voice recognition not working

Check internet connection for model download

Ensure microphone permissions

Try speaking clearly in English

Database errors

Run python setup_database.py

Check SQLite file permissions

Verify database path in .env

Location services failing

Check OpenStreetMap API access

Verify address format

Test with known locations (e.g., "Karachi, Pakistan")

Debug Tools
API Documentation: http://localhost:8000/docs

Health Check: http://localhost:8000/health

System Status: http://localhost:8000/system-health

📈 Future Roadmap
Short Term (Q1 2024)
Payment gateway integration

Advanced analytics dashboard

SMS order confirmations

Multi-language menu support

Medium Term (Q2 2024)
Mobile app development

Loyalty program integration

AI-based recommendations

Delivery tracking system

Long Term (Q3 2024+)
Multi-restaurant marketplace

Advanced AI chatbots

Predictive ordering

IoT kitchen integration

🤝 Contributing
We welcome contributions! Please follow these steps:

Fork the repository

Create a feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add AmazingFeature')

Push to branch (git push origin feature/AmazingFeature)

Open a Pull Request

Development Guidelines
Follow PEP 8 coding standards

Write comprehensive docstrings

Add tests for new features

Update documentation accordingly

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
HuggingFace for free AI models

OpenStreetMap for free geocoding services

GREEN-API for WhatsApp Business API

FastAPI community for excellent documentation

All contributors and testers

📞 Support & Contact
For support, feature requests, or questions:

Email: support@foodexpress.com

WhatsApp: +92 300 1234567

Issues: GitHub Issues

Documentation: API Docs



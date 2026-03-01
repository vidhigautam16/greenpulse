# 🌿 GreenPulse — Real-Time Carbon Intelligence

An AI-powered environmental intelligence platform that monitors air quality in real time and delivers policy-aware insights using streaming data + RAG-based AI.

Built for sustainability, real-time processing, and climate-tech innovation.

---

## 🚀 Project Overview

GreenPulse is a production-ready environmental monitoring system that:

- Streams live AQI data from Indian cities
- Processes real-time environmental metrics
- Uses AI (RAG + Gemini) to answer pollution-related questions
- Provides a lightweight, responsive dashboard

Unlike traditional systems that rely on historical reports, GreenPulse enables proactive environmental awareness.

---

## 🌍 Key Features

### 📡 Live Environmental Monitoring
- Real-time AQI streaming (WAQI API)
- Multi-city support (Delhi, Mumbai, Kolkata, Chennai, Prayagraj)
- Tracks PM2.5, PM10, CO₂, NO₂, SO₂, O₃
- Rolling window analytics (5, 15, 60 minutes)

### 🤖 AI-Powered Policy Insights
- Retrieval-Augmented Generation (RAG)
- LangChain + Vector embeddings
- Context from Indian environmental policies (NCAP, GRAP, Green Bharat Mission)
- Ask questions like:
  - “Why is Delhi AQI rising?”
  - “What action does GRAP suggest for AQI above 300?”

### 📊 Responsive Dashboard
- Mobile + Desktop friendly
- Real-time charts & metrics
- Lightweight frontend
- WebSocket streaming updates

### ⚡ Production Ready Architecture
- FastAPI backend
- WebSocket live data
- Streaming AI responses (SSE)
- Easily deployable (Replit / Local / Cloud)

---

## 🛠️ Tech Stack

- Python
- FastAPI
- Pathway (real-time streaming)
- LangChain
- Google Gemini API
- WAQI API
- HTML / JS frontend
- WebSockets

---

## 📦 Setup Guide (3 Steps)

### 1️⃣ Get API Keys

WAQI Token:  
https://aqicn.org/data-platform/token/

Google Gemini API Key:  
https://makersuite.google.com/app/apikey

---

### 2️⃣ Configure Environment

```bash
cp .env.example .env
```

Open `.env` and add:

```env
WAQI_TOKEN=your_waqi_token_here
GOOGLE_API_KEY=your_google_api_key_here
```

---

### 3️⃣ Run the Application

```bash
pip install -r requirements.txt
pip install pathway
python run.py
```

Open in browser:

```
http://localhost:8000/app
```

---

## 📁 Project Structure

```
greenpulse/
│
├── run.py
├── requirements.txt
├── .env.example
│
├── backend/
│   ├── main.py
│   ├── pathway_stream.py
│   └── rag.py
│
└── frontend/
    └── index.html
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|------------|
| `/` | GET | Service Info |
| `/app` | GET | Dashboard UI |
| `/api/snapshot` | GET | Current AQI snapshot |
| `/api/cities` | GET | List available cities |
| `/api/cities/select` | POST | Update active cities |
| `/api/chat` | POST | Ask AI (full response) |
| `/api/chat/stream` | POST | AI streaming response |
| `/ws/stream` | WebSocket | Real-time data stream |

---

## 💡 Use Cases

- Smart city environmental dashboards
- NGO pollution awareness platforms
- AI-assisted climate policy understanding
- Real-time sustainability monitoring tools

---

## 🔮 Future Enhancements

- Predictive AQI modeling
- Carbon emission estimation layer
- Alert system for critical AQI levels
- Government integration APIs
- Deployment with Docker + CI/CD

---

## 🤝 Contributing

Pull requests are welcome.  
If you'd like to improve features or add new cities, feel free to contribute.

---

## 📜 License

Open-source for educational and sustainability innovation purposes.

---

## 🌱 Vision

GreenPulse transforms environmental monitoring from reactive reporting to proactive climate intelligence.

Real-time data + AI = Smarter sustainability decisions.

# 🚀 LLM Phone Feedback System

A comprehensive AI-powered system for conducting phone surveys and knowledge base queries through multiple channels including voice calls, SMS, and WhatsApp messaging.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### 🎯 Core Features
- **Multi-Channel Communication**: Voice calls, SMS, and WhatsApp
- **AI-Powered Survey Management**: Create and manage intelligent surveys
- **Knowledge Base Integration**: RAG-based document querying
- **Real-time Sentiment Analysis**: Advanced NLP processing
- **Campaign Analytics**: Comprehensive success rate tracking
- **User Management**: Secure authentication with Clerk

### 🤖 AI/ML Capabilities
- **Large Language Models**: OpenAI GPT integration
- **Retrieval-Augmented Generation (RAG)**: Document-based Q&A
- **Sentiment Analysis**: Multi-level emotional insights
- **Vector Embeddings**: Semantic document search
- **Context Management**: Intelligent conversation handling

### 📊 Analytics & Insights
- Success rate calculation: `(Completed Calls / Total Calls) × 100`
- Real-time call status tracking
- Sentiment trend analysis
- Response quality metrics

## 🛠 Tech Stack

### Frontend
- **React.js** - UI Framework
- **Tailwind CSS** - Styling
- **Clerk** - Authentication
- **Lucide React** - Icons
- **React Router** - Navigation

### Backend
- **FastAPI** - Python API Framework
- **Uvicorn** - ASGI Server
- **Pydantic** - Data Validation
- **MongoDB** - NoSQL Database
- **Motor** - Async MongoDB Driver

### AI/ML
- **OpenAI GPT** - Language Models
- **LangChain** - LLM Orchestration
- **Vector Embeddings** - Semantic Search
- **NLTK** - Natural Language Processing

### Communication Services
- **Twilio** - Voice calls and SMS
- **Nexmo/Vonage** - WhatsApp Business API
- **ngrok** - Webhook tunneling

### Infrastructure
- **Docker** - Containerization
- **Node.js** - Frontend Runtime
- **Python 3.9+** - Backend Runtime

## 📋 Prerequisites

- **Node.js** 16+ and npm
- **Python** 3.9+
- **MongoDB** 4.4+
- **Git**
- **Twilio Account**
- **Nexmo/Vonage Account**
- **OpenAI API Key**
- **Clerk Account**

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/llm-phone-feedback-system.git
cd llm-phone-feedback-system
```

### 2. Backend Setup
```bash
cd server
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd ..
npm install
```

### 4. Environment Configuration
```bash
cp .env.template .env
# Edit .env with your actual API keys and configuration
```

## ⚙️ Configuration

### Environment Variables

Copy `.env.template` to `.env` and configure:

#### Authentication
```env
CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here
```

#### Database
```env
MONGODB_URI=mongodb://localhost:27017/llm_feedback_system
```

#### AI Services
```env
OPENAI_API_KEY=sk-your_openai_api_key
OPENAI_MODEL=gpt-4
```

#### Communication Services
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
NEXMO_API_KEY=your_nexmo_api_key
```

## 🏃‍♂️ Usage

### Start Development Environment

1. **Start MongoDB**
```bash
mongod
```

2. **Start Backend Server**
```bash
cd server
python main.py
# Server runs on http://localhost:8000
```

3. **Start Frontend**
```bash
npm start
# Frontend runs on http://localhost:3000
```

4. **Start ngrok (for webhooks)**
```bash
ngrok http 8000
```

### Creating Your First Campaign

1. **Access the Web Interface**: `http://localhost:3000`
2. **Sign In** with Clerk authentication
3. **Create Survey**: Navigate to Surveys → New Survey
4. **Launch Campaign**: Go to Calls → Create Campaign
5. **Monitor Results**: Check Dashboard for analytics

### Example Survey Creation
```json
{
  "title": "Customer Satisfaction Survey",
  "questions": [
    {
      "id": "satisfaction",
      "text": "How satisfied are you with our service?",
      "type": "scale",
      "options": ["1", "2", "3", "4", "5"]
    },
    {
      "id": "feedback",
      "text": "What can we improve?",
      "type": "text"
    }
  ]
}
```

## 📚 API Documentation

### Core Endpoints

#### Calls
- `GET /api/calls` - List all calls
- `POST /api/calls` - Create new call
- `GET /api/calls/{id}` - Get call details
- `PUT /api/calls/{id}` - Update call status

#### Surveys
- `GET /api/surveys` - List surveys
- `POST /api/surveys` - Create survey
- `DELETE /api/surveys/{id}` - Delete survey

#### Knowledge Base
- `POST /api/knowledge/upload` - Upload documents
- `POST /api/knowledge/query` - Query knowledge base
- `GET /api/knowledge/documents` - List documents

#### Analytics
- `GET /api/stats/summary` - Campaign statistics
- `GET /api/stats/sentiment` - Sentiment analysis

### Webhook Endpoints
- `POST /webhook/twilio/voice` - Voice call events
- `POST /webhook/twilio/sms` - SMS events
- `POST /webhook/nexmo/whatsapp` - WhatsApp events

## 🏗 Architecture

### System Architecture
```
Frontend (React) ↔ Backend (FastAPI) ↔ MongoDB
                        ↓
              AI Services (OpenAI/LangChain)
                        ↓
        Communication APIs (Twilio/Nexmo)
```

### Data Flow
1. **User Creates Campaign** → Frontend → Backend → Database
2. **Campaign Execution** → Backend → Communication APIs
3. **Response Processing** → Webhooks → AI Analysis → Database
4. **Analytics Generation** → Backend → Frontend → Dashboard

### Key Components

#### LLM Integration
- **GPT Models**: Complex reasoning and response generation
- **Embeddings**: Document vectorization and similarity search
- **Prompt Engineering**: Optimized templates for different scenarios

#### RAG Pipeline
```python
# Document Processing
def process_document(file):
    text = extract_text(file)
    chunks = split_text(text)
    embeddings = generate_embeddings(chunks)
    return store_vectors(embeddings)

# Query Processing
def query_knowledge_base(question):
    query_embedding = generate_embedding(question)
    relevant_docs = vector_search(query_embedding)
    context = prepare_context(relevant_docs)
    response = llm_generate(question, context)
    return response
```

#### Sentiment Analysis
```python
def analyze_sentiment(text):
    analysis = {
        "sentiment": classify_sentiment(text),
        "confidence": calculate_confidence(text),
        "emotions": detect_emotions(text),
        "entities": extract_entities(text)
    }
    return analysis
```

## 🔧 Development

### Project Structure
```
llm-phone-feedback-system/
├── src/                    # React frontend
│   ├── components/        # UI components
│   ├── services/         # API services
│   └── utils/           # Utilities
├── server/               # FastAPI backend
│   ├── app/            # Application code
│   ├── models/         # Data models
│   └── api/           # API routes
├── public/             # Static files
└── docs/              # Documentation
```

### Running Tests
```bash
# Backend tests
cd server
pytest

# Frontend tests
npm test
```

### Code Quality
```bash
# Python linting
flake8 server/

# JavaScript linting
npm run lint
```

## 📈 Success Rate Calculation

The system calculates success rates using the formula:

**Success Rate = (Completed Calls / Total Calls) × 100**

### Call Status Categories
- **Completed**: Successfully finished calls
- **Failed**: Calls that encountered errors
- **Scheduled**: Calls waiting to be executed
- **In Progress**: Currently active calls
- **Cancelled**: Manually cancelled calls

### Example Scenarios
| Total Calls | Completed | Success Rate |
|-------------|-----------|--------------|
| 100         | 85        | 85%          |
| 50          | 40        | 80%          |
| 25          | 20        | 80%          |
| 10          | 0         | 0%           |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Write tests for new features
- Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, email mohkach2001@gmail.com or join our [Discord server](https://discord.com/users/moe9063).

## 🙏 Acknowledgments

- OpenAI for GPT models
- Twilio for communication APIs
- MongoDB for database services
- The open-source community

---

**Made with ❤️ for intelligent customer feedback collection**

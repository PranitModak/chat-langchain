# 🦜️🔗 Chat LangChain

This repo is an implementation of a chatbot specifically focused on question answering over the [LangChain documentation](https://python.langchain.com/).
Built with [LangChain](https://github.com/langchain-ai/langchain/), [LangGraph](https://github.com/langchain-ai/langgraph/), [Pydantic](https://pydantic.dev/), and [Next.js](https://nextjs.org).



> Looking for the JS version? Click [here](https://github.com/langchain-ai/chat-langchainjs).

The app leverages LangChain and LangGraph's streaming support and async API to update the page in real time for multiple users.

## 🚀 Running Locally

### Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.11+**
- **Node.js 18+** and **npm** or **yarn**
- **Poetry** (Python dependency management)
- **Git**

### Quick Start

#### Option 1: Using Makefile (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/langchain-ai/chat-langchain.git
   cd chat-langchain
   ```

2. **Complete setup**
   ```bash
   make setup
   ```

3. **Edit environment variables**
   ```bash
   # Edit .env file with your API keys
   nano .env
   # or
   code .env
   ```

4. **Ingest documentation data**
   ```bash
   # Choose one of the ingestion modes:
   make ingest        # Web scraping (fastest)
   make ingest-sphinx # Sphinx build (most reliable)
   make ingest-git    # Git access (fastest)
   ```

5. **Start the application**
   ```bash
   # Start both backend and frontend (requires tmux)
   make start
   
   # Or start them separately:
   make start-backend   # Terminal 1
   make start-frontend  # Terminal 2
   ```

6. **Open your browser**
   Navigate to `http://localhost:3000` to start chatting!

#### Option 2: Manual Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/langchain-ai/chat-langchain.git
   cd chat-langchain
   ```

2. **Set up environment variables**
   ```bash
   # Create environment file
   cp env.example .env
   ```
   
   Edit `.env` and add your API key:
   ```env
   # Required API Key
   GOOGLE_API_KEY=your_google_api_key_here
   
   # Vector Database (Chroma is used by default)
   CHROMA_PERSIST_DIRECTORY=./chroma_db
   ```

3. **Install Python dependencies**
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install
   ```

4. **Install Frontend dependencies**
   ```bash
   cd frontend
   npm install
   # or if using yarn
   yarn install
   cd ..
   ```

5. **Ingest documentation data**
   ```bash
   # Activate poetry environment
   poetry shell
   
   # Choose one of the ingestion modes:
   
   # Option 1: Web Scraping (Original)
   python backend/ingest.py --mode web --wipe
   
   # Option 2: Local Sphinx Build (More reliable)
   python backend/ingest.py --mode sphinx --wipe
   
   # Option 3: Direct Git Access (Fastest)
   python backend/ingest.py --mode gitingest --wipe
   ```

6. **Start the Backend**
   ```bash
   # In the poetry shell
   python backend/main.py
   ```
   The backend will start on `http://localhost:8080`

7. **Start the Frontend**
   ```bash
   # In a new terminal
   cd frontend
   npm run dev
   # or
   yarn dev
   ```
   The frontend will start on `http://localhost:3000`

8. **Open your browser**
   Navigate to `http://localhost:3000` to start chatting!

## 📚 Ingestion Modes Explained

### 1. Web Scraping (Original)
```bash
python backend/ingest.py --mode web --wipe
```
- **Pros**: No additional setup required
- **Cons**: Can be unreliable, depends on website availability
- **Use case**: Quick testing

### 2. Local Sphinx Build
```bash
python backend/ingest.py --mode sphinx --wipe
```
- **Pros**: More reliable, complete documentation coverage
- **Cons**: Requires more time and disk space
- **Use case**: Production-like environment

### 3. Direct Git Access (gitingest)
```bash
python backend/ingest.py --mode gitingest --wipe
```
- **Pros**: Fastest, gets raw source files
- **Cons**: May miss some formatting
- **Use case**: Development and testing

## 🔧 Development

### Makefile Commands

The project includes a comprehensive Makefile for common development tasks:

```bash
# View all available commands
make help

# Complete setup
make setup

# Install dependencies
make install-backend
make install-frontend

# Ingest documentation
make ingest        # Web scraping
make ingest-sphinx # Sphinx build
make ingest-git    # Git access

# Start servers
make start-backend
make start-frontend
make start         # Both (requires tmux)

# Code quality
make format
make lint
make test

# Cleanup
make clean
```

### Backend Development

The backend is built with:
- **FastAPI**: Web framework
- **LangChain**: LLM orchestration
- **LangGraph**: Conversation flow management
- **Pydantic**: Data validation and serialization
- **Google Gemini**: LLM provider (exclusive)
- **ChromaDB**: Vector database (exclusive)

Key files:
- `backend/main.py`: FastAPI application entry point
- `backend/retrieval_graph/graph.py`: Main conversation graph
- `backend/ingest.py`: Document ingestion pipeline
- `backend/configuration.py`: Configuration management

### Frontend Development

The frontend is built with:
- **Next.js 14**: React framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Radix UI**: Accessible components

Key files:
- `frontend/app/page.tsx`: Main application page
- `frontend/app/components/ChatLangChain.tsx`: Chat interface
- `frontend/app/contexts/GraphContext.tsx`: State management

### Running Tests

```bash
# All tests
make test

# Or individually:
# Backend tests
poetry run pytest backend/tests/

# Frontend tests
cd frontend
npm test
```

## 🌐 API Endpoints

The backend provides the following endpoints:

- `POST /chat`: Main chat endpoint
- `POST /api/threads`: Create new conversation thread
- `POST /api/threads/search`: Search user threads
- `GET /api/threads/{thread_id}`: Get specific thread

## 🔍 Troubleshooting

### Common Issues

1. **Poetry not found**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Node modules not found**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Chroma database issues**
   ```bash
   rm -rf chroma_db/
   python backend/ingest.py --mode web --wipe
   ```

4. **API key errors**
   - Ensure your Google API key is set in `.env`
   - Check that the key is valid and has sufficient credits

5. **Port conflicts**
   - Backend: Change port in `backend/main.py` (default: 8080)
   - Frontend: Change port in `frontend/package.json` scripts (default: 3000)

### Environment Setup

For different operating systems:

**macOS/Linux:**
```bash
# Install Python 3.11+
brew install python@3.11  # macOS
sudo apt install python3.11  # Ubuntu

# Install Node.js
brew install node  # macOS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -  # Ubuntu
sudo apt-get install -y nodejs
```

**Windows:**
```bash
# Install Python 3.11+ from python.org
# Install Node.js from nodejs.org
# Use WSL2 for better development experience
```

## 📖 Technical Description

There are two components: ingestion and question-answering.

### Ingestion Process

1. Pull HTML from documentation sites and GitHub codebases
2. Load HTML with LangChain's `RecursiveURLLoader` and `SitemapLoader`
3. Split documents with `RecursiveCharacterTextSplitter`
4. Create vector embeddings using Google Gemini embeddings
5. Store in ChromaDB vector database with deduplication

### Question-Answering Process

1. **Query Analysis**: Determine standalone question from chat history using Google Gemini
2. **Document Retrieval**: Find relevant documents from vector store
3. **Research Planning**: Create step-by-step research plan for complex queries
4. **Response Generation**: Generate answer using retrieved context and Google Gemini
5. **Streaming**: Stream response in real-time to frontend

## 📚 Documentation

Looking to use or modify this Use Case Accelerant for your own needs? We've added a few docs to aid with this:

- **[Concepts](./CONCEPTS.md)**: A conceptual overview of the different components of Chat LangChain. Goes over features like ingestion, vector stores, query analysis, etc.
- **[Modify](./MODIFY.md)**: A guide on how to modify Chat LangChain for your own needs. Covers the frontend, backend and everything in between.
- **[LangSmith](./LANGSMITH.md)**: A guide on adding robustness to your application using LangSmith. Covers observability, evaluations, and feedback.
- **[Production](./PRODUCTION.md)**: Documentation on preparing your application for production usage. Explains different security considerations, and more.
- **[Deployment](./DEPLOYMENT.md)**: How to deploy your application to production. Covers setting up production databases, deploying the frontend, and more.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

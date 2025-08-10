# FinDocGPT - AI-Powered Investment Analysis Platform

**A project by team KubeAI at Hack-Nation's Global AI Hackathon**

FinDocGPT is a sophisticated agentic AI system that revolutionizes financial document analysis and investment strategy formulation. Built with modern web technologies and advanced AI capabilities, it provides comprehensive financial analysis through an intuitive interface.

## 🎯 Project Overview

FinDocGPT combines the power of SEC document retrieval, advanced RAG (Retrieval-Augmented Generation) technology, and multi-agent AI systems to deliver comprehensive investment analysis. The platform automatically fetches real SEC filings, processes them through a knowledge graph, and employs specialized AI agents to generate actionable investment insights.

### Key Capabilities
- **Automated SEC Data Pipeline**: Auto fetching of 10-K, 10-Q, and 8-K filings using EdgarTools
- **Advanced RAG System**: Document indexing and semantic search powered by Cognee
- **Multi-Agent Analysis**: Specialized AI agents for research, strategy, and risk assessment
- **Interactive Web Interface**: Modern React-based frontend with real-time updates
- **Iterative Analysis Engine**: Self-improving analysis through multiple refinement cycles

## 🏗️ System Architecture

### Backend Infrastructure (Django REST API)

The backend is built on Django 5.2+ with a modular architecture consisting of three main applications:

#### **Documents App** (`backend/documents/`)
- **Models**: Document metadata storage with status tracking
- **Services**: SEC filing retrieval and RAG integration
- **API Endpoints**: Document management and company-specific querying
- **Features**: Automatic document processing, status monitoring, content validation

#### **Analysis App** (`backend/analysis/`)
- **Iterative Analysis Engine**: Self-improving multi-cycle analysis system
- **Progress Tracking**: Real-time iteration monitoring with completeness scoring
- **Result Storage**: Comprehensive analysis results with full iteration history
- **Quality Metrics**: AI-powered analysis completeness assessment (0-10 scale)
- **Cancellation Support**: User-controlled analysis termination with partial results

#### **Agents App** (`backend/agents/`)
- **Legacy Component**: Simplified agent models (not actively used in current architecture)
- **Note**: The current system uses the IterativeAnalysisService instead of separate agents

### Core Services Layer (`backend/services/`)

#### **EdgarService** (`edgar_service.py`)
- SEC EDGAR database integration using EdgarTools
- Company search and identification
- Filing retrieval (10-K, 10-Q, 8-K forms)
- Content extraction and metadata processing
- Real-time data validation and error handling

#### **CogneeService** (`cognee_service.py`)
- RAG system integration with Cognee SDK
- Document indexing and knowledge graph creation
- Semantic search and context retrieval
- Investment-specific query processing
- Health monitoring and performance tracking

#### **IterativeAnalysisService** (`iterative_analysis_service.py`) - Core Engine
- **Multi-Cycle Analysis**: Iterative refinement with up to 10 cycles
- **Initial Analysis**: Comprehensive analysis generation from document summaries
- **Completeness Evaluation**: AI-powered gap identification and scoring (0-10 scale)
- **Targeted RAG Queries**: Dynamic query generation based on identified gaps
- **Analysis Refinement**: Integration of RAG results into improved analysis
- **Progress Tracking**: Real-time iteration monitoring and cancellation support
- **Quality Termination**: Automatic stopping when completeness score ≥ 7/10

#### **GeminiValidationService** (`gemini_validation_service.py`) - Validation Layer
- **RAG Response Validation**: Quality assessment of Cognee RAG responses
- **Fallback Enhancement**: Internet search when RAG responses are inadequate
- **Source Attribution**: Clear tracking of information sources (RAG vs. web search)
- **Financial Standards**: Specialized validation for financial information quality
- **Quality Scoring**: Multi-factor assessment of response reliability and completeness

### Frontend Architecture (Next.js 15)

Built with modern React and TypeScript, featuring:

#### **Core Pages** (`frontend/src/app/`)
- **Dashboard** (`page.tsx`): Company selection and navigation hub
- **Company Analysis** (`company/[company]/page.tsx`): Dedicated company analysis interface
- **Iterative Analysis** (`analysis/page.tsx`): Advanced multi-cycle analysis dashboard
- **Document Management** (`documents/page.tsx`): Document viewing and management

#### **Component Library** (`frontend/src/components/`)
- **Analysis Components**: Progress tracking, iteration timeline, results visualization
- **Document Components**: Document summaries, status indicators, content viewers
- **Layout Components**: Navigation, responsive design, loading states
- **Common Components**: Reusable UI elements with consistent styling

#### **State Management**
- **React Query**: Server state management and caching
- **Custom Hooks**: Company-specific data fetching and management
- **Real-time Updates**: Live status updates during processing

## 🚀 Technology Stack

### Backend Technologies
- **Django 5.2+**: Web framework with REST API capabilities
- **Django REST Framework**: API development and serialization
- **EdgarTools**: SEC filing data retrieval and processing
- **Cognee SDK**: RAG system and knowledge management
- **OpenAI SDK**: GPT-4 integration for AI agents
- **Google Generative AI**: Gemini integration for validation
- **SQLite**: Development database (PostgreSQL ready)
- **Python-dotenv**: Environment configuration management

### Frontend Technologies
- **Next.js 15**: React framework with App Router and Turbopack
- **React 19**: Latest React with concurrent features
- **TypeScript 5**: Type-safe development
- **Tailwind CSS 4**: Utility-first styling framework
- **React Query (TanStack)**: Server state management
- **Lucide React**: Modern icon library
- **Axios**: HTTP client for API communication
- **Recharts**: Data visualization and charting

### AI & Data Technologies
- **OpenAI GPT-4**: Primary AI model for iterative analysis and refinement
- **Google Gemini 2.5 Flash**: RAG validation, enhancement, and quality assessment
- **Cognee**: Knowledge graph, document indexing, and semantic search
- **EdgarTools**: SEC EDGAR database access and filing retrieval
- **Dual AI Architecture**: Primary analysis (OpenAI) + Validation layer (Gemini)

## 📊 Key Features

### 1. Intelligent Document Pipeline
- **Automatic Fetching**: Real-time SEC filing retrieval based on company queries
- **Smart Processing**: Content extraction, validation, and metadata enrichment
- **RAG Integration**: Automatic indexing in Cognee knowledge graph
- **Status Tracking**: Real-time processing status with error handling

### 2. Iterative Analysis Engine (Core Architecture)
- **Self-Improving Analysis**: Multi-cycle refinement process with completeness scoring
- **Gap Detection**: AI-powered identification of analysis weaknesses and missing information
- **Targeted RAG Queries**: Dynamic generation of specific queries to fill identified gaps
- **Gemini Validation**: Secondary AI validation and enhancement of RAG responses
- **Quality Scoring**: Continuous assessment of analysis completeness (0-10 scale)
- **Adaptive Termination**: Intelligent stopping when analysis reaches sufficient quality

### 3. Advanced RAG with Validation Layer
- **Primary RAG System**: Cognee-powered knowledge graph and semantic search
- **Validation Pipeline**: Gemini AI validates RAG response quality and relevance
- **Fallback Enhancement**: Internet search via Gemini when RAG responses are inadequate
- **Source Attribution**: Clear tracking of information sources (RAG vs. web search)
- **Quality Assessment**: Financial information standards validation

### 4. Interactive Web Interface
- **Company-Centric Design**: Dedicated pages for each company analysis
- **Real-time Updates**: Live progress tracking and status updates
- **Document Management**: Comprehensive document viewing and organization
- **Responsive Design**: Optimized for desktop and mobile devices

### 5. Advanced Query Capabilities
- **Natural Language Processing**: Intuitive query interface
- **Context-Aware Responses**: RAG-powered answers with source attribution
- **Multi-Document Analysis**: Cross-document insights and comparisons
- **Investment-Focused**: Specialized prompts for financial analysis

## 🔄 Iterative Analysis Workflow

The core innovation of FinDocGPT is its iterative analysis engine that continuously refines investment analysis through multiple cycles:

### Step-by-Step Process

#### 1. **Document Preparation**
- Gather all available document summaries with metadata
- Filter documents based on company criteria (if specified)
- Prepare structured context for analysis

#### 2. **Initial Analysis Generation**
- Generate comprehensive investment analysis using OpenAI GPT-4
- Base analysis on document summaries and available metadata
- Structure results with investment recommendation, reasoning, and risk factors

#### 3. **Completeness Evaluation**
- AI-powered assessment of analysis quality and completeness
- Identify specific gaps, weaknesses, and missing information
- Generate completeness score (0-10 scale)
- Determine if analysis meets quality threshold (≥7/10)

#### 4. **Targeted RAG Query Generation**
- Generate specific queries to address identified gaps
- Focus on missing financial data, market context, or risk factors
- Create targeted questions for the RAG knowledge base

#### 5. **RAG Query Execution with Validation**
- Execute queries against Cognee knowledge graph
- **Gemini Validation Layer**: Assess if RAG responses adequately answer queries
- **Fallback Enhancement**: Use Gemini internet search if RAG responses are insufficient
- **Source Attribution**: Track whether information comes from documents or web search

#### 6. **Analysis Refinement**
- Integrate RAG results into the original analysis
- Update recommendations based on new information
- Enhance reasoning with additional context and data
- Mark sections that have been significantly updated

#### 7. **Iteration Control**
- Repeat steps 3-6 until analysis reaches quality threshold or max iterations (10)
- Real-time progress tracking with cancellation support
- Preserve partial results if process is terminated early

### Key Innovations

- **Self-Improving**: Each iteration builds upon previous analysis
- **Gap-Driven**: Focuses refinement on specific identified weaknesses
- **Validated RAG**: Ensures information quality through dual AI validation
- **Source-Aware**: Maintains transparency about information origins
- **Quality-Controlled**: Objective scoring prevents infinite loops

## 🛠️ Installation & Setup

### Prerequisites
```bash
# Required Software
- Python 3.11+
- Node.js 18+
- Git

# Required API Keys
- OpenAI API key (for GPT-4 access)
- Cognee API key (optional, has fallback)
- Google Gemini API key (for validation)
```

### Backend Setup
```bash
# Clone repository
git clone <repository-url>
cd FinDocGPT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp backend/.env.example backend/.env
# Edit .env with your API keys

# Setup database
cd backend
python manage.py migrate
python manage.py collectstatic

# Start development server
python manage.py runserver
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with backend URL

# Start development server
npm run dev
```

## 🎮 Usage Guide

### 1. Company Analysis Workflow
1. **Enter Company**: Start by entering a company name or ticker symbol
2. **Document Fetching**: System automatically fetches relevant SEC filings
3. **Processing**: Documents are processed and stored in the RAG system
4. **Query Interface**: Ask natural language questions about the company
5. **Simple Analysis**: Receive immediate RAG-powered responses

### 2. Iterative Analysis (Advanced Feature)
1. **Create Analysis**: Start a new iterative analysis session with investment query
2. **Monitor Progress**: Watch real-time iteration cycles with completeness scoring
3. **Track Refinement**: View detailed iteration timeline showing:
   - Initial analysis generation
   - Completeness evaluation and gap identification
   - Targeted RAG queries and results
   - Analysis refinement with new information
4. **Quality Assessment**: Monitor completeness score progression (0-10 scale)
5. **Review Results**: Examine comprehensive final analysis with:
   - Investment recommendation and confidence level
   - Detailed reasoning and supporting evidence
   - Risk assessment and mitigation strategies
   - Source attribution (document vs. web search)
6. **Export Insights**: Save or share detailed analysis results

### 3. Document Management
1. **View Documents**: Browse all processed SEC filings
2. **Document Summaries**: Access AI-generated document summaries
3. **Status Monitoring**: Track processing status and errors
4. **Manual Processing**: Trigger reprocessing if needed

## 🔧 Development Features

### Interactive CLI Tool
The project includes a powerful command-line interface (`interactive_cognee_edgar.py`) for:
- Direct SEC document fetching and processing
- RAG system testing and validation
- Performance monitoring and debugging
- Session management and statistics

### Testing & Validation
- **Integration Tests**: Comprehensive API and service testing
- **Validation Pipeline**: Multi-layer content validation
- **Performance Monitoring**: Response time and accuracy tracking
- **Error Handling**: Robust error recovery and reporting

### Monitoring & Debugging
- **Service Health Checks**: Real-time system status monitoring
- **Analysis Quality Metrics**: Completeness and accuracy scoring
- **Performance Analytics**: Processing time and efficiency tracking
- **Debug Tools**: Comprehensive logging and diagnostic capabilities

## 📈 Performance & Scalability

### Optimization Features
- **Caching Strategy**: Intelligent caching of documents and analysis results
- **Async Processing**: Non-blocking document processing and analysis
- **Rate Limiting**: Respectful API usage with proper throttling
- **Error Recovery**: Automatic retry mechanisms and graceful degradation

### Scalability Considerations
- **Database Optimization**: Efficient queries and indexing strategies
- **API Design**: RESTful architecture with pagination and filtering
- **Frontend Performance**: Code splitting and lazy loading
- **Resource Management**: Memory-efficient processing and cleanup

## 🎯 Hackathon Achievement

This project represents a sophisticated financial analysis platform with cutting-edge AI architecture built during Hack-Nation's Global AI Hackathon. Key achievements include:

- **Innovative Iterative Analysis**: Self-improving AI analysis with gap detection and targeted refinement
- **Dual AI Architecture**: OpenAI for primary analysis + Gemini for validation and enhancement
- **Advanced RAG Pipeline**: Cognee knowledge graph with intelligent fallback to web search
- **Real Data Integration**: Actual SEC filing processing with comprehensive validation
- **Production-Ready System**: Full-stack implementation with real-time monitoring and cancellation
- **Quality-Controlled AI**: Objective completeness scoring and intelligent termination criteria

## 🚀 Future Enhancements

### Planned Features
- **Portfolio Analysis**: Multi-company portfolio optimization
- **Real-time Market Data**: Integration with live market feeds
- **Advanced Visualizations**: Interactive charts and financial modeling
- **Collaboration Features**: Team analysis and sharing capabilities
- **Mobile App**: Native mobile application development

### Technical Improvements
- **Performance Optimization**: Enhanced caching and processing speed
- **AI Model Fine-tuning**: Custom models for financial analysis
- **Advanced RAG**: Improved knowledge graph and retrieval accuracy
- **Security Enhancements**: Enterprise-grade security features

## 📄 License

This project is developed for Hack-Nation's Global AI Hackathon by team KubeAI.

## 🤝 Contributing

This project was built during a hackathon by team KubeAI. For questions or collaboration opportunities, please reach out to the team.

---

**FinDocGPT** - Revolutionizing investment analysis through AI-powered document intelligence. Built with ❤️ by team KubeAI at Hack-Nation's Global AI Hackathon.
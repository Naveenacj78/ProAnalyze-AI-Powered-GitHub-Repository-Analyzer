# ProAnalyze - Python Version

A comprehensive GitHub repository analysis tool with AI-powered insights, visualizations, and interactive chat capabilities.

## 🚀 Features

- **🔍 Repository Analysis**: Deep analysis of Python repositories using Mixtral 8x7B LLM
- **📊 Visual Workflows**: Auto-generated system and user workflow diagrams using Graphviz
- **💬 AI Chat**: Interactive chatbot for asking questions about your codebase
- **📋 Comprehensive Reports**: Detailed analysis covering overview, features, dependencies, workflow, strengths, and improvements
- **🌐 Web Interface**: Modern Streamlit-based web application

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Git (for repository access)
- Graphviz (for diagram generation)

### Install Graphviz

**Ubuntu/Debian:**
```bash
sudo apt-get install graphviz
```

**macOS:**
```bash
brew install graphviz
```

**Windows:**
Download and install from [Graphviz website](https://graphviz.org/download/)

### Install Python Dependencies

```bash
# Clone or download the project
cd analyzer_v3_copy

# Install Python packages
pip install -r requirements.txt
```

## 🔧 Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp env_example.txt .env

# Edit with your API keys
nano .env
```

Add your API keys:

```env
TOGETHER_API_KEY=your_together_api_key_here
GITHUB_TOKEN=your_github_token_here
```

### 2. Get API Keys

**Together AI API Key:**
1. Visit [Together AI](https://api.together.xyz/)
2. Sign up for an account
3. Get your API key from the dashboard

**GitHub Token:**
1. Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Generate a new token with `repo` scope (for private repositories)
3. Copy the token

## 🚀 Usage

### Quick Start (Flask UI)

```bash
# Run the application
python flask_app.py
```

The application will start on `http://localhost:8501`

### Manual Start (Flask)

```bash
# Set environment variables
export TOGETHER_API_KEY="your_api_key"
export GITHUB_TOKEN="your_github_token"

# Run Flask
python flask_app.py
```

## 📱 Web Interface

### Home Page
- Overview of features and capabilities
- Quick start instructions

### Analyze Page
1. **Enter Repository URL**: Paste any GitHub repository URL
2. **Click Analyze**: The system will:
   - Fetch repository data and files
   - Analyze Python files using Mixtral 8x7B
   - Generate comprehensive analysis report
3. **Generate Diagrams**: Create visual workflow diagrams
4. **View Results**: Explore detailed analysis sections

### AI Chat Page
1. **Load Repository**: Enter a GitHub URL to load repository context
2. **Start Chatting**: Ask questions about the codebase
3. **Get AI Answers**: Receive detailed, context-aware responses

## 🔍 Analysis Features

### Comprehensive Analysis Sections

- **📖 Project Overview**: Purpose, methodology, and significance
- **⭐ Key Features**: Main functionality and capabilities
- **📦 Libraries & Dependencies**: Important libraries and their roles
- **🔄 Project Workflow**: Step-by-step operation flow
- **⚙️ Implementation Details**: Technical architecture and design patterns
- **💪 Project Strengths**: Unique advantages and capabilities
- **🚀 Areas for Improvement**: Concrete enhancement suggestions

### Visual Workflow Diagrams

- **System Workflow**: Internal technical processes
- **User Workflow**: User interaction journey
- **Auto-generated**: Created using AI analysis of workflow descriptions
- **Interactive**: SVG-based diagrams for better visualization

### AI Chat Capabilities

- **Context-Aware**: Answers based on actual repository code
- **Technical Focus**: Detailed explanations of architecture and implementation
- **Code References**: Cites specific files and functions
- **Question Types**: Architecture, implementation, debugging, optimization

## 🏗️ Architecture

### Core Components

- **`app.py`**: Core services and data models
- **`streamlit_app.py`**: Web interface and user interactions
- **`run.py`**: Startup script with environment checks

### Services

- **GitHubService**: Repository data fetching and URL parsing
- **AnalysisService**: LLM integration and code analysis
- **WorkflowDiagramService**: Diagram generation using Graphviz
- **ChatService**: AI chat functionality

### Data Models

- **RepositoryData**: Repository information and file list
- **FileData**: Individual file information
- **WorkflowStep**: Workflow diagram components
- **WorkflowDiagrams**: Generated diagram data

## 🔧 Configuration Options

### Analysis Settings

```python
# In app.py Config class
MAX_FILES = 5          # Maximum files to analyze
MAX_FILE_SIZE = 2000   # Maximum file content size
MAX_RETRIES = 3        # API retry attempts
BASE_DELAY = 2         # Delay between retries (seconds)
```

### Model Configuration

```python
MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"
MAX_TOKENS = 4096
TEMPERATURE = 0.3
TOP_P = 0.9
```

## 🐛 Troubleshooting

### Common Issues

**1. Graphviz not found:**
```bash
# Install Graphviz system package
sudo apt-get install graphviz  # Ubuntu/Debian
brew install graphviz          # macOS
```

**2. API Key errors:**
- Verify your Together AI API key is correct
- Check your GitHub token has `repo` scope
- Ensure environment variables are set

**3. Repository access issues:**
- Use HTTPS URLs for public repositories
- Ensure GitHub token has proper permissions
- Check repository is accessible

**4. Analysis failures:**
- Ensure repository contains Python files
- Check file sizes are reasonable
- Verify API quotas and limits

### Debug Mode

```bash
# Run with debug information
streamlit run streamlit_app.py --logger.level debug
```

## 📊 Performance

### Optimization Tips

- **File Limits**: Analysis is limited to 5 files by default
- **Content Truncation**: Large files are truncated to 2000 characters
- **Caching**: Streamlit caches analysis results in session state
- **Async Operations**: Non-blocking API calls for better performance

### Resource Usage

- **Memory**: ~200-500MB depending on repository size
- **API Calls**: 2-3 calls per analysis (analysis + diagrams)
- **Processing Time**: 30-60 seconds for typical repositories

## 🔒 Security

### Data Handling

- **API Keys**: Stored in environment variables only
- **Repository Data**: Cached in session state (temporary)
- **Content Sanitization**: Sensitive information is masked
- **No Persistent Storage**: No data is saved to disk

### Privacy

- **Repository Access**: Only reads public repository data
- **Content Analysis**: Files are sent to Together AI for analysis
- **No Data Retention**: Analysis results are not stored

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
streamlit run streamlit_app.py --server.runOnSave true
```

### Code Structure

- **Services**: Core functionality in `app.py`
- **Interface**: Streamlit components in `streamlit_app.py`
- **Configuration**: Environment-based settings
- **Error Handling**: Comprehensive error messages and fallbacks

## 📄 License

This project maintains the same license as the original TypeScript version.

## 🆚 Python vs TypeScript Version

### Advantages of Python Version

- **Simpler Setup**: No Node.js or npm required
- **Better AI Integration**: Native Python libraries for ML/AI
- **Easier Deployment**: Single Python environment
- **Streamlit Interface**: Modern, responsive web interface
- **Better Error Handling**: Comprehensive error messages

### Feature Parity

- ✅ Repository analysis with Mixtral 8x7B
- ✅ Workflow diagram generation
- ✅ AI chat functionality
- ✅ Comprehensive analysis sections
- ✅ Modern web interface
- ✅ Environment-based configuration

## 🚀 Deployment

### Local Development

```bash
python run.py
```

### Production Deployment

```bash
# Using Streamlit Cloud
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

# Install Graphviz
RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt

# Run application
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Verify your API keys and configuration
3. Ensure all dependencies are installed
4. Check the console output for error messages

---

**ProAnalyze Python Version** - Bringing AI-powered repository analysis to Python! 🐍✨


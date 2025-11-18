import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "your-perplexity-api-key")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model Configuration
LOCAL_MODEL = "llama3.1:8b"

# Perplexity Models Available to You
PERPLEXITY_SEARCH_MODEL = "sonar"  # Lightweight for simple queries
PERPLEXITY_REASONING_MODEL = "sonar-reasoning"  # For complex analysis
PERPLEXITY_RESEARCH_MODEL = "sonar-deep-research"  # For comprehensive reports

# Default Perplexity model
PERPLEXITY_MODEL = PERPLEXITY_SEARCH_MODEL  # Start with lightweight model

# Vector Store Configuration
VECTOR_STORE_PATH = "./vector_store"
UPLOAD_FOLDER = "./data/uploads"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# App Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.pptx'}
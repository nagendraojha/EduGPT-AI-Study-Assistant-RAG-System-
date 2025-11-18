import requests
import ollama
from typing import List, Dict, Any
import json

class RAGChain:
    def __init__(self, vector_store, config):
        self.vector_store = vector_store
        self.config = config
    
    def get_local_response(self, query: str, context: str) -> str:
        """Get response from local Ollama model"""
        try:
            prompt = f"""You are an expert educational assistant. Based on the following context from the user's study materials, please provide a comprehensive answer to their question.

CONTEXT FROM STUDY MATERIALS:
{context}

USER'S QUESTION: {query}

Please provide a detailed, accurate answer based on the provided context. If the context doesn't contain enough information to fully answer the question, please indicate what specific information is missing and provide a general explanation based on your knowledge.

Structure your response to be clear and educational:"""

            response = ollama.generate(
                model=self.config.LOCAL_MODEL,
                prompt=prompt,
                options={
                    'temperature': 0.3,
                    'top_k': 40,
                    'top_p': 0.9,
                }
            )
            
            return response['response']
        except Exception as e:
            return f"Error with local model: {str(e)}"
    
    def get_perplexity_response(self, query: str, context: str, query_type: str = "search") -> str:
        """Get response from Perplexity API using appropriate model based on query type"""
        try:
            # Validate API key
            if not self.config.PERPLEXITY_API_KEY or self.config.PERPLEXITY_API_KEY == "your-perplexity-api-key":
                return "Perplexity API key not configured. Using local model instead."
            
            # Choose the right model based on query type
            if query_type == "reasoning" or any(word in query.lower() for word in ['compare', 'analyze', 'explain', 'why', 'how']):
                model = self.config.PERPLEXITY_REASONING_MODEL
                print(f"🤔 Using reasoning model: {model}")
            elif query_type == "research" or any(word in query.lower() for word in ['comprehensive', 'detailed', 'report', 'research']):
                model = self.config.PERPLEXITY_RESEARCH_MODEL
                print(f"🔍 Using research model: {model}")
            else:
                model = self.config.PERPLEXITY_SEARCH_MODEL
                print(f"🔎 Using search model: {model}")
            
            headers = {
                "Authorization": f"Bearer {self.config.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Optimized prompt for Perplexity models
            if context.strip():
                prompt = f"""Based on the following context from the user's study materials, answer their question. If the context is insufficient, use your general knowledge to provide a helpful answer.

CONTEXT FROM UPLOADED MATERIALS:
{context}

QUESTION: {query}

Please provide a comprehensive and accurate answer:"""
            else:
                prompt = f"""Answer the following question based on your knowledge:

QUESTION: {query}

Please provide a comprehensive and accurate answer:"""

            data = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert computer science educator. Provide clear, accurate explanations with examples when helpful. Be comprehensive but concise."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.3,
                "top_p": 0.9
            }
            
            print(f"🔄 Sending request to Perplexity API with model: {model}")
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            print(f"📊 API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("✅ Perplexity API request successful")
                return content
            else:
                error_msg = f"Perplexity API error ({response.status_code}): {response.text}"
                print(f"❌ {error_msg}")
                return f"{error_msg}. Switching to local model."
                
        except requests.exceptions.Timeout:
            error_msg = "Perplexity API timeout"
            print(f"❌ {error_msg}")
            return f"{error_msg}. Using local model."
        except Exception as e:
            error_msg = f"Error with Perplexity API: {str(e)}"
            print(f"❌ {error_msg}")
            return f"{error_msg}. Using local model."
    
    def generate_response(self, query: str, use_perplexity: bool = False) -> Dict[str, Any]:
        """Generate response using RAG with intelligent model selection"""
        # Search for relevant context
        search_results = self.vector_store.search(query, k=5)
        
        # Combine context from search results
        context = "\n\n".join([
            f"From {result['document']['filename']} (relevance: {result['score']:.3f}):\n{result['document']['chunk']}"
            for result in search_results
        ]) if search_results else ""
        
        # Determine query type for model selection
        query_type = "search"  # default
        if any(word in query.lower() for word in ['compare', 'analyze', 'explain', 'why', 'how', 'difference']):
            query_type = "reasoning"
        elif any(word in query.lower() for word in ['comprehensive', 'detailed', 'report', 'research', 'summary']):
            query_type = "research"
        
        # Generate response
        if use_perplexity and self.config.PERPLEXITY_API_KEY != "your-perplexity-api-key":
            response = self.get_perplexity_response(query, context, query_type)
        else:
            response = self.get_local_response(query, context)
        
        return {
            "response": response,
            "sources": [
                {
                    "filename": result['document']['filename'],
                    "score": result['score'],
                    "content": result['document']['chunk'][:150] + "..."
                }
                for result in search_results
            ] if search_results else [],
            "context_length": len(context)
        }
    
    def summarize_document(self, content: str, use_perplexity: bool = False) -> str:
        """Generate document summary using research model"""
        query = f"Please provide a comprehensive summary of the following document. Focus on key points, main arguments, and important findings:\n\n{content[:3000]}"
        
        if use_perplexity:
            return self.get_perplexity_response(query, "", "research")
        else:
            return self.get_local_response(query, "")
    
    def compare_concepts(self, concept1: str, concept2: str, use_perplexity: bool = False) -> str:
        """Compare two concepts using reasoning model"""
        query = f"Compare and contrast {concept1} and {concept2}. Discuss their similarities, differences, advantages, disadvantages, and use cases."
        
        response_data = self.generate_response(query, use_perplexity)
        return response_data["response"]
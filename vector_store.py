import faiss
import numpy as np
import pickle
import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List, Dict, Any
from utils.document_processor import DocumentProcessor

class VectorStore:
    def __init__(self, embedding_model: str = "sentence-transformers/all-mpnet-base-v2"):
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.index = None
        self.documents = []
        self.document_processor = DocumentProcessor()
    
    def create_index(self, documents: List[Dict[str, Any]]) -> None:
        """Create FAISS index from documents"""
        all_chunks = []
        all_metadata = []
        
        for doc in documents:
            chunks = self.document_processor.chunk_text(doc['content'])
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    'document_id': doc['id'],
                    'filename': doc['filename'],
                    'chunk': chunk,
                    'chunk_id': i
                })
        
        # Generate embeddings
        print(f"Generating embeddings for {len(all_chunks)} chunks...")
        embeddings = self.embedding_model.embed_documents(all_chunks)
        embeddings = np.array(embeddings).astype('float32')
        
        # Create FAISS index with cosine similarity
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        self.documents = all_metadata
        print(f"Created vector store with {len(self.documents)} chunks")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if self.index is None or len(self.documents) == 0:
            return []
        
        # Encode query
        query_embedding = self.embedding_model.embed_query(query)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search (increase k to get more results, then filter)
        k_search = min(k * 2, len(self.documents))
        scores, indices = self.index.search(query_embedding, k_search)
        
        results = []
        seen_chunks = set()
        
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents) and idx >= 0:
                chunk_content = self.documents[idx]['chunk']
                # Avoid duplicate chunks
                if chunk_content not in seen_chunks:
                    seen_chunks.add(chunk_content)
                    # Convert cosine similarity to more readable score (0-1)
                    normalized_score = max(0.0, (score + 1) / 2)  # Convert from [-1,1] to [0,1]
                    results.append({
                        'document': self.documents[idx],
                        'score': normalized_score
                    })
                
                if len(results) >= k:
                    break
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def save(self, path: str) -> None:
        """Save vector store to disk"""
        if not os.path.exists(path):
            os.makedirs(path)
        
        if self.index is not None:
            faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        
        with open(os.path.join(path, "documents.pkl"), 'wb') as f:
            pickle.dump(self.documents, f)
        
        print(f"Vector store saved to {path}")
    
    def load(self, path: str) -> bool:
        """Load vector store from disk"""
        try:
            index_path = os.path.join(path, "index.faiss")
            documents_path = os.path.join(path, "documents.pkl")
            
            if os.path.exists(index_path) and os.path.exists(documents_path):
                self.index = faiss.read_index(index_path)
                with open(documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"Vector store loaded with {len(self.documents)} chunks")
                return True
            else:
                print("Vector store files not found")
                return False
        except Exception as e:
            print(f"Error loading vector store: {e}")
            return False
from flask import Flask, render_template, request, jsonify, session
import os
import uuid
from werkzeug.utils import secure_filename
import config
from utils.document_processor import DocumentProcessor
from utils.vector_store import VectorStore
from utils.rag_chain import RAGChain
import traceback
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'edugpt-secret-key-2024'
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE

# Global components (simpler approach)
document_processor = DocumentProcessor()
global_vector_store = VectorStore()
rag_chain = RAGChain(global_vector_store, config)

# Simple session state
processed_files = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-documents', methods=['POST'])
def process_documents():
    global processed_files
    
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        processed_documents = []
        
        for file in files:
            if file.filename == '':
                continue
            
            # Check file extension
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in config.SUPPORTED_EXTENSIONS:
                # Save file temporarily
                file_path = os.path.join(config.UPLOAD_FOLDER, filename)
                file.save(file_path)
                
                # Process document
                print(f"Processing file: {filename}")
                result = document_processor.process_file(file_path)
                
                if 'error' not in result and result.get('content', '').strip():
                    processed_documents.append({
                        'id': str(uuid.uuid4()),
                        'filename': filename,
                        'content': result['content'],
                        'type': result['type']
                    })
                    print(f"Successfully processed: {filename}, Content length: {len(result['content'])}")
                else:
                    error_msg = result.get('error', 'No content extracted')
                    print(f"Error processing {filename}: {error_msg}")
                
                # Clean up temporary file
                os.remove(file_path)
        
        if processed_documents:
            # Create vector store
            print("Creating vector store...")
            global_vector_store.create_index(processed_documents)
            processed_files = [doc['filename'] for doc in processed_documents]
            
            # Save vector store
            global_vector_store.save(config.VECTOR_STORE_PATH)
            
            return jsonify({
                'success': True,
                'processed_files': len(processed_documents),
                'files': processed_files
            })
        else:
            return jsonify({'success': False, 'error': 'No valid files processed or no content extracted'})
    
    except Exception as e:
        print(f"Error in process_documents: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'})
            
        message = data.get('message', '')
        use_perplexity = data.get('use_perplexity', False)
        
        if not message:
            return jsonify({'error': 'No message provided'})
        
        print(f"Received message: {message}")
        print(f"Processed files: {processed_files}")
        
        # Check if vector store exists
        vector_store_path = config.VECTOR_STORE_PATH
        index_path = os.path.join(vector_store_path, "index.faiss")
        documents_path = os.path.join(vector_store_path, "documents.pkl")
        
        if not os.path.exists(index_path) or not os.path.exists(documents_path):
            return jsonify({'error': 'No documents processed yet. Please upload and process documents first.'})
        
        # Load vector store if not already loaded
        if global_vector_store.index is None:
            if not global_vector_store.load(vector_store_path):
                return jsonify({'error': 'Failed to load knowledge base. Please process your documents again.'})
        
        # Generate response
        print("Generating response...")
        response_data = rag_chain.generate_response(message, use_perplexity)
        
        print("Response generated successfully")
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Error processing your request: {str(e)}'})

@app.route('/summarize-document', methods=['POST'])
def summarize_document():
    """Handle document summarization requests"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'})
            
        use_perplexity = data.get('use_perplexity', False)
        
        # Check if we have processed files
        if not processed_files:
            return jsonify({'error': 'No documents processed yet. Please upload and process documents first.'})
        
        # Load vector store to access document content
        if not global_vector_store.load(config.VECTOR_STORE_PATH):
            return jsonify({'error': 'Failed to load knowledge base. Please process your documents again.'})
        
        # Get all document content for summarization
        all_content = ""
        for doc in global_vector_store.documents:
            all_content += doc['chunk'] + "\n\n"
        
        if not all_content.strip():
            return jsonify({'error': 'No content found in processed documents.'})
        
        # Generate summary
        summary = rag_chain.summarize_document(all_content, use_perplexity)
        
        return jsonify({
            'summary': summary,
            'document_count': len(processed_files),
            'documents': processed_files
        })
        
    except Exception as e:
        print(f"Error in summarize-document: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Error generating summary: {str(e)}'})
    
    except Exception as e:
        print(f"Error in summarize: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/compare', methods=['POST'])
def compare_concepts():
    try:
        data = request.get_json()
        concept1 = data.get('concept1', '')
        concept2 = data.get('concept2', '')
        use_perplexity = data.get('use_perplexity', False)
        
        if not concept1 or not concept2:
            return jsonify({'error': 'Please provide two concepts to compare'})
        
        response = rag_chain.compare_concepts(concept1, concept2, use_perplexity)
        
        return jsonify({'comparison': response})
    
    except Exception as e:
        print(f"Error in compare: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/change-model', methods=['POST'])
def change_model():
    try:
        data = request.get_json()
        model = data.get('model', 'llama2')
        
        config.LOCAL_MODEL = model
        
        return jsonify({'success': True, 'model': model})
    
    except Exception as e:
        print(f"Error changing model: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-uploaded-files', methods=['GET'])
def get_uploaded_files():
    return jsonify({'files': processed_files})

@app.route('/debug/status', methods=['GET'])
def debug_status():
    """Debug endpoint to check system status"""
    vector_store_path = config.VECTOR_STORE_PATH
    index_exists = os.path.exists(os.path.join(vector_store_path, "index.faiss"))
    documents_exists = os.path.exists(os.path.join(vector_store_path, "documents.pkl"))
    
    return jsonify({
        'processed_files': processed_files,
        'vector_store_loaded': global_vector_store.index is not None,
        'index_exists': index_exists,
        'documents_exists': documents_exists,
        'ollama_available': check_ollama()
    })

def check_ollama():
    """Check if Ollama is running"""
    try:
        import ollama
        models = ollama.list()
        return True
    except:
        return False

def ensure_directories():
    """Ensure required directories exist"""
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.VECTOR_STORE_PATH, exist_ok=True)

if __name__ == '__main__':
    ensure_directories()
    print("EduGPT Server Starting...")
    print("Make sure Ollama is running: ollama serve")
    print("Access the application at: http://localhost:5000")
    print("Debug status at: http://localhost:5000/debug/status")
    app.run(debug=True, host='0.0.0.0', port=5000)
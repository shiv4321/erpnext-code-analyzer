"""
RAG Engine for Code Analysis
Integrates with analyzer.py output to provide context-aware answers
"""

import json
import os
from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class CodeRAG:
    def __init__(self, groq_api_key: str, index_path: str = "faiss_index"):
        self.groq = Groq(api_key=groq_api_key)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index_path = index_path
        self.index = None
        self.metadata = []
        
    def prepare_chunks(self, entities_path: str, source_dir: str) -> List[Dict]:
        """Convert analyzer output + source code into searchable chunks"""
        with open(entities_path, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        
        chunks = []
        
        for entity in entities:
            file_path = entity['file']
            full_path = Path(source_dir) / file_path
            
            # Read source code
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    source = f.read()
            except:
                source = ""
            
            # Chunk 1: File overview
            classes = [c['name'] for c in entity['classes']]
            functions = [f['name'] for f in entity['functions']]
            
            chunks.append({
                'text': f"File: {file_path}\nClasses: {', '.join(classes)}\nFunctions: {', '.join(functions)}\nImports: {', '.join(entity['imports'][:10])}",
                'metadata': {
                    'type': 'file_overview',
                    'file': file_path,
                    'classes': classes,
                    'functions': functions
                }
            })
            
            # Chunk 2: Each class with methods
            for cls in entity['classes']:
                chunks.append({
                    'text': f"Class: {cls['name']} in {file_path}\nMethods: {', '.join(cls['methods'])}\nLine: {cls['line']}",
                    'metadata': {
                        'type': 'class',
                        'file': file_path,
                        'name': cls['name'],
                        'methods': cls['methods'],
                        'line': cls['line']
                    }
                })
            
            # Chunk 3: Each function with signature
            for func in entity['functions']:
                chunks.append({
                    'text': f"Function: {func['name']} in {file_path}\nParameters: {', '.join(func['args'])}\nLine: {func['line']}",
                    'metadata': {
                        'type': 'function',
                        'file': file_path,
                        'name': func['name'],
                        'args': func['args'],
                        'line': func['line']
                    }
                })
        
        return chunks
    
    def build_index(self, chunks: List[Dict]):
        """Create FAISS index from chunks"""
        texts = [c['text'] for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=True)
        
        # Create FAISS index
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings.astype('float32'))
        self.metadata = [c['metadata'] for c in chunks]
        
        # Save
        os.makedirs(self.index_path, exist_ok=True)
        faiss.write_index(self.index, f"{self.index_path}/code.index")
        with open(f"{self.index_path}/metadata.json", 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        print(f"✓ Indexed {len(chunks)} chunks")
    
    def load_index(self):
        """Load existing FAISS index"""
        self.index = faiss.read_index(f"{self.index_path}/code.index")
        with open(f"{self.index_path}/metadata.json", 'r') as f:
            self.metadata = json.load(f)
        print(f"✓ Loaded index with {len(self.metadata)} chunks")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant code chunks"""
        query_emb = self.embedder.encode([query]).astype('float32')
        distances, indices = self.index.search(query_emb, top_k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            results.append({
                'metadata': self.metadata[idx],
                'score': float(dist)
            })
        return results
    
    def query(self, question: str, summary_path: str = None) -> str:
        """Answer question using RAG"""
        # Retrieve relevant chunks
        results = self.search(question, top_k=5)
        
        # Build context
        context_parts = []
        for r in results:
            meta = r['metadata']
            if meta['type'] == 'class':
                context_parts.append(f"Class: {meta['name']}\nFile: {meta['file']}\nMethods: {', '.join(meta['methods'])}\nLine: {meta['line']}")
            elif meta['type'] == 'function':
                context_parts.append(f"Function: {meta['name']}\nFile: {meta['file']}\nParams: {', '.join(meta['args'])}\nLine: {meta['line']}")
            else:
                context_parts.append(f"File: {meta['file']}\nClasses: {', '.join(meta.get('classes', []))}\nFunctions: {', '.join(meta.get('functions', []))}")
        
        context = "\n\n".join(context_parts)
        
        # Add call graph info if available
        if summary_path and os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                summary = json.load(f)
                most_called = summary.get('most_called', [])[:5]
                context += f"\n\nMost Called Functions: {', '.join([f'{name} ({count}x)' for name, count in most_called])}"
        
        # Generate answer
        prompt = f"""You are a code analysis expert. Answer the question using ONLY the provided codebase context.

Context from codebase:
{context}

Question: {question}

Instructions:
- Always cite exact file paths
- Reference specific classes/functions/line numbers
- For conversion errors, explain the root cause and provide a concrete fix
- Be precise and concise
- If context is insufficient, say so

Answer:"""

        response = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024
        )
        
        return response.choices[0].message.content


def main():
    """CLI for RAG system"""
    print("\n🧠 Code-Aware RAG System")
    print("=" * 60)
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY not found in environment variables")
        print("Create a .env file with: GROQ_API_KEY=your_key_here")
        return
    
    rag = CodeRAG(api_key)
    
    # Check if index exists
    if os.path.exists("faiss_index/code.index"):
        print("\n📚 Loading existing index...")
        rag.load_index()
    else:
        print("\n📚 Building new index...")
        print("Enter path to entities.json (from analyzer):")
        entities_path = input("> ").strip() or "analysis_output/entities.json"
        
        print("Enter path to source code directory:")
        source_dir = input("> ").strip() or r"C:\ErpNext_Code_Analyzer\erpnext\accounts"
        
        chunks = rag.prepare_chunks(entities_path, source_dir)
        rag.build_index(chunks)
    
    # Query loop
    print("\n💬 Ask questions about the codebase (type 'exit' to quit):")
    print("-" * 60)
    
    summary_path = "analysis_output/summary.json"
    
    while True:
        question = input("\n❓ Question: ").strip()
        
        if question.lower() in ['exit', 'quit', 'q']:
            break
        
        if not question:
            continue
        
        print("\n🔍 Searching...\n")
        answer = rag.query(question, summary_path)
        print(f"💡 Answer:\n{answer}\n")
        print("-" * 60)
    
    print("\n👋 Goodbye!")


if __name__ == '__main__':
    main()

import json
import threading
import numpy as np
from sqlalchemy.orm import Session
from backend.database import DocumentChunk

class NumPyVectorStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.chunks_cache = []
        self.embeddings_matrix = None
        self._is_initialized = False

    def initialize(self, db: Session):
        """Load all chunks and their embeddings from the database into memory."""
        with self.lock:
            chunks = db.query(DocumentChunk).filter(DocumentChunk.embedding_json != None).all()
            self.chunks_cache = []
            embeddings = []
            
            for chunk in chunks:
                try:
                    emb = json.loads(chunk.embedding_json)
                    if isinstance(emb, list) and len(emb) > 0:
                        self.chunks_cache.append({
                            "id": chunk.id,
                            "document_id": chunk.document_id,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "page_number": chunk.page_number
                        })
                        embeddings.append(emb)
                except Exception as e:
                    print(f"Error loading embedding for chunk {chunk.id}: {e}")
            
            if embeddings:
                self.embeddings_matrix = np.array(embeddings, dtype=np.float32)
            else:
                self.embeddings_matrix = None
            
            self._is_initialized = True
            print(f"NumPyVectorStore: loaded {len(self.chunks_cache)} chunks into memory.")

    def add_chunk(self, chunk_id: int, document_id: int, chunk_index: int, content: str, page_number: int, embedding: list):
        """Dynamically append a new chunk to the in-memory store."""
        with self.lock:
            emb_arr = np.array(embedding, dtype=np.float32).reshape(1, -1)
            self.chunks_cache.append({
                "id": chunk_id,
                "document_id": document_id,
                "chunk_index": chunk_index,
                "content": content,
                "page_number": page_number
            })
            if self.embeddings_matrix is not None:
                self.embeddings_matrix = np.vstack([self.embeddings_matrix, emb_arr])
            else:
                self.embeddings_matrix = emb_arr

    def search(self, db: Session, query_embedding: list, top_k: int = 5):
        """Perform cosine similarity search using NumPy."""
        # Ensure we are initialized
        if not self._is_initialized:
            self.initialize(db)
            
        with self.lock:
            if self.embeddings_matrix is None or len(self.chunks_cache) == 0:
                return []
            
            q_vec = np.array(query_embedding, dtype=np.float32)
            
            # Compute cosine similarity
            # cos(theta) = A . B / (||A|| ||B||)
            dot_products = np.dot(self.embeddings_matrix, q_vec)
            norms_matrix = np.linalg.norm(self.embeddings_matrix, axis=1)
            norm_q = np.linalg.norm(q_vec)
            
            # Avoid division by zero
            norms_matrix[norms_matrix == 0] = 1e-10
            if norm_q == 0:
                norm_q = 1e-10
                
            similarities = dot_products / (norms_matrix * norm_q)
            
            # Get indices of top K similarities
            top_k = min(top_k, len(self.chunks_cache))
            indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in indices:
                score = float(similarities[idx])
                chunk_data = self.chunks_cache[idx].copy()
                chunk_data["score"] = score
                results.append(chunk_data)
                
            return results

# Singleton instance
vector_store = NumPyVectorStore()

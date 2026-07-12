"""RAG utilities for semantic search in the Ecofix knowledge base."""

import os
import re
import json
import math
import time
import hashlib
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client_instance = None

def _get_client():
    global _client_instance
    if _client_instance is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment")
        _client_instance = genai.Client(api_key=api_key)
    return _client_instance


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(a * a for a in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


class RagIndex:
    """Handles parsing, embedding generation, caching and query retrieval."""
    
    def __init__(
        self,
        knowledge_base_path: str = "docs/knowledge_base",
        cache_path: str = "backend/agent/rag_cache.json"
    ):
        self.kb_path = knowledge_base_path
        self.cache_path = cache_path
        self.chunks: List[str] = []
        self.embeddings: List[List[float]] = []
        
    def _compute_file_hash(self) -> str:
        if not os.path.exists(self.kb_path):
            return ""
        hasher = hashlib.sha256()
        if os.path.isdir(self.kb_path):
            # Sort files to ensure deterministic hashing
            for root, _, files in os.walk(self.kb_path):
                for file in sorted(files):
                    if not file.endswith(".md"):
                        continue
                    file_path = os.path.join(root, file)
                    hasher.update(file.encode('utf-8'))
                    with open(file_path, 'rb') as f:
                        hasher.update(f.read())
        else:
            with open(self.kb_path, 'rb') as f:
                hasher.update(f.read())
        return hasher.hexdigest()
        
    def parse_chunks(self) -> List[str]:
        """Parse markdown files into chunks."""
        if not os.path.exists(self.kb_path):
            return []
            
        files_to_parse = []
        if os.path.isdir(self.kb_path):
            for root, _, files in os.walk(self.kb_path):
                for file in sorted(files):
                    if file.endswith(".md"):
                        files_to_parse.append(os.path.join(root, file))
        else:
            files_to_parse.append(self.kb_path)
            
        chunks = []
        for file_path in files_to_parse:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Split by markdown headers ## or ###
                sections = re.split(r'\n(?=#{2,3}\s)', content)
                for section in sections:
                    section = section.strip()
                    if not section:
                        continue
                    
                    # Special parsing for FAQ questions if it's the FAQ file
                    if "faq.md" in file_path.lower() or "## FAQ type" in section or "FAQ type" in section:
                        faq_parts = re.split(r'\n(?=\*\*[^*]+\*\*\n?)', section)
                        for part in faq_parts:
                            part = part.strip()
                            if not part or "## FAQ type" in part:
                                continue
                            chunks.append(part)
                    else:
                        chunks.append(section)
            except Exception as e:
                print(f"[RAG] Error parsing {file_path}: {e}")
                
        return chunks

    def load_index(self):
        """Load index from cache, or rebuild it if cache is stale or missing."""
        current_hash = self._compute_file_hash()
        
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    
                if cache_data.get("file_hash") == current_hash:
                    self.chunks = cache_data.get("chunks", [])
                    self.embeddings = cache_data.get("embeddings", [])
                    if self.chunks and self.embeddings and len(self.chunks) == len(self.embeddings):
                        print("[RAG] Loaded RAG index from cache successfully.")
                        return
            except Exception as e:
                print(f"[RAG] Error reading cache file: {e}. Rebuilding...")
                
        self.rebuild_index(current_hash)

    def rebuild_index(self, file_hash: str):
        """Rebuild the RAG index: parse, generate embeddings, and save cache."""
        print("[RAG] Rebuilding RAG index...")
        self.chunks = self.parse_chunks()
        if not self.chunks:
            self.embeddings = []
            return
            
        # Call Gemini API to generate embeddings, batching to respect free-tier quota
        try:
            print(f"[RAG] Generating embeddings for {len(self.chunks)} chunks...")
            batch_size = 90
            all_embeddings = []
            for i in range(0, len(self.chunks), batch_size):
                batch = self.chunks[i:i + batch_size]
                print(f"[RAG] Embedding batch {i // batch_size + 1} ({len(batch)} chunks)...")
                client = _get_client()
                res = client.models.embed_content(
                    model="text-embedding-004",
                    contents=batch,
                )
                all_embeddings.extend([e.values for e in res.embeddings])
                if i + batch_size < len(self.chunks):
                    time.sleep(60)
            # self.embeddings is the full list of embeddings
            self.embeddings = all_embeddings
            
            # Save to cache
            cache_data = {
                "file_hash": file_hash,
                "chunks": self.chunks,
                "embeddings": self.embeddings
            }
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print("[RAG] RAG index rebuilt and cached successfully.")
        except Exception as e:
            print(f"[RAG] Error generating embeddings or saving cache: {e}")
            # Fallback to empty embeddings
            self.embeddings = [[] for _ in self.chunks]

    def retrieve(self, query: str, top_n: int = 2) -> Dict[str, Any]:
        """Retrieve the top N most relevant chunks and the max similarity score."""
        if not self.chunks or not self.embeddings:
            return {"chunks": [], "max_score": 0.0}
            
        # Get query embedding
        try:
            client = _get_client()
            res = client.models.embed_content(
                model="text-embedding-004",
                contents=query,
            )
            query_embedding = res.embeddings[0].values
        except Exception as e:
            print(f"[RAG] Error generating query embedding: {e}")
            return {"chunks": [], "max_score": 0.0}
            
        # Calculate similarity with all chunks
        scores = []
        for i, chunk_emb in enumerate(self.embeddings):
            if not chunk_emb or not isinstance(chunk_emb, list):
                continue
            sim = cosine_similarity(query_embedding, chunk_emb)
            scores.append((sim, self.chunks[i]))
            
        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Get top N chunks
        max_score = scores[0][0] if scores else 0.0
        retrieved = [chunk for _, chunk in scores[:top_n]]
        return {"chunks": retrieved, "max_score": max_score}
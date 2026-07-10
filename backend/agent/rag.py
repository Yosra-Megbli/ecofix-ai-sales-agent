"""RAG utilities for semantic search in the Ecofix knowledge base."""

import os
import re
import json
import math
import hashlib
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure globally
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key, transport="rest")


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
        knowledge_base_path: str = "docs/ecofix-knowledge-base.md",
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
        with open(self.kb_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
        
    def parse_chunks(self) -> List[str]:
        """Parse markdown file into sections and individual FAQ questions."""
        if not os.path.exists(self.kb_path):
            return []
            
        with open(self.kb_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        chunks = []
        
        # Split by markdown headers ## or ###
        sections = re.split(r'\n(?=#{2,3}\s)', content)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # Check if it's the FAQ section
            if "## FAQ type" in section or "FAQ type" in section:
                # FAQ section contains bold questions: **Question?**
                # Split by the bold questions
                faq_parts = re.split(r'\n(?=\*\*[^*]+\*\*\n?)', section)
                for part in faq_parts:
                    part = part.strip()
                    if not part or "## FAQ type" in part:
                        continue
                    chunks.append(part)
            else:
                chunks.append(section)
                
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
            
        # Call Gemini API to batch generate embeddings
        try:
            print(f"[RAG] Generating embeddings for {len(self.chunks)} chunks...")
            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=self.chunks
            )
            # res["embedding"] is a list of embeddings
            self.embeddings = res["embedding"]
            
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

    def retrieve(self, query: str, top_n: int = 2) -> List[str]:
        """Retrieve the top N most relevant chunks for a query."""
        if not self.chunks or not self.embeddings:
            return []
            
        # Get query embedding
        try:
            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=query
            )
            query_embedding = res["embedding"]
        except Exception as e:
            print(f"[RAG] Error generating query embedding: {e}")
            return []
            
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
        retrieved = [chunk for _, chunk in scores[:top_n]]
        return retrieved

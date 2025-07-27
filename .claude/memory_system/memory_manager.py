#!/usr/bin/env python3
"""
Memory Manager for Claude Code Hook System
Provides ChromaDB vector storage and SQLite metadata storage
"""
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

import chromadb
from chromadb.config import Settings
from pydantic import BaseModel, Field


@dataclass
class MemoryConfig:
    """Configuration for memory system"""

    project_id: str
    project_path: str
    db_path: str = ".claude/memory_system/db"
    chroma_persist_path: str = ".claude/memory_system/chroma"
    collection_prefix: str = "claude_memories"
    max_results: int = 10
    similarity_threshold: float = 0.7


class Memory(BaseModel):
    """Memory data model"""

    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    project_id: str
    memory_type: str = "general"  # general, code_pattern, error_solution, etc.
    session_id: Optional[str] = None  # For grouping memories by session


class MemoryManager:
    """Manages project-based memories using ChromaDB and SQLite"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._ensure_directories()
        self._init_sqlite()
        self._init_chroma()

    def _ensure_directories(self):
        """Create necessary directories"""
        for path in [self.config.db_path, self.config.chroma_persist_path]:
            full_path = Path(self.config.project_path) / path
            full_path.mkdir(parents=True, exist_ok=True)

    def _init_sqlite(self):
        """Initialize SQLite database for metadata"""
        db_file = (
            Path(self.config.project_path)
            / self.config.db_path
            / f"{self.config.project_id}.db"
        )
        self.db = sqlite3.connect(str(db_file))
        self.db.row_factory = sqlite3.Row

        # Create tables
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed DATETIME,
                session_id TEXT
            )
        """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_stats (
                project_id TEXT PRIMARY KEY,
                total_memories INTEGER DEFAULT 0,
                last_updated DATETIME,
                config TEXT
            )
        """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                summary TEXT,
                memory_count INTEGER DEFAULT 0
            )
        """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_type 
            ON memories(project_id, memory_type)
        """
        )

        self.db.commit()

    def _init_chroma(self):
        """Initialize ChromaDB for vector storage"""
        persist_path = Path(self.config.project_path) / self.config.chroma_persist_path

        self.chroma_client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        collection_name = f"{self.config.collection_prefix}_{self.config.project_id}"

        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
        except ValueError:
            self.collection = self.chroma_client.create_collection(
                name=collection_name, metadata={"project_id": self.config.project_id}
            )

    def _generate_id(self, content: str, memory_type: str) -> str:
        """Generate unique ID for memory"""
        hash_input = f"{self.config.project_id}:{memory_type}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def store_memory(
        self, content: str, metadata: Dict[str, Any], memory_type: str = "general"
    ) -> str:
        """Store a memory with vector embedding and metadata"""
        memory_id = self._generate_id(content, memory_type)

        # Prepare metadata
        full_metadata = {
            "project_id": self.config.project_id,
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
            **metadata,
        }

        # Store in ChromaDB (handles embedding automatically)
        self.collection.upsert(
            ids=[memory_id], documents=[content], metadatas=[full_metadata]
        )

        # Store in SQLite
        self.db.execute(
            """
            INSERT OR REPLACE INTO memories 
            (id, project_id, memory_type, content, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                self.config.project_id,
                memory_type,
                content,
                json.dumps(metadata),
                datetime.now(),
            ),
        )

        # Update stats
        self._update_stats()
        self.db.commit()

        return memory_id

    def search_memories(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search memories using vector similarity"""
        limit = limit or self.config.max_results

        # Build where clause for filtering
        where: Dict[str, Any] = {"project_id": self.config.project_id}
        if memory_types:
            where["memory_type"] = {"$in": memory_types}

        # Search in ChromaDB
        results = self.collection.query(
            query_texts=[query], n_results=limit, where=where
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        # Update access stats
        memory_ids = results["ids"][0]
        self._update_access_stats(memory_ids)

        # Format results
        memories = []
        # Ensure we have all required result fields
        if results["distances"] and results["documents"] and results["metadatas"]:
            for i, memory_id in enumerate(memory_ids):
                if results["distances"][0][i] > self.config.similarity_threshold:
                    continue

                memories.append(
                    {
                        "id": memory_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": 1 - results["distances"][0][i],
                    }
                )

        return memories

    def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get specific memory by ID"""
        cursor = self.db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            return None

        self._update_access_stats([memory_id])

        return {
            "id": row["id"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]),
            "memory_type": row["memory_type"],
            "timestamp": row["timestamp"],
            "access_count": row["access_count"],
        }

    def list_memories(
        self, memory_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List memories with optional filtering"""
        query = """
            SELECT * FROM memories
            WHERE project_id = ?
        """
        params: List[Any] = [self.config.project_id]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self.db.execute(query, params)

        memories = []
        for row in cursor:
            memories.append(
                {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]),
                    "memory_type": row["memory_type"],
                    "timestamp": row["timestamp"],
                    "access_count": row["access_count"],
                }
            )

        return memories

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        # Delete from ChromaDB
        self.collection.delete(ids=[memory_id])

        # Delete from SQLite
        cursor = self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

        if cursor.rowcount > 0:
            self._update_stats()
            self.db.commit()
            return True

        return False

    def clear_project_memories(self) -> int:
        """Clear all memories for current project"""
        # Get count first
        cursor = self.db.execute(
            "SELECT COUNT(*) as count FROM memories WHERE project_id = ?",
            (self.config.project_id,),
        )
        count = cursor.fetchone()["count"]

        # Clear from ChromaDB
        self.collection.delete(where={"project_id": self.config.project_id})

        # Clear from SQLite
        self.db.execute(
            "DELETE FROM memories WHERE project_id = ?", (self.config.project_id,)
        )

        self._update_stats()
        self.db.commit()

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics for project"""
        cursor = self.db.execute(
            """
            SELECT 
                COUNT(*) as total,
                memory_type,
                AVG(access_count) as avg_access_count
            FROM memories
            WHERE project_id = ?
            GROUP BY memory_type
        """,
            (self.config.project_id,),
        )

        stats = {"project_id": self.config.project_id, "by_type": {}, "total": 0}

        for row in cursor:
            stats["by_type"][row["memory_type"]] = {
                "count": row["total"],
                "avg_access_count": row["avg_access_count"],
            }
            stats["total"] += row["total"]

        return stats

    def _update_stats(self):
        """Update project statistics"""
        cursor = self.db.execute(
            "SELECT COUNT(*) as count FROM memories WHERE project_id = ?",
            (self.config.project_id,),
        )
        count = cursor.fetchone()["count"]

        self.db.execute(
            """
            INSERT OR REPLACE INTO memory_stats
            (project_id, total_memories, last_updated, config)
            VALUES (?, ?, ?, ?)
        """,
            (
                self.config.project_id,
                count,
                datetime.now(),
                json.dumps(asdict(self.config)),
            ),
        )

    def _update_access_stats(self, memory_ids: List[str]):
        """Update access statistics for memories"""
        for memory_id in memory_ids:
            self.db.execute(
                """
                UPDATE memories 
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
            """,
                (datetime.now(), memory_id),
            )
        self.db.commit()


def get_memory_manager(project_path: str) -> MemoryManager:
    """Factory function to get memory manager for project"""
    # Derive project ID from path
    project_id = Path(project_path).name.replace(" ", "_").lower()

    config = MemoryConfig(project_id=project_id, project_path=project_path)

    return MemoryManager(config)

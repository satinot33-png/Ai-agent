"""
Message storage implementations for AI Agent.

This module provides concrete implementations of the MessageStore interface
for different storage backends (file, memory, database, etc.).

Each store handles:
- Persisting message exchanges
- Retrieving message history
- Clearing stored messages
- Thread-safe operations
"""

import asyncio
import json
import logging
from abc import ABC
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sqlite3
from contextlib import asynccontextmanager

from agent import MessageStore, AgentRequest, AgentResponse, setup_logger, AgentError, ErrorCode


logger = setup_logger(__name__)


# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================

class InMemoryMessageStore(MessageStore):
    """
    In-memory message storage implementation.
    
    Useful for testing and development. Messages are lost on process restart.
    Thread-safe using asyncio locks.
    """
    
    def __init__(self):
        self.storage: Dict[str, List[Dict[str, Any]]] = {}
        self.lock = asyncio.Lock()
        self.logger = setup_logger(f"{__name__}.InMemoryMessageStore")
    
    async def save(self, agent_id: str, request: AgentRequest, response: AgentResponse) -> None:
        """Save a message exchange in memory."""
        try:
            async with self.lock:
                if agent_id not in self.storage:
                    self.storage[agent_id] = []
                
                entry = {
                    "request": request.to_dict(),
                    "response": response.to_dict(),
                }
                self.storage[agent_id].append(entry)
            
            self.logger.debug(f"Saved message {request.message_id} for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    async def get_history(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve message history from memory."""
        try:
            async with self.lock:
                if agent_id not in self.storage:
                    return []
                
                messages = self.storage[agent_id]
                return messages[offset:offset + limit]
        except Exception as e:
            self.logger.error(f"Failed to retrieve history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    async def clear(self, agent_id: str) -> None:
        """Clear all messages for an agent."""
        try:
            async with self.lock:
                if agent_id in self.storage:
                    del self.storage[agent_id]
            self.logger.info(f"Cleared history for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )


# ============================================================================
# SQLITE DATABASE STORAGE
# ============================================================================

class SQLiteMessageStore(MessageStore):
    """
    SQLite database message storage implementation.
    
    Persistent storage with SQL queries. Thread-safe with connection pooling.
    """
    
    def __init__(self, db_path: str = "./agent_data/agent_messages.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(f"{__name__}.SQLiteMessageStore")
        
        # Initialize database schema
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    message_id TEXT UNIQUE NOT NULL,
                    request_content TEXT NOT NULL,
                    request_metadata TEXT,
                    response_content TEXT NOT NULL,
                    response_success BOOLEAN,
                    response_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_id ON messages(agent_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON messages(created_at)
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise AgentError(
                f"Database initialization error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    async def save(self, agent_id: str, request: AgentRequest, response: AgentResponse) -> None:
        """Save a message exchange to database."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._save_sync,
                agent_id,
                request,
                response
            )
            self.logger.debug(f"Saved message {request.message_id} for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    def _save_sync(self, agent_id: str, request: AgentRequest, response: AgentResponse) -> None:
        """Synchronous save operation."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Ensure agent exists
            cursor.execute("INSERT OR IGNORE INTO agents (agent_id) VALUES (?)", (agent_id,))
            
            # Insert message
            cursor.execute("""
                INSERT INTO messages (
                    agent_id, message_id, request_content, request_metadata,
                    response_content, response_success, response_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_id,
                request.message_id,
                request.content,
                json.dumps(request.metadata),
                response.content,
                response.success,
                response.error_message
            ))
            
            conn.commit()
        finally:
            conn.close()
    
    async def get_history(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve message history from database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._get_history_sync,
                agent_id,
                limit,
                offset
            )
        except Exception as e:
            self.logger.error(f"Failed to retrieve history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    def _get_history_sync(self, agent_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Synchronous history retrieval."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM messages
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (agent_id, limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    async def clear(self, agent_id: str) -> None:
        """Clear all messages for an agent."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._clear_sync, agent_id)
            self.logger.info(f"Cleared history for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    def _clear_sync(self, agent_id: str) -> None:
        """Synchronous clear operation."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE agent_id = ?", (agent_id,))
            conn.commit()
        finally:
            conn.close()


# ============================================================================
# JSONL FILE STORAGE (Enhanced)
# ============================================================================

class JsonlMessageStore(MessageStore):
    """
    JSONL (JSON Lines) file-based message storage implementation.
    
    Enhanced version with:
    - Automatic rotation when file size exceeds limit
    - Async file operations
    - Concurrent read/write safety
    """
    
    def __init__(self, storage_path: str = "./agent_data", max_file_size: int = 10 * 1024 * 1024):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size  # 10MB default
        self.logger = setup_logger(f"{__name__}.JsonlMessageStore")
        self.locks: Dict[str, asyncio.Lock] = {}
    
    def _get_agent_file(self, agent_id: str) -> Path:
        """Get the file path for an agent's messages."""
        return self.storage_path / f"{agent_id}_messages.jsonl"
    
    def _get_lock(self, agent_id: str) -> asyncio.Lock:
        """Get or create lock for agent."""
        if agent_id not in self.locks:
            self.locks[agent_id] = asyncio.Lock()
        return self.locks[agent_id]
    
    async def save(self, agent_id: str, request: AgentRequest, response: AgentResponse) -> None:
        """Save a message exchange to file."""
        try:
            lock = self._get_lock(agent_id)
            async with lock:
                agent_file = self._get_agent_file(agent_id)
                entry = {
                    "request": request.to_dict(),
                    "response": response.to_dict(),
                }
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._write_entry,
                    agent_file,
                    entry
                )
            
            self.logger.debug(f"Saved message {request.message_id} for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    def _write_entry(self, agent_file: Path, entry: Dict[str, Any]) -> None:
        """Write entry to file with rotation check."""
        # Check if rotation is needed
        if agent_file.exists() and agent_file.stat().st_size > self.max_file_size:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rotated_file = agent_file.with_stem(f"{agent_file.stem}_{timestamp}")
            agent_file.rename(rotated_file)
            self.logger.info(f"Rotated message file to {rotated_file.name}")
        
        # Append entry
        with open(agent_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    async def get_history(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve message history from file."""
        try:
            lock = self._get_lock(agent_id)
            async with lock:
                agent_file = self._get_agent_file(agent_id)
                
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    self._read_entries,
                    agent_file,
                    limit,
                    offset
                )
        except Exception as e:
            self.logger.error(f"Failed to retrieve history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    def _read_entries(self, agent_file: Path, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Read entries from file."""
        if not agent_file.exists():
            return []
        
        messages = []
        with open(agent_file, 'r') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        
        # Apply offset and limit
        return messages[offset:offset + limit]
    
    async def clear(self, agent_id: str) -> None:
        """Clear all messages for an agent."""
        try:
            lock = self._get_lock(agent_id)
            async with lock:
                agent_file = self._get_agent_file(agent_id)
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._delete_file, agent_file)
            
            self.logger.info(f"Cleared history for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear history: {e}")
            raise AgentError(
                f"Storage error: {str(e)}",
                error_code=ErrorCode.STORAGE_ERROR
            )
    
    def _delete_file(self, agent_file: Path) -> None:
        """Delete agent file."""
        if agent_file.exists():
            agent_file.unlink()


# ============================================================================
# STORAGE FACTORY
# ============================================================================

def create_store(
    storage_type: str,
    storage_path: str = "./agent_data"
) -> MessageStore:
    """
    Factory function to create a message store instance.
    
    Args:
        storage_type: Type of storage ("file", "memory", "sqlite", "jsonl")
        storage_path: Path for file-based storage
    
    Returns:
        Initialized MessageStore instance
    
    Raises:
        AgentError: If storage type is unknown or initialization fails
    """
    storage_type = storage_type.lower()
    
    if storage_type in ("file", "jsonl"):
        return JsonlMessageStore(storage_path)
    elif storage_type == "memory":
        return InMemoryMessageStore()
    elif storage_type == "sqlite":
        db_path = str(Path(storage_path) / "agent_messages.db")
        return SQLiteMessageStore(db_path)
    else:
        raise AgentError(
            f"Unknown storage type: {storage_type}",
            error_code=ErrorCode.CONFIG_ERROR
        )

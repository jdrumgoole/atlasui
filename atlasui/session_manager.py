"""
MongoDB session manager for maintaining persistent connections.

This module provides session management for MongoDB cluster connections,
allowing users to login once and maintain their connection throughout
their session.
"""

import uuid
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pymongo import MongoClient
import threading


class MongoSession:
    """Represents a MongoDB client session with metadata."""

    def __init__(
        self,
        session_id: str,
        client: MongoClient,
        cluster_name: str,
        username: str,
        connection_string: str
    ):
        self.session_id = session_id
        self.client = client
        self.cluster_name = cluster_name
        self.username = username
        self.connection_string = connection_string  # Store sanitized version
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()

    def touch(self):
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()

    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if the session has expired."""
        expiry_time = self.last_accessed + timedelta(minutes=timeout_minutes)
        return datetime.now() > expiry_time

    def close(self):
        """Close the MongoDB client connection."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass  # Ignore errors on close


class SessionManager:
    """
    Manages MongoDB client sessions.

    This class provides thread-safe session management for MongoDB connections,
    including automatic cleanup of expired sessions.
    """

    def __init__(self, session_timeout_minutes: int = 60):
        """
        Initialize the session manager.

        Args:
            session_timeout_minutes: How long a session remains valid without access
        """
        self._sessions: Dict[str, MongoSession] = {}
        self._lock = threading.Lock()
        self.session_timeout_minutes = session_timeout_minutes

    def create_session(
        self,
        client: MongoClient,
        cluster_name: str,
        username: str,
        connection_string: str
    ) -> str:
        """
        Create a new session for a MongoDB connection.

        Args:
            client: The authenticated MongoDB client
            cluster_name: Name of the cluster
            username: Username used for authentication
            connection_string: Sanitized connection string (without credentials)

        Returns:
            Session ID as a string
        """
        session_id = str(uuid.uuid4())
        session = MongoSession(
            session_id=session_id,
            client=client,
            cluster_name=cluster_name,
            username=username,
            connection_string=connection_string
        )

        with self._lock:
            self._sessions[session_id] = session

        return session_id

    def get_session(self, session_id: str) -> Optional[MongoSession]:
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            MongoSession if found and not expired, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            # Check if expired
            if session.is_expired(self.session_timeout_minutes):
                self._remove_session(session_id)
                return None

            # Update last accessed time
            session.touch()
            return session

    def _remove_session(self, session_id: str):
        """
        Remove a session (internal method, assumes lock is held).

        Args:
            session_id: The session ID to remove
        """
        session = self._sessions.pop(session_id, None)
        if session:
            session.close()

    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session and close its connection.

        Args:
            session_id: The session ID to remove

        Returns:
            True if session was removed, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                self._remove_session(session_id)
                return True
            return False

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if session.is_expired(self.session_timeout_minutes)
            ]

            for session_id in expired_ids:
                self._remove_session(session_id)

        return len(expired_ids)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a session without the client object.

        Args:
            session_id: The session ID

        Returns:
            Dictionary with session info or None if not found
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        return {
            "session_id": session.session_id,
            "cluster_name": session.cluster_name,
            "username": session.username,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
        }

    def list_sessions(self) -> list[Dict[str, Any]]:
        """
        List all active sessions.

        Returns:
            List of session info dictionaries
        """
        with self._lock:
            return [
                {
                    "session_id": session.session_id,
                    "cluster_name": session.cluster_name,
                    "username": session.username,
                    "created_at": session.created_at.isoformat(),
                    "last_accessed": session.last_accessed.isoformat(),
                }
                for session in self._sessions.values()
            ]

    def close_all_sessions(self):
        """Close all sessions and clear the session store."""
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()

    def __len__(self) -> int:
        """Return the number of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    Returns:
        The global SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(session_timeout_minutes=60)
    return _session_manager

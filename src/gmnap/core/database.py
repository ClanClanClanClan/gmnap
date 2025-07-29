"""
GMNAP Database Management

Provides database abstraction layer for storing and retrieving mathematician entries.
"""

import sqlite3
import json
import logging
import threading
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class GMNAPDatabase:
    """
    Database management for GMNAP mathematician entries.
    
    Provides CRUD operations and schema management for the mathematician database.
    """
    
    def __init__(self, db_path: str = "gmnap.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger("gmnap.database")
        self._table_lock = threading.Lock()  # Thread-safe table creation
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if it doesn't exist (thread-safe)."""
        with self._table_lock:  # Ensure only one thread initializes at a time
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Create main entries table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mathematician_entries (
                            global_id TEXT PRIMARY KEY,
                            canonical_latin TEXT NOT NULL,
                            canonical_native TEXT,
                            entry_data TEXT NOT NULL,
                            region_code TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            version TEXT DEFAULT 'v7'
                        )
                    ''')
                    
                    # Create index on canonical_latin for faster searches
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_canonical_latin 
                        ON mathematician_entries(canonical_latin)
                    ''')
                    
                    # Create index on region_code
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_region_code 
                        ON mathematician_entries(region_code)
                    ''')
                    
                    conn.commit()
                    self.logger.info(f"Database initialized at {self.db_path}")
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")
                raise
    
    def store_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Store a mathematician entry in the database.
        
        Args:
            entry: Complete entry dictionary
            
        Returns:
            True if stored successfully
        """
        try:
            global_id = entry.get('GlobalID')
            canonical_latin = entry.get('CanonicalLatin')
            canonical_native = entry.get('CanonicalNative')
            region_code = entry.get('RegionCode')
            
            if not global_id or not canonical_latin:
                raise ValueError("Entry must contain GlobalID and CanonicalLatin")
            
            # Validate GlobalID to prevent injection attacks
            if not isinstance(global_id, str):
                raise TypeError("GlobalID must be a string")
            
            # Reject obvious injection attempts
            dangerous_patterns = [
                '\x00', '../', '..\\', '\\', '\n', '\r', '\t', '--', ';',
                ' OR ', ' or ', "'", '"', 'DROP ', 'INSERT ', 'UPDATE ', 'DELETE ',
                'drop ', 'insert ', 'update ', 'delete ', '/*', '*/', 'exec', 'EXEC',
                'union ', 'UNION ', 'select ', 'SELECT '
            ]
            for pattern in dangerous_patterns:
                if pattern in global_id:
                    raise ValueError(f"Invalid GlobalID contains dangerous pattern: {pattern}")
            
            # Length check
            if len(global_id) > 100:
                raise ValueError(f"GlobalID too long: {len(global_id)} characters")
            
            # Basic alphanumeric + limited punctuation check  
            if not all(c.isalnum() or c in '-_=+' for c in global_id):
                raise ValueError(f"GlobalID contains invalid characters")
            
            now = datetime.utcnow().isoformat()
            entry_json = json.dumps(entry, ensure_ascii=False)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or replace entry
                cursor.execute('''
                    INSERT OR REPLACE INTO mathematician_entries 
                    (global_id, canonical_latin, canonical_native, entry_data, 
                     region_code, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (global_id, canonical_latin, canonical_native, entry_json,
                      region_code, now, now))
                
                conn.commit()
                self.logger.debug(f"Stored entry {global_id}: {canonical_latin}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store entry: {e}")
            return False
    
    def get_entry(self, global_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an entry by GlobalID.
        
        Args:
            global_id: GlobalID to look up
            
        Returns:
            Entry dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT entry_data FROM mathematician_entries WHERE global_id = ?',
                    (global_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get entry {global_id}: {e}")
            return None
    
    def search_entries(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search entries by canonical name.
        
        Args:
            query: Search query (partial name match)
            limit: Maximum number of results
            
        Returns:
            List of matching entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT entry_data FROM mathematician_entries 
                    WHERE canonical_latin LIKE ? 
                    ORDER BY canonical_latin 
                    LIMIT ?
                ''', (f'%{query}%', limit))
                
                rows = cursor.fetchall()
                return [json.loads(row[0]) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to search entries: {e}")
            return []
    
    def get_entries_by_region(self, region_code: str) -> List[Dict[str, Any]]:
        """
        Get all entries for a specific region.
        
        Args:
            region_code: Region code (e.g., "A1", "B1")
            
        Returns:
            List of entries for the region
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT entry_data FROM mathematician_entries WHERE region_code = ?',
                    (region_code,)
                )
                
                rows = cursor.fetchall()
                return [json.loads(row[0]) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get entries for region {region_code}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total entries
                cursor.execute('SELECT COUNT(*) FROM mathematician_entries')
                total_entries = cursor.fetchone()[0]
                
                # Entries by region
                cursor.execute('''
                    SELECT region_code, COUNT(*) 
                    FROM mathematician_entries 
                    GROUP BY region_code 
                    ORDER BY COUNT(*) DESC
                ''')
                region_stats = dict(cursor.fetchall())
                
                # Database file size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    "total_entries": total_entries,
                    "regions": region_stats,
                    "database_size_bytes": db_size,
                    "database_path": self.db_path
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}
    
    def delete_entry(self, global_id: str) -> bool:
        """
        Delete an entry by GlobalID.
        
        Args:
            global_id: GlobalID to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM mathematician_entries WHERE global_id = ?',
                    (global_id,)
                )
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    self.logger.info(f"Deleted entry {global_id}")
                else:
                    self.logger.warning(f"Entry {global_id} not found for deletion")
                
                return deleted
                
        except Exception as e:
            self.logger.error(f"Failed to delete entry {global_id}: {e}")
            return False
# src\services\ticker_cache.py

import pickle
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
from functools import wraps

class StockCache:
    """
    Thread-safe singleton cache manager for TickerResearch objects.

    Uses SQLite for persistent storage with pickle serialization.
    Significantly improves performance by avoiding repeated Yahoo Finance API calls.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure single cache instance using double-checked locking pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        """
        Initialize cache settings and database.
        
        Only runs on first instantiation due to singleton pattern.
        Creates cache directory and SQLite database if they don't exist!
        """
        if not hasattr(self, 'initialized'):
            self.cache_dir = Path.home() / '.cache' / 'stock_info'
            self.db_path = self.cache_dir / 'ticker_cache.db'
            self.cache_enabled = True
            self.cache_duration = timedelta(hours=24)
            self.initialized = True
            self._init_db()
    
    def _init_db(self):
        """
        Initialize SQLite database with required schema.
        
        Creates ticker_cache table if it doesn't exist with:
        - symbol: Unique ticker symbol (PRIMARY KEY)
        - data: Pickled TickerResearch object
        - timestamp: ISO format cache timestamp
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ticker_cache (
                    symbol TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def enable(self):
        """Enable cache for future TickerResearch fetching and retrieval"""
        self.cache_enabled = True
    
    def disable(self):
        """Disable cache for future TickerResearch fetching and retrieval"""
        self.cache_enabled = False
    
    def set_duration(self, duration: timedelta):
        """
        Set cache entry lifetime.
        
        Args:
            duration: How long entries in cache should be considered valid
        """
        self.cache_duration = duration
    
    def clear(self) -> bool:
        """
        Clear all cached data from database.
        
        Returns:
            bool: True if successfully cleared, False if error
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM ticker_cache")
            return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
    
    def get(self, symbol: str) -> Optional[Any]:
        """
        Retrieve cached ticker if valid and not expired.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Cached TickerResearch object or None if:
            - Cache disabled
            - Symbol not found
            - Cache entry expired
            - Any error occurs during retrieval
        """
        if not self.cache_enabled:
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data, timestamp FROM ticker_cache WHERE symbol = ?",
                    (symbol.upper(),)
                )
                result = cursor.fetchone()
                
                if result:
                    data, timestamp = result
                    cache_time = datetime.fromisoformat(timestamp)
                    
                    if datetime.now() - cache_time < self.cache_duration:
                        return pickle.loads(data)
                        
                    # delete data if it has been cached longer than self.cache_duration
                    conn.execute(
                        "DELETE FROM ticker_cache WHERE symbol = ?",
                        (symbol.upper(),)
                    )
                return None
        except Exception as e:
            print(f"Error retrieving from cache: {e}")
            return None
    
    def set(self, symbol: str, ticker_object: Any) -> bool:
        """
        Cache a ticker object with the current timestamp.
        
        Args:
            symbol: Stock ticker symbol
            ticker_object: TickerResearch obj to cache
            
        Returns:
            bool: True if successfully cached, False otherwise
        """
        if not self.cache_enabled:
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                serialized_data = pickle.dumps(ticker_object)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ticker_cache (symbol, data, timestamp)
                    VALUES (?, ?, ?)
                    """,
                    (
                        symbol.upper(),
                        serialized_data,
                        datetime.now().isoformat()
                    )
                )
            return True
        except Exception as e:
            print(f"Error caching data: {e}")
            return False

def use_cache(func):
    """
    Decorator to handle caching for TickerResearch initialization.
    
    Wraps initialization of all new TickerResearch object to:
    1. First check cache before expensive data fetching
    2. Update cache after fresh data fetch
    3. Monitor and report performance timing to emphasize the benefit of caching
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        import time
        start_time = time.time()
        cache = StockCache()
        
        if cache.cache_enabled:
            cached_ticker = cache.get(self.symbol)
            if cached_ticker is not None:
                # copy cached data to self in order to use
                self.__dict__.update(cached_ticker.__dict__)
                elapsed = time.time() - start_time
                print(f"- Fetched cached data for {self.symbol.upper()} in {elapsed:.2f}s")
                return
        
        # no cache hit if we are here, so proceed with normal init and fetch fresh data
        func(self, *args, **kwargs)
        
        # now cache fresh data we just grabbed
        if cache.cache_enabled:
            cache.set(self.symbol, self)
        
        # elapsed time should be considerably longer
        elapsed = time.time() - start_time
        print(f"- Fetched fresh data for {self.symbol.upper()} in {elapsed:.2f}s")
            
    return wrapper
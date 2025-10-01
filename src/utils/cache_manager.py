"""
Data Cache Manager

Intelligent caching system for API data to avoid redundant requests and improve performance.
Supports both TradingView and Polygon.io data with configurable expiration and storage.
"""

import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


class DataCacheManager:
    """Manage caching for market data APIs with intelligent expiration and cleanup."""
    
    def __init__(self, cache_dir: str = "cache", max_cache_size_mb: int = 100):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            max_cache_size_mb: Maximum cache size in MB before cleanup
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different data types
        (self.cache_dir / "tv_data").mkdir(exist_ok=True)
        (self.cache_dir / "polygon_data").mkdir(exist_ok=True)
        (self.cache_dir / "metadata").mkdir(exist_ok=True)
        
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024
        
        # Cache expiration settings (in hours)
        self.expiration_times = {
            'tv_stock_data': 4,      # TradingView stock data expires in 4 hours (market hours)
            'tv_returns_data': 4,     # Returns data expires in 4 hours
            'polygon_options': 1,     # Options data expires in 1 hour (more volatile)
            'polygon_stock_price': 4, # Stock prices expire in 4 hours
            'metadata': 24            # Metadata expires in 24 hours
        }
        
        print(f"📁 Data Cache Manager initialized")
        print(f"   Cache directory: {self.cache_dir.absolute()}")
        print(f"   Max cache size: {max_cache_size_mb} MB")
        
        # Perform initial cleanup
        self._cleanup_expired_cache()
    
    def _generate_cache_key(self, data_type: str, symbol: str = None, **kwargs) -> str:
        """
        Generate a unique cache key for the data.
        
        Args:
            data_type: Type of data (tv_stock_data, polygon_options, etc.)
            symbol: Stock symbol (if applicable)
            **kwargs: Additional parameters that affect the data
            
        Returns:
            Unique cache key string
        """
        key_parts = [data_type]
        
        if symbol:
            key_parts.append(symbol.upper())
        
        # Sort kwargs for consistent key generation
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}={value}")
        
        key_string = "_".join(key_parts)
        
        # Create hash for very long keys
        if len(key_string) > 100:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{data_type}_{symbol}_{key_hash[:8]}" if symbol else f"{data_type}_{key_hash[:8]}"
        
        return key_string
    
    def _get_cache_path(self, cache_key: str, data_type: str) -> Path:
        """Get the file path for a cache entry."""
        if data_type.startswith('tv_'):
            subdir = "tv_data"
        elif data_type.startswith('polygon_'):
            subdir = "polygon_data"
        else:
            subdir = "metadata"
        
        return self.cache_dir / subdir / f"{cache_key}.pkl"
    
    def _is_expired(self, cache_path: Path, data_type: str) -> bool:
        """Check if a cache entry has expired."""
        if not cache_path.exists():
            return True
        
        expiration_hours = self.expiration_times.get(data_type, 4)
        expiration_time = datetime.now() - timedelta(hours=expiration_hours)
        
        file_modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return file_modified < expiration_time
    
    def get(self, data_type: str, symbol: str = None, **kwargs) -> Optional[Any]:
        """
        Retrieve data from cache if available and not expired.
        
        Args:
            data_type: Type of data to retrieve
            symbol: Stock symbol (if applicable)
            **kwargs: Additional parameters
            
        Returns:
            Cached data or None if not available/expired
        """
        try:
            cache_key = self._generate_cache_key(data_type, symbol, **kwargs)
            cache_path = self._get_cache_path(cache_key, data_type)
            
            if self._is_expired(cache_path, data_type):
                if cache_path.exists():
                    cache_path.unlink()  # Remove expired cache
                return None
            
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            
            print(f"  💾 Cache HIT: {data_type} for {symbol or 'N/A'}")
            return cached_data
            
        except Exception as e:
            print(f"  ⚠️ Cache read error for {cache_key}: {e}")
            return None
    
    def set(self, data_type: str, data: Any, symbol: str = None, **kwargs) -> bool:
        """
        Store data in cache.
        
        Args:
            data_type: Type of data to store
            data: Data to cache
            symbol: Stock symbol (if applicable)
            **kwargs: Additional parameters
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(data_type, symbol, **kwargs)
            cache_path = self._get_cache_path(cache_key, data_type)
            
            # Create directory if it doesn't exist
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"  💾 Cache SET: {data_type} for {symbol or 'N/A'}")
            
            # Check cache size and cleanup if needed
            self._check_cache_size()
            
            return True
            
        except Exception as e:
            print(f"  ⚠️ Cache write error for {cache_key}: {e}")
            return False
    
    def _check_cache_size(self):
        """Check cache size and perform cleanup if necessary."""
        total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
        
        if total_size > self.max_cache_size_bytes:
            print(f"  🧹 Cache size exceeded ({total_size // 1024 // 1024} MB), cleaning up...")
            self._cleanup_old_cache()
    
    def _cleanup_expired_cache(self):
        """Remove expired cache entries."""
        expired_count = 0
        
        for cache_file in self.cache_dir.rglob('*.pkl'):
            # Determine data type from path
            if 'tv_data' in str(cache_file):
                data_type = 'tv_stock_data'  # Default for TV data
            elif 'polygon_data' in str(cache_file):
                data_type = 'polygon_options'  # Default for Polygon data
            else:
                data_type = 'metadata'
            
            if self._is_expired(cache_file, data_type):
                cache_file.unlink()
                expired_count += 1
        
        if expired_count > 0:
            print(f"  🧹 Cleaned up {expired_count} expired cache entries")
    
    def _cleanup_old_cache(self):
        """Remove oldest cache entries to free space."""
        cache_files = []
        
        for cache_file in self.cache_dir.rglob('*.pkl'):
            if cache_file.is_file():
                cache_files.append((cache_file, cache_file.stat().st_mtime))
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[1])
        
        # Remove oldest 25% of files
        files_to_remove = len(cache_files) // 4
        
        for cache_file, _ in cache_files[:files_to_remove]:
            cache_file.unlink()
        
        print(f"  🧹 Removed {files_to_remove} old cache entries")
    
    def clear_cache(self, data_type: str = None, symbol: str = None):
        """
        Clear cache entries.
        
        Args:
            data_type: Specific data type to clear (None for all)
            symbol: Specific symbol to clear (None for all)
        """
        cleared_count = 0
        
        for cache_file in self.cache_dir.rglob('*.pkl'):
            should_remove = True
            
            if data_type:
                # Check if file matches data type
                if data_type.startswith('tv_') and 'tv_data' not in str(cache_file):
                    should_remove = False
                elif data_type.startswith('polygon_') and 'polygon_data' not in str(cache_file):
                    should_remove = False
            
            if symbol and should_remove:
                # Check if file contains symbol
                if symbol.upper() not in cache_file.stem.upper():
                    should_remove = False
            
            if should_remove:
                cache_file.unlink()
                cleared_count += 1
        
        print(f"  🧹 Cleared {cleared_count} cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'tv_data_files': 0,
            'polygon_data_files': 0,
            'metadata_files': 0,
            'oldest_entry': None,
            'newest_entry': None
        }
        
        oldest_time = float('inf')
        newest_time = 0
        
        for cache_file in self.cache_dir.rglob('*.pkl'):
            if cache_file.is_file():
                stats['total_files'] += 1
                stats['total_size_mb'] += cache_file.stat().st_size
                
                # Categorize by subdirectory
                if 'tv_data' in str(cache_file):
                    stats['tv_data_files'] += 1
                elif 'polygon_data' in str(cache_file):
                    stats['polygon_data_files'] += 1
                else:
                    stats['metadata_files'] += 1
                
                # Track oldest and newest
                mtime = cache_file.stat().st_mtime
                if mtime < oldest_time:
                    oldest_time = mtime
                    stats['oldest_entry'] = datetime.fromtimestamp(mtime)
                if mtime > newest_time:
                    newest_time = mtime
                    stats['newest_entry'] = datetime.fromtimestamp(mtime)
        
        stats['total_size_mb'] = stats['total_size_mb'] / 1024 / 1024  # Convert to MB
        
        return stats
    
    def print_cache_stats(self):
        """Print cache statistics."""
        stats = self.get_cache_stats()
        
        print(f"\n📊 Cache Statistics:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total size: {stats['total_size_mb']:.1f} MB")
        print(f"   TradingView data: {stats['tv_data_files']} files")
        print(f"   Polygon.io data: {stats['polygon_data_files']} files")
        print(f"   Metadata: {stats['metadata_files']} files")
        
        if stats['oldest_entry']:
            print(f"   Oldest entry: {stats['oldest_entry'].strftime('%Y-%m-%d %H:%M:%S')}")
        if stats['newest_entry']:
            print(f"   Newest entry: {stats['newest_entry'].strftime('%Y-%m-%d %H:%M:%S')}")


# Global cache manager instance
cache_manager = DataCacheManager()


def get_cache_manager() -> DataCacheManager:
    """Get the global cache manager instance."""
    return cache_manager


def enable_caching(cache_dir: str = "cache", max_size_mb: int = 100):
    """Enable caching with custom settings."""
    global cache_manager
    cache_manager = DataCacheManager(cache_dir, max_size_mb)
    return cache_manager


def disable_caching():
    """Disable caching by clearing the global instance."""
    global cache_manager
    cache_manager = None


if __name__ == "__main__":
    # Test the cache manager
    print("🧪 Testing Data Cache Manager")
    print("=" * 40)
    
    cache = DataCacheManager("test_cache", 10)
    
    # Test storing and retrieving data
    test_data = {"symbol": "AAPL", "price": 150.0, "timestamp": datetime.now()}
    
    # Store data
    cache.set("tv_stock_data", test_data, symbol="AAPL", days=180)
    
    # Retrieve data
    retrieved = cache.get("tv_stock_data", symbol="AAPL", days=180)
    
    if retrieved:
        print("✅ Cache test passed - data retrieved successfully")
        print(f"   Retrieved: {retrieved}")
    else:
        print("❌ Cache test failed - no data retrieved")
    
    # Print stats
    cache.print_cache_stats()
    
    # Cleanup
    cache.clear_cache()
    print("🧹 Test cache cleared")
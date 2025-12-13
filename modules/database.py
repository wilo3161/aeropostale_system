# modules/cache.py
"""
Sistema de caché inteligente con invalidation automática.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
import hashlib
import json

logger = logging.getLogger(__name__)

class CacheEntry:
    """Entrada individual del caché"""
    
    def __init__(self, key: str, value: Any, ttl: int = 300):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl  # Time To Live en segundos
        self.access_count = 0
        self.last_accessed = self.created_at
        self.tags: List[str] = []
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado"""
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    def access(self) -> Any:
        """Registra un acceso y retorna el valor"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value
    
    def add_tag(self, tag: str):
        """Agrega una etiqueta a la entrada"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Verifica si la entrada tiene una etiqueta específica"""
        return tag in self.tags


class SmartCache:
    """Sistema de caché inteligente con invalidation por tags"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'size': 0
        }
        self.lock = threading.RLock()
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Inicia hilo para limpieza periódica"""
        def cleanup_loop():
            while True:
                try:
                    self._cleanup_expired()
                    time.sleep(60)  # Limpiar cada minuto
                except Exception as e:
                    logger.error(f"Error en hilo de limpieza: {e}")
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor del caché
        
        Args:
            key: Clave del caché
            default: Valor por defecto si no se encuentra
        
        Returns:
            Valor almacenado o default
        """
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_expired():
                    del self.cache[key]
                    self.stats['expirations'] += 1
                    self.stats['misses'] += 1
                    self.stats['size'] = len(self.cache)
                    return default
                
                self.stats['hits'] += 1
                return entry.access()
            
            self.stats['misses'] += 1
            return default
    
    def set(self, key: str, value: Any, ttl: int = 300, tags: List[str] = None):
        """
        Almacena un valor en el caché
        
        Args:
            key: Clave del caché
            value: Valor a almacenar
            ttl: Time To Live en segundos
            tags: Etiquetas para invalidation por grupo
        """
        with self.lock:
            # Verificar si necesitamos hacer espacio
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_oldest()
            
            # Crear nueva entrada
            entry = CacheEntry(key, value, ttl)
            
            if tags:
                for tag in tags:
                    entry.add_tag(tag)
            
            self.cache[key] = entry
            self.stats['size'] = len(self.cache)
    
    def _evict_oldest(self):
        """Elimina la entrada menos usada recientemente"""
        if not self.cache:
            return
        
        oldest_key = None
        oldest_time = datetime.now()
        
        for key, entry in self.cache.items():
            if entry.last_accessed < oldest_time:
                oldest_time = entry.last_accessed
                oldest_key = key
        
        if oldest_key:
            del self.cache[oldest_key]
            self.stats['evictions'] += 1
            self.stats['size'] = len(self.cache)
    
    def _cleanup_expired(self):
        """Limpia entradas expiradas"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
                self.stats['expirations'] += 1
            
            if expired_keys:
                self.stats['size'] = len(self.cache)
                logger.debug(f"Limpiadas {len(expired_keys)} entradas expiradas")
    
    def invalidate(self, key: str):
        """Invalida una entrada específica"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['size'] = len(self.cache)
                return True
            return False
    
    def invalidate_by_tag(self, tag: str):
        """Invalida todas las entradas con una etiqueta específica"""
        with self.lock:
            keys_to_delete = [
                key for key, entry in self.cache.items()
                if entry.has_tag(tag)
            ]
            
            for key in keys_to_delete:
                del self.cache[key]
            
            self.stats['size'] = len(self.cache)
            
            if keys_to_delete:
                logger.debug(f"Invalidadas {len(keys_to_delete)} entradas con tag '{tag}'")
                return len(keys_to_delete)
            
            return 0
    
    def invalidate_by_pattern(self, pattern: str):
        """Invalida todas las entradas cuyas claves coincidan con un patrón"""
        with self.lock:
            import fnmatch
            keys_to_delete = [
                key for key in self.cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            
            for key in keys_to_delete:
                del self.cache[key]
            
            self.stats['size'] = len(self.cache)
            
            if keys_to_delete:
                logger.debug(f"Invalidadas {len(keys_to_delete)} entradas con patrón '{pattern}'")
                return len(keys_to_delete)
            
            return 0
    
    def clear(self):
        """Limpia todo el caché"""
        with self.lock:
            self.cache.clear()
            self.stats['size'] = 0
            logger.info("Caché limpiado completamente")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        with self.lock:
            total_accesses = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_accesses * 100) if total_accesses > 0 else 0
            
            # Calcular eficiencia del caché
            efficiency = "alta" if hit_rate > 80 else "media" if hit_rate > 50 else "baja"
            
            return {
                **self.stats,
                'hit_rate': f"{hit_rate:.1f}%",
                'efficiency': efficiency,
                'memory_usage': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> str:
        """Estima el uso de memoria del caché"""
        try:
            import sys
            total_size = 0
            for key, entry in self.cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(entry.value)
            
            if total_size < 1024:
                return f"{total_size} B"
            elif total_size < 1024 * 1024:
                return f"{total_size / 1024:.1f} KB"
            else:
                return f"{total_size / (1024 * 1024):.1f} MB"
        except:
            return "desconocido"
    
    def get_keys(self) -> List[str]:
        """Obtiene todas las claves del caché"""
        with self.lock:
            return list(self.cache.keys())
    
    def get_entries_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Obtiene todas las entradas con una etiqueta específica"""
        with self.lock:
            entries = []
            for key, entry in self.cache.items():
                if entry.has_tag(tag):
                    entries.append({
                        'key': key,
                        'value': entry.value,
                        'created_at': entry.created_at,
                        'last_accessed': entry.last_accessed,
                        'access_count': entry.access_count,
                        'ttl': entry.ttl,
                        'tags': entry.tags
                    })
            return entries


class CacheManager:
    """Gestor de caché con funciones avanzadas"""
    
    def __init__(self):
        self.cache = SmartCache()
        self.namespaces: Dict[str, SmartCache] = {}
    
    def get_namespace(self, namespace: str) -> SmartCache:
        """Obtiene o crea un namespace de caché"""
        if namespace not in self.namespaces:
            self.namespaces[namespace] = SmartCache(max_size=500)
        return self.namespaces[namespace]
    
    def memoize(self, ttl: int = 300, tags: List[str] = None, namespace: str = "default"):
        """
        Decorador para cachear resultados de funciones
        
        Args:
            ttl: Time To Live en segundos
            tags: Etiquetas para la entrada
            namespace: Namespace del caché
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generar clave única basada en la función y argumentos
                cache_key = self._generate_function_key(func, args, kwargs)
                cache_instance = self.get_namespace(namespace)
                
                # Intentar obtener del caché
                cached_result = cache_instance.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Ejecutar función y cachear resultado
                result = func(*args, **kwargs)
                cache_instance.set(cache_key, result, ttl=ttl, tags=tags)
                
                return result
            return wrapper
        return decorator
    
    def _generate_function_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Genera una clave única para una función y sus argumentos"""
        func_name = func.__name__
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))
        
        key_data = f"{func_name}_{args_str}_{kwargs_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def invalidate_function_cache(self, func_name: str, namespace: str = "default"):
        """Invalida el caché de una función específica"""
        cache_instance = self.get_namespace(namespace)
        pattern = f"*{func_name}*"
        return cache_instance.invalidate_by_pattern(pattern)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas globales de todos los namespaces"""
        global_stats = {
            'total_namespaces': len(self.namespaces),
            'namespaces': {},
            'global_hit_rate': 0,
            'total_entries': 0
        }
        
        total_hits = 0
        total_misses = 0
        
        for namespace, cache_instance in self.namespaces.items():
            stats = cache_instance.get_stats()
            global_stats['namespaces'][namespace] = stats
            
            total_hits += stats['hits']
            total_misses += stats['misses']
            global_stats['total_entries'] += stats['size']
        
        total_accesses = total_hits + total_misses
        if total_accesses > 0:
            global_stats['global_hit_rate'] = f"{(total_hits / total_accesses * 100):.1f}%"
        
        return global_stats


# Singleton global
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Obtiene la instancia singleton de CacheManager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

# Decorador de conveniencia
def cached(ttl: int = 300, tags: List[str] = None, namespace: str = "default"):
    """Decorador para cachear funciones"""
    return get_cache_manager().memoize(ttl=ttl, tags=tags, namespace=namespace)

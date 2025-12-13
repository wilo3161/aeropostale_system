# modules/error_handler.py
"""
Sistema centralizado de manejo de errores para el sistema Aeropostale.
"""

import traceback
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
import pandas as pd

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Manejo centralizado de errores"""
    
    # Categorías de errores
    ERROR_CATEGORIES = {
        'database': {
            'keywords': ['connection', 'query', 'timeout', 'sql', 'database', 'supabase'],
            'user_message': "❌ Error de conexión con la base de datos. Intente nuevamente en unos minutos.",
            'severity': 'high'
        },
        'api': {
            'keywords': ['api', 'http', 'request', 'key', 'authentication', 'rate limit'],
            'user_message': "🔌 Error de conexión con servicio externo. Verifique su conexión a internet.",
            'severity': 'medium'
        },
        'file': {
            'keywords': ['file', 'path', 'io', 'permission', 'not found', 'corrupt'],
            'user_message': "📄 Error al procesar archivo. Verifique el formato y permisos.",
            'severity': 'medium'
        },
        'validation': {
            'keywords': ['validation', 'format', 'type', 'range', 'invalid'],
            'user_message': "📝 Error en los datos ingresados. Revise los valores y formatos.",
            'severity': 'low'
        },
        'network': {
            'keywords': ['network', 'connection', 'timeout', 'socket', 'host'],
            'user_message': "🌐 Error de red. Verifique su conexión a internet.",
            'severity': 'medium'
        }
    }
    
    def __init__(self):
        self.error_log: List[Dict] = []
        self.alert_threshold = 5  # Alertar después de 5 errores similares
        self.max_log_size = 1000  # Máximo de errores en memoria
        self._notification_callbacks = []
    
    def handle(self, error: Exception, context: Optional[Dict] = None, 
               user_context: Optional[str] = None) -> str:
        """
        Maneja un error de manera centralizada
        
        Args:
            error: Excepción capturada
            context: Contexto adicional para debugging
            user_context: Contexto amigable para el usuario
            
        Returns:
            Mensaje amigable para el usuario
        """
        # Generar ID único para el error
        error_id = str(uuid.uuid4())[:8]
        
        # Categorizar el error
        category = self._categorize_error(error)
        category_info = self.ERROR_CATEGORIES.get(category, {})
        
        # Crear registro de error
        error_info = {
            'id': error_id,
            'timestamp': datetime.now().isoformat(),
            'type': type(error).__name__,
            'message': str(error),
            'category': category,
            'severity': category_info.get('severity', 'unknown'),
            'context': context or {},
            'user_context': user_context,
            'traceback': traceback.format_exc(),
            'resolved': False,
            'retry_count': 0
        }
        
        # Guardar en log
        self._log_error(error_info)
        
        # Verificar si necesita alerta
        self._check_alert_threshold(error_info)
        
        # Notificar callbacks registrados
        self._notify_callbacks(error_info)
        
        # Retornar mensaje amigable
        return self._create_user_friendly_error(error_info, user_context)
    
    def _categorize_error(self, error: Exception) -> str:
        """Categoriza el error basado en su mensaje"""
        error_str = str(error).lower()
        
        for category, info in self.ERROR_CATEGORIES.items():
            if any(keyword in error_str for keyword in info['keywords']):
                return category
        
        # Categoría por defecto basada en tipo de excepción
        error_type = type(error).__name__
        if 'Database' in error_type or 'SQL' in error_type:
            return 'database'
        elif 'HTTP' in error_type or 'API' in error_type:
            return 'api'
        elif 'IO' in error_type or 'File' in error_type:
            return 'file'
        elif 'Value' in error_type or 'Type' in error_type:
            return 'validation'
        else:
            return 'unknown'
    
    def _log_error(self, error_info: Dict):
        """Log estructurado del error"""
        # Agregar al log en memoria
        self.error_log.append(error_info)
        
        # Limitar tamaño del log
        if len(self.error_log) > self.max_log_size:
            self.error_log = self.error_log[-self.max_log_size:]
        
        # Log según severidad
        log_msg = f"Error {error_info['id']} [{error_info['category']}]: {error_info['type']} - {error_info['message']}"
        
        if error_info['severity'] == 'high':
            logger.error(log_msg)
            if error_info.get('context'):
                logger.error(f"Contexto: {error_info['context']}")
        elif error_info['severity'] == 'medium':
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Log detallado en debug
        logger.debug(f"Traceback completo: {error_info['traceback']}")
    
    def _check_alert_threshold(self, error_info: Dict):
        """Verifica si se debe enviar alerta por errores repetidos"""
        # Contar errores similares en las últimas 2 horas
        cutoff_time = datetime.now() - timedelta(hours=2)
        
        similar_errors = [
            e for e in self.error_log
            if e['category'] == error_info['category'] and
            datetime.fromisoformat(e['timestamp']) > cutoff_time
        ]
        
        if len(similar_errors) >= self.alert_threshold:
            self._send_alert(similar_errors, error_info['category'])
    
    def _send_alert(self, errors: List[Dict], category: str):
        """Envía alerta de errores repetidos"""
        alert_msg = (
            f"⚠️ **ALERTA DE ERRORES REPETIDOS**\n"
            f"• Categoría: {category}\n"
            f"• Cantidad: {len(errors)} en 2 horas\n"
            f"• Último error: {errors[-1]['message'][:100]}"
        )
        
        logger.warning(alert_msg)
        
        # Aquí se integraría con el sistema de notificaciones existente
        # Por ahora solo log
        
        # Marcar errores como alertados
        for error in errors[-self.alert_threshold:]:
            error['alerted'] = True
    
    def _notify_callbacks(self, error_info: Dict):
        """Notifica a callbacks registrados"""
        for callback in self._notification_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error en callback de notificación: {e}")
    
    def _create_user_friendly_error(self, error_info: Dict, user_context: Optional[str]) -> str:
        """Crea mensaje de error amigable para el usuario"""
        # Usar contexto proporcionado por el usuario si existe
        if user_context:
            return user_context
        
        # Usar mensaje predeterminado por categoría
        category_info = self.ERROR_CATEGORIES.get(error_info['category'], {})
        default_message = category_info.get('user_message', "⚠️ Ocurrió un error inesperado. Por favor, intente nuevamente.")
        
        # Personalizar según tipo de error común
        error_msg = error_info['message'].lower()
        
        if 'timeout' in error_msg:
            return "⏱️ La operación tardó demasiado tiempo. Intente nuevamente."
        elif 'connection' in error_msg:
            return "🔌 Error de conexión. Verifique su internet y reintente."
        elif 'permission' in error_msg:
            return "🔐 No tiene permisos para realizar esta acción."
        elif 'not found' in error_msg:
            return "🔍 El recurso solicitado no fue encontrado."
        
        return default_message
    
    def register_notification_callback(self, callback: Callable):
        """Registra un callback para notificaciones de errores"""
        self._notification_callbacks.append(callback)
    
    def get_error_report(self, hours: int = 24, category: Optional[str] = None) -> pd.DataFrame:
        """
        Genera reporte de errores
        
        Args:
            hours: Horas hacia atrás para filtrar
            category: Filtrar por categoría específica
        
        Returns:
            DataFrame con errores
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        filtered_errors = [
            e for e in self.error_log
            if datetime.fromisoformat(e['timestamp']) > cutoff
        ]
        
        if category:
            filtered_errors = [e for e in filtered_errors if e['category'] == category]
        
        if not filtered_errors:
            return pd.DataFrame()
        
        # Convertir a DataFrame
        df = pd.DataFrame(filtered_errors)
        
        # Limpiar columnas para visualización
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hora'] = df['timestamp'].dt.strftime('%H:%M')
            df['fecha'] = df['timestamp'].dt.strftime('%Y-%m-%d')
        
        # Ordenar por fecha descendente
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
        
        return df
    
    def get_stats(self, hours: int = 24) -> Dict:
        """Obtiene estadísticas de errores"""
        df = self.get_error_report(hours)
        
        if df.empty:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_severity': {},
                'error_rate': '0.0%'
            }
        
        total = len(df)
        by_category = df['category'].value_counts().to_dict() if 'category' in df.columns else {}
        by_severity = df['severity'].value_counts().to_dict() if 'severity' in df.columns else {}
        
        # Calcular tasa de error (errores por hora)
        if hours > 0:
            error_rate = (total / hours)
        else:
            error_rate = 0
        
        return {
            'total_errors': total,
            'by_category': by_category,
            'by_severity': by_severity,
            'error_rate': f"{error_rate:.1f} errores/hora",
            'time_period': f"{hours} horas"
        }
    
    def mark_resolved(self, error_id: str, resolution_notes: str = ""):
        """Marca un error como resuelto"""
        for error in self.error_log:
            if error['id'] == error_id:
                error['resolved'] = True
                error['resolved_at'] = datetime.now().isoformat()
                error['resolution_notes'] = resolution_notes
                logger.info(f"Error {error_id} marcado como resuelto")
                return True
        return False
    
    def clear_old_errors(self, days: int = 7):
        """Limpia errores antiguos"""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.error_log)
        
        self.error_log = [
            e for e in self.error_log
            if datetime.fromisoformat(e['timestamp']) > cutoff
        ]
        
        cleared_count = original_count - len(self.error_log)
        if cleared_count > 0:
            logger.info(f"Limpiados {cleared_count} errores con más de {days} días")
    
    def export_to_csv(self, filepath: str, hours: int = 24):
        """Exporta errores a CSV"""
        try:
            df = self.get_error_report(hours)
            if not df.empty:
                df.to_csv(filepath, index=False, encoding='utf-8')
                logger.info(f"Errores exportados a {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error exportando a CSV: {e}")
            return False

# Singleton global
_error_handler_instance = None

def get_error_handler() -> ErrorHandler:
    """Obtiene la instancia singleton de ErrorHandler"""
    global _error_handler_instance
    if _error_handler_instance is None:
        _error_handler_instance = ErrorHandler()
    return _error_handler_instance

# Decorador para manejo automático de errores
def error_handler_decorator(user_context: Optional[str] = None):
    """
    Decorador para manejo automático de errores en funciones
    
    Ejemplo:
        @error_handler_decorator("Error procesando archivo")
        def procesar_archivo(ruta):
            # código que puede fallar
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                error_msg = handler.handle(e, 
                                         context={'function': func.__name__,
                                                  'args': str(args),
                                                  'kwargs': str(kwargs)},
                                         user_context=user_context)
                # Re-lanzar la excepción original si es crítico
                if handler._categorize_error(e) == 'database':
                    raise
                return None
        return wrapper
    return decorator

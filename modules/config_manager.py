
# modules/config_manager.py
"""
Gestor centralizado de configuraciones para el sistema Aeropostale.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Configurar logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestor centralizado de configuraciones"""
    
    # Configuraciones por defecto
    DEFAULT_CONFIG = {
        'database': {
            'url': "https://nsgdyqoqzlcyyameccqn.supabase.co",
            'key': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5zZ2R5cW9xemxjeXlhbWVjY3FuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwMTA3MzksImV4cCI6MjA3MTU4NjczOX0.jA6sem9IMts6aPeYlMsldbtQaEaKAuQaQ1xf03TdWso",
            'timeout': 30,
            'retry_attempts': 3
        },
        'security': {
            'admin_password': "Wilo3161",
            'user_password': "User1234",
            'session_timeout': 3600,
            'password_hash_algorithm': 'sha256'
        },
        'apis': {
            'gemini': {
                'model': 'gemini-1.5-flash',
                'temperature': 0.1,
                'max_tokens': 2000
            },
            'whatsapp': {
                'enabled': False,
                'provider': 'twilio',
                'webhook_url': ''
            }
        },
        'paths': {
            'data_dir': 'data_wilo',
            'images_dir': 'images',
            'backup_dir': 'backups',
            'logs_dir': 'logs'
        },
        'email': {
            'imap_server': 'mail.fashionclub.com.ec',
            'imap_port': 993,
            'smtp_server': 'smtp.fashionclub.com.ec',
            'smtp_port': 587
        },
        'features': {
            'wilo_ai_enabled': True,
            'auto_backup': True,
            'real_time_alerts': True,
            'email_scanning': False
        },
        'ui': {
            'theme': 'dark',
            'language': 'es',
            'refresh_interval': 300
        }
    }
    
    def __init__(self, config_file: str = 'config.json'):
        """Inicializa el gestor de configuraciones"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_file = Path(config_file)
        self._loaded_from_env = False
        self._loaded_from_file = False
        
        # Cargar configuraciones en orden de prioridad
        self._load_all_configs()
        
        # Crear directorios necesarios
        self._create_directories()
        
        logger.info("✅ ConfigManager inicializado")
    
    def _load_all_configs(self):
        """Carga configuraciones desde múltiples fuentes en orden"""
        
        # 1. Variables de entorno (máxima prioridad)
        self._load_from_env()
        
        # 2. Archivo de configuración
        self._load_from_file()
        
        # 3. Configuración por defecto (ya cargada)
    
    def _load_from_env(self):
        """Carga configuraciones desde variables de entorno"""
        try:
            load_dotenv()  # Cargar .env si existe
            
            # Database
            if db_url := os.getenv('SUPABASE_URL'):
                self.config['database']['url'] = db_url
            if db_key := os.getenv('SUPABASE_KEY'):
                self.config['database']['key'] = db_key
            
            # Security
            if admin_pw := os.getenv('ADMIN_PASSWORD'):
                self.config['security']['admin_password'] = admin_pw
            if user_pw := os.getenv('USER_PASSWORD'):
                self.config['security']['user_password'] = user_pw
            
            # APIs
            if gemini_key := os.getenv('GEMINI_API_KEY'):
                self.config['apis']['gemini']['api_key'] = gemini_key
            
            # Email
            if email_user := os.getenv('EMAIL_USER'):
                self.config['email']['username'] = email_user
            if email_pass := os.getenv('EMAIL_PASSWORD'):
                self.config['email']['password'] = email_pass
            
            self._loaded_from_env = True
            logger.debug("Configuraciones cargadas desde variables de entorno")
            
        except Exception as e:
            logger.warning(f"No se pudieron cargar configuraciones de entorno: {e}")
    
    def _load_from_file(self):
        """Carga configuraciones desde archivo JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                self._merge_config(file_config)
                self._loaded_from_file = True
                logger.debug(f"Configuraciones cargadas desde {self.config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Error de formato en archivo de configuración: {e}")
            self._backup_corrupt_config()
        except Exception as e:
            logger.error(f"Error al cargar archivo de configuración: {e}")
    
    def _merge_config(self, new_config: Dict):
        """Fusión recursiva de diccionarios de configuración"""
        def merge_dict(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dict(target[key], value)
                else:
                    target[key] = value
        
        merge_dict(self.config, new_config)
    
    def _backup_corrupt_config(self):
        """Realiza backup de archivo de configuración corrupto"""
        try:
            backup_name = f"{self.config_file}.corrupt.{int(os.path.getmtime(self.config_file))}"
            self.config_file.rename(backup_name)
            logger.warning(f"Archivo de configuración corrupto respaldado como {backup_name}")
        except Exception as e:
            logger.error(f"No se pudo respaldar archivo corrupto: {e}")
    
    def _create_directories(self):
        """Crea directorios necesarios si no existen"""
        directories = [
            self.get('paths.data_dir'),
            self.get('paths.images_dir'),
            self.get('paths.backup_dir'),
            self.get('paths.logs_dir')
        ]
        
        for directory in directories:
            if directory:
                try:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Directorio verificado/creado: {directory}")
                except Exception as e:
                    logger.error(f"Error al crear directorio {directory}: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene configuración por path (ej: 'database.url')
        
        Args:
            key_path: Ruta de la configuración (ej: 'database.url')
            default: Valor por defecto si no se encuentra
        
        Returns:
            Valor de la configuración o default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, {})
                else:
                    return default
            
            # Si el valor final es un diccionario vacío, retornar default
            if value == {}:
                return default
            
            return value
            
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error al acceder a {key_path}: {e}")
            return default
    
    def set(self, key_path: str, value: Any, persist: bool = False):
        """
        Establece una configuración
        
        Args:
            key_path: Ruta de la configuración
            value: Valor a establecer
            persist: Si es True, guarda en archivo
        """
        keys = key_path.split('.')
        config_level = self.config
        
        # Navegar hasta el penúltimo nivel
        for key in keys[:-1]:
            if key not in config_level or not isinstance(config_level[key], dict):
                config_level[key] = {}
            config_level = config_level[key]
        
        # Establecer valor
        config_level[keys[-1]] = value
        
        # Persistir si se solicita
        if persist:
            self.save()
    
    def save(self):
        """Guarda la configuración actual en archivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuración guardada en {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False
    
    def reload(self):
        """Recarga configuraciones desde todas las fuentes"""
        old_config = self.config.copy()
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_all_configs()
        
        # Verificar si hubo cambios
        if old_config != self.config:
            logger.info("Configuración recargada con cambios")
            return True
        return False
    
    def get_all(self) -> Dict:
        """Obtiene toda la configuración (copia)"""
        import copy
        return copy.deepcopy(self.config)
    
    def validate(self) -> Dict[str, list]:
        """
        Valida configuraciones críticas
        
        Returns:
            Dict con errores y advertencias
        """
        errors = []
        warnings = []
        
        # Validar base de datos
        if not self.get('database.url'):
            errors.append("URL de base de datos no configurada")
        if not self.get('database.key'):
            errors.append("API Key de base de datos no configurada")
        
        # Validar rutas
        for path_key in ['data_dir', 'images_dir']:
            path = self.get(f'paths.{path_key}')
            if path and not Path(path).exists():
                warnings.append(f"Directorio {path_key} no existe: {path}")
        
        # Validar passwords por defecto
        if self.get('security.admin_password') == 'Wilo3161':
            warnings.append("Password de administrador usando valor por defecto")
        if self.get('security.user_password') == 'User1234':
            warnings.append("Password de usuario usando valor por defecto")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
    
    def print_summary(self):
        """Imprime resumen de configuración (para debug)"""
        summary = {
            'Fuentes cargadas': {
                'Entorno': self._loaded_from_env,
                'Archivo': self._loaded_from_file,
                'Default': True
            },
            'Base de datos': {
                'URL': '✓' if self.get('database.url') else '✗',
                'API Key': '✓' if self.get('database.key') else '✗'
            },
            'Seguridad': {
                'Admin Password': '✓' if self.get('security.admin_password') else '✗',
                'Session Timeout': self.get('security.session_timeout')
            },
            'Características': {
                'WILO AI': 'Habilitado' if self.get('features.wilo_ai_enabled') else 'Deshabilitado',
                'Auto Backup': 'Habilitado' if self.get('features.auto_backup') else 'Deshabilitado'
            }
        }
        
        import pprint
        logger.info("Resumen de configuración:\n" + pprint.pformat(summary, indent=2))

# Singleton global
_config_instance = None

def get_config() -> ConfigManager:
    """Obtiene la instancia singleton de ConfigManager"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance

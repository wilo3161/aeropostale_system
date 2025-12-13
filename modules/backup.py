# modules/backup.py
"""
Sistema de backup automático para el sistema Aeropostale.
"""

import logging
import shutil
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from modules.config_manager import get_config
from modules.error_handler import get_error_handler
from modules.database import get_database

logger = logging.getLogger(__name__)

class BackupSystem:
    """Sistema de backup automático"""
    
    def __init__(self, backup_dir: Optional[str] = None):
        config = get_config()
        self.backup_dir = Path(backup_dir or config.get('paths.backup_dir', 'backups'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = 7
        self.max_backups = 10
        self.compression_level = 9
        self.error_handler = get_error_handler()
        
        # Configuración de backup
        self.backup_config = {
            'include_database': True,
            'include_configs': True,
            'include_logs': True,
            'include_wilo_data': True,
            'include_images': False,  # Las imágenes pueden ser grandes
            'max_backup_size_mb': 500
        }
    
    def create_backup(self, backup_type: str = "full", description: str = "") -> Optional[Path]:
        """
        Crea un backup del sistema
        
        Args:
            backup_type: 'full', 'incremental', 'database_only'
            description: Descripción opcional del backup
        
        Returns:
            Ruta al archivo de backup creado o None si falla
        """
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{backup_type}_{backup_id}"
        
        if description:
            backup_name += f"_{description[:50].replace(' ', '_')}"
        
        temp_dir = self.backup_dir / "temp" / backup_name
        backup_file = self.backup_dir / f"{backup_name}.zip"
        
        try:
            # Crear directorio temporal
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear metadata del backup
            metadata = self._create_metadata(backup_type, description)
            
            # Realizar backup según tipo
            if backup_type == "full":
                self._full_backup(temp_dir, metadata)
            elif backup_type == "database_only":
                self._database_backup(temp_dir, metadata)
            elif backup_type == "incremental":
                self._incremental_backup(temp_dir, metadata)
            else:
                raise ValueError(f"Tipo de backup no soportado: {backup_type}")
            
            # Comprimir backup
            self._compress_backup(temp_dir, backup_file)
            
            # Verificar tamaño
            if backup_file.stat().st_size > self.backup_config['max_backup_size_mb'] * 1024 * 1024:
                logger.warning(f"Backup muy grande: {backup_file.stat().st_size / (1024*1024):.1f} MB")
            
            # Limpiar directorio temporal
            shutil.rmtree(temp_dir)
            
            # Limpiar backups antiguos
            self._clean_old_backups()
            
            logger.info(f"✅ Backup creado: {backup_file.name} ({backup_file.stat().st_size / 1024:.0f} KB)")
            return backup_file
            
        except Exception as e:
            self.error_handler.handle(e, user_context="❌ Error creando backup")
            
            # Limpiar en caso de error
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if backup_file.exists():
                backup_file.unlink(missing_ok=True)
            
            return None
    
    def _create_metadata(self, backup_type: str, description: str) -> Dict[str, Any]:
        """Crea metadata del backup"""
        config = get_config()
        
        return {
            'backup_id': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'timestamp': datetime.now().isoformat(),
            'type': backup_type,
            'description': description,
            'system_info': {
                'version': '2.0',
                'config_source': 'env' if config._loaded_from_env else 'file',
                'features_enabled': config.get('features', {})
            },
            'contents': [],
            'size_bytes': 0
        }
    
    def _full_backup(self, temp_dir: Path, metadata: Dict):
        """Realiza un backup completo"""
        config = get_config()
        
        # 1. Backup de base de datos
        if self.backup_config['include_database']:
            self._backup_database(temp_dir, metadata)
        
        # 2. Backup de configuraciones
        if self.backup_config['include_configs']:
            self._backup_configs(temp_dir, metadata)
        
        # 3. Backup de datos WILO
        if self.backup_config['include_wilo_data']:
            self._backup_wilo_data(temp_dir, metadata)
        
        # 4. Backup de logs
        if self.backup_config['include_logs']:
            self._backup_logs(temp_dir, metadata)
        
        # 5. Backup de imágenes (opcional)
        if self.backup_config['include_images']:
            self._backup_images(temp_dir, metadata)
    
    def _database_backup(self, temp_dir: Path, metadata: Dict):
        """Backup solo de base de datos"""
        self._backup_database(temp_dir, metadata)
    
    def _incremental_backup(self, temp_dir: Path, metadata: Dict):
        """Backup incremental (desde el último backup)"""
        # En una implementación real, se compararía con el último backup
        # Por ahora hacemos un backup completo pero marcado como incremental
        self._full_backup(temp_dir, metadata)
        metadata['type'] = 'incremental'
    
    def _backup_database(self, temp_dir: Path, metadata: Dict):
        """Backup de datos de Supabase"""
        try:
            db = get_database()
            data_dir = temp_dir / "database"
            data_dir.mkdir(exist_ok=True)
            
            # Tablas a respaldar
            tables = [
                'daily_kpis', 'trabajadores', 'guide_stores',
                'guide_senders', 'guide_logs', 'distribuciones_semanales'
            ]
            
            for table in tables:
                try:
                    # Obtener todos los datos de la tabla
                    # Nota: En producción, se debería paginar para tablas grandes
                    data = db.orm.execute(
                        'select',
                        table,
                        limit=10000  # Límite para backup
                    )
                    
                    if data:
                        # Guardar como JSON
                        table_file = data_dir / f"{table}.json"
                        with open(table_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        
                        metadata['contents'].append({
                            'type': 'database',
                            'table': table,
                            'rows': len(data),
                            'file': table_file.name
                        })
                        
                        logger.debug(f"  ✓ Tabla {table}: {len(data)} registros")
                    
                except Exception as e:
                    logger.warning(f"  ✗ Error respaldando tabla {table}: {e}")
                    continue
            
            # Guardar schema información
            schema_info = {
                'tables': tables,
                'backup_timestamp': datetime.now().isoformat(),
                'row_counts': {table: len(data) for table in tables if 'data' in locals()}
            }
            
            schema_file = data_dir / "schema_info.json"
            with open(schema_file, 'w', encoding='utf-8') as f:
                json.dump(schema_info, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error en backup de base de datos: {e}")
    
    def _backup_configs(self, temp_dir: Path, metadata: Dict):
        """Backup de archivos de configuración"""
        config_dir = temp_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        config_files = [
            Path('config.json'),
            Path('.env'),
            Path('data_wilo/email_config.json'),
            Path('data_wilo/gemini_config.json'),
            Path('data_wilo/novedades_database.json')
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    shutil.copy2(config_file, config_dir / config_file.name)
                    
                    metadata['contents'].append({
                        'type': 'config',
                        'file': config_file.name,
                        'size': config_file.stat().st_size
                    })
                    
                    logger.debug(f"  ✓ Config: {config_file.name}")
                    
                except Exception as e:
                    logger.warning(f"  ✗ Error copiando {config_file}: {e}")
    
    def _backup_wilo_data(self, temp_dir: Path, metadata: Dict):
        """Backup de datos de WILO AI"""
        wilo_dir = Path('data_wilo')
        if wilo_dir.exists():
            backup_wilo_dir = temp_dir / "wilo_data"
            shutil.copytree(wilo_dir, backup_wilo_dir, dirs_exist_ok=True)
            
            # Contar archivos
            file_count = sum(1 for _ in wilo_dir.rglob('*') if _.is_file())
            
            metadata['contents'].append({
                'type': 'wilo_data',
                'directory': 'data_wilo',
                'file_count': file_count
            })
            
            logger.debug(f"  ✓ WILO data: {file_count} archivos")
    
    def _backup_logs(self, temp_dir: Path, metadata: Dict):
        """Backup de archivos de log"""
        log_dir = Path('logs')
        if log_dir.exists():
            backup_log_dir = temp_dir / "logs"
            backup_log_dir.mkdir(exist_ok=True)
            
            # Copiar logs de los últimos 7 días
            cutoff_date = datetime.now() - timedelta(days=7)
            log_files = list(log_dir.glob("*.log"))
            
            copied_count = 0
            for log_file in log_files:
                if log_file.stat().st_mtime > cutoff_date.timestamp():
                    try:
                        shutil.copy2(log_file, backup_log_dir / log_file.name)
                        copied_count += 1
                    except Exception as e:
                        logger.warning(f"  ✗ Error copiando log {log_file}: {e}")
            
            metadata['contents'].append({
                'type': 'logs',
                'directory': 'logs',
                'files_copied': copied_count,
                'days': 7
            })
            
            logger.debug(f"  ✓ Logs: {copied_count} archivos (últimos 7 días)")
    
    def _backup_images(self, temp_dir: Path, metadata: Dict):
        """Backup de imágenes (opcional)"""
        images_dir = Path('images')
        if images_dir.exists():
            # Solo respaldar imágenes de logos, no todas
            logo_files = list(images_dir.glob("*logo*")) + list(images_dir.glob("*brand*"))
            
            if logo_files:
                backup_images_dir = temp_dir / "images"
                backup_images_dir.mkdir(exist_ok=True)
                
                for img_file in logo_files:
                    try:
                        shutil.copy2(img_file, backup_images_dir / img_file.name)
                    except Exception as e:
                        logger.warning(f"  ✗ Error copiando imagen {img_file}: {e}")
                
                metadata['contents'].append({
                    'type': 'images',
                    'directory': 'images',
                    'files_copied': len(logo_files)
                })
                
                logger.debug(f"  ✓ Imágenes: {len(logo_files)} archivos")
    
    def _compress_backup(self, source_dir: Path, dest_file: Path):
        """Comprime el directorio de backup"""
        with zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=self.compression_level) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        # Actualizar metadata con tamaño
        metadata_file = source_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata['size_bytes'] = dest_file.stat().st_size
            metadata['compressed'] = True
            
            # Agregar metadata al zip
            with zipfile.ZipFile(dest_file, 'a') as zipf:
                zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
    
    def _clean_old_backups(self):
        """Limpia backups antiguos"""
        try:
            backup_files = list(self.backup_dir.glob("backup_*.zip"))
            
            if len(backup_files) <= self.max_backups:
                return
            
            # Ordenar por fecha de modificación (más antiguos primero)
            backup_files.sort(key=lambda x: x.stat().st_mtime)
            
            # Eliminar los más antiguos
            files_to_delete = backup_files[:len(backup_files) - self.max_backups]
            
            for backup_file in files_to_delete:
                try:
                    backup_file.unlink()
                    logger.info(f"🗑️ Eliminado backup antiguo: {backup_file.name}")
                except Exception as e:
                    logger.error(f"Error eliminando backup {backup_file}: {e}")
            
        except Exception as e:
            logger.error(f"Error limpiando backups antiguos: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Lista todos los backups disponibles"""
        backups = []
        
        try:
            backup_files = list(self.backup_dir.glob("backup_*.zip"))
            
            for backup_file in backup_files:
                try:
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        if 'metadata.json' in zipf.namelist():
                            with zipf.open('metadata.json') as f:
                                metadata = json.load(f)
                            
                            backups.append({
                                'filename': backup_file.name,
                                'path': backup_file,
                                'size_mb': backup_file.stat().st_size / (1024 * 1024),
                                'created': metadata.get('timestamp'),
                                'type': metadata.get('type', 'unknown'),
                                'description': metadata.get('description', ''),
                                'contents': metadata.get('contents', [])
                            })
                        else:
                            # Backup sin metadata
                            backups.append({
                                'filename': backup_file.name,
                                'path': backup_file,
                                'size_mb': backup_file.stat().st_size / (1024 * 1024),
                                'created': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                                'type': 'unknown',
                                'description': 'Sin metadata',
                                'contents': []
                            })
                            
                except Exception as e:
                    logger.warning(f"Error leyendo metadata de {backup_file}: {e}")
        
        except Exception as e:
            self.error_handler.handle(e, user_context="Error listando backups")
        
        # Ordenar por fecha (más recientes primero)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    def restore_backup(self, backup_file: Path, restore_type: str = "full") -> bool:
        """
        Restaura un backup
        
        Args:
            backup_file: Archivo de backup a restaurar
            restore_type: 'full', 'database_only', 'configs_only'
        
        Returns:
            True si la restauración fue exitosa
        """
        temp_dir = self.backup_dir / "restore_temp"
        
        try:
            # Extraer backup
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Leer metadata
            metadata_file = temp_dir / "metadata.json"
            if not metadata_file.exists():
                logger.error("Backup no contiene metadata")
                return False
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"Iniciando restauración desde {backup_file.name}")
            logger.info(f"Tipo: {metadata.get('type')}, Descripción: {metadata.get('description')}")
            
            # Restaurar según tipo
            if restore_type == "full" or restore_type == "database_only":
                self._restore_database(temp_dir)
            
            if restore_type == "full" or restore_type == "configs_only":
                self._restore_configs(temp_dir)
            
            # Limpiar directorio temporal
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info("✅ Restauración completada exitosamente")
            return True
            
        except Exception as e:
            self.error_handler.handle(e, user_context="❌ Error restaurando backup")
            
            # Limpiar en caso de error
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            return False
    
    def _restore_database(self, temp_dir: Path):
        """Restaura base de datos desde backup"""
        db_dir = temp_dir / "database"
        if not db_dir.exists():
            logger.warning("No hay datos de base de datos en el backup")
            return
        
        db = get_database()
        
        # Restaurar cada tabla
        for table_file in db_dir.glob("*.json"):
            if table_file.name == "schema_info.json":
                continue
            
            table_name = table_file.stem
            logger.info(f"Restaurando tabla: {table_name}")
            
            try:
                with open(table_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data:
                    # Usar bulk upsert para restaurar
                    success = db.orm.bulk_upsert(table_name, data, batch_size=100)
                    if success:
                        logger.info(f"  ✓ {table_name}: {len(data)} registros restaurados")
                    else:
                        logger.warning(f"  ✗ {table_name}: Error en restauración")
                
            except Exception as e:
                logger.error(f"Error restaurando tabla {table_name}: {e}")
    
    def _restore_configs(self, temp_dir: Path):
        """Restaura configuraciones desde backup"""
        config_dir = temp_dir / "config"
        if not config_dir.exists():
            logger.warning("No hay configuraciones en el backup")
            return
        
        # Restaurar cada archivo de configuración
        for config_file in config_dir.glob("*"):
            try:
                shutil.copy2(config_file, Path(config_file.name))
                logger.info(f"  ✓ Config: {config_file.name} restaurado")
            except Exception as e:
                logger.warning(f"  ✗ Error restaurando {config_file}: {e}")
    
    def schedule_backup(self, hour: int = 2, backup_type: str = "full"):
        """Programa backup automático diario"""
        def backup_job():
            logger.info(f"📅 Backup programado para las {hour:02d}:00 (tipo: {backup_type})")
            
            while True:
                now = datetime.now()
                
                # Ejecutar a la hora programada
                if now.hour == hour and now.minute == 0:
                    try:
                        description = f"backup_automatico_{now.strftime('%Y%m%d')}"
                        backup_file = self.create_backup(backup_type, description)
                        
                        if backup_file:
                            logger.info(f"✅ Backup automático completado: {backup_file.name}")
                        else:
                            logger.error("❌ Falló backup automático")
                        
                        # Esperar 61 minutos para evitar múltiples ejecuciones
                        time.sleep(3660)
                        
                    except Exception as e:
                        self.error_handler.handle(e, user_context="Error en backup automático")
                        time.sleep(300)  # Esperar 5 minutos en caso de error
                
                time.sleep(30)  # Verificar cada 30 segundos
        
        thread = threading.Thread(target=backup_job, daemon=True)
        thread.start()
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de backups"""
        backups = self.list_backups()
        
        if not backups:
            return {
                'total_backups': 0,
                'total_size_gb': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'by_type': {}
            }
        
        total_size = sum(b['size_mb'] for b in backups)
        
        # Agrupar por tipo
        by_type = {}
        for backup in backups:
            backup_type = backup.get('type', 'unknown')
            if backup_type not in by_type:
                by_type[backup_type] = {
                    'count': 0,
                    'total_size_mb': 0
                }
            by_type[backup_type]['count'] += 1
            by_type[backup_type]['total_size_mb'] += backup['size_mb']
        
        return {
            'total_backups': len(backups),
            'total_size_gb': total_size / 1024,
            'oldest_backup': backups[-1]['created'] if backups else None,
            'newest_backup': backups[0]['created'] if backups else None,
            'by_type': by_type,
            'retention_days': self.retention_days,
            'max_backups': self.max_backups
        }


# Singleton global
_backup_system = None

def get_backup_system() -> BackupSystem:
    """Obtiene la instancia singleton de BackupSystem"""
    global _backup_system
    if _backup_system is None:
        _backup_system = BackupSystem()
    return _backup_system

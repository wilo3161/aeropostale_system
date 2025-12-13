# modules/health_monitor.py
"""
Sistema de monitoreo de salud para el sistema Aeropostale.
"""

import time
import threading
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitor de salud del sistema"""
    
    def __init__(self):
        self.checks: List[Dict] = []
        self.metrics_history: Dict[str, List] = {
            'response_times': [],
            'memory_usage': [],
            'database_latency': [],
            'api_latency': [],
            'disk_usage': []
        }
        self.status_history: List[Dict] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 60  # Segundos entre checks
        self.max_history_size = 1000
        
        # Registrar checks por defecto
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Registra los checks de salud por defecto"""
        self.register_check('database', self.check_database, interval=30, critical=True)
        self.register_check('storage', self.check_storage, interval=300)
        self.register_check('apis', self.check_apis, interval=300)
        self.register_check('memory', self.check_memory, interval=60)
        self.register_check('disk', self.check_disk, interval=300)
    
    def register_check(self, name: str, check_func: Callable, 
                      interval: int = 60, critical: bool = False):
        """
        Registra un check de salud
        
        Args:
            name: Nombre identificador del check
            check_func: Función que ejecuta el check
            interval: Intervalo en segundos entre ejecuciones
            critical: Si es True, el sistema se considera no saludable si falla
        """
        self.checks.append({
            'name': name,
            'function': check_func,
            'interval': interval,
            'critical': critical,
            'last_run': None,
            'last_status': 'unknown',
            'last_error': None,
            'response_time': None,
            'next_run': datetime.now()
        })
        
        logger.debug(f"Check registrado: {name} (intervalo: {interval}s, crítico: {critical})")
    
    def unregister_check(self, name: str):
        """Elimina un check registrado"""
        self.checks = [c for c in self.checks if c['name'] != name]
        logger.debug(f"Check eliminado: {name}")
    
    def run_check(self, check_name: str) -> Dict[str, Any]:
        """Ejecuta un check específico"""
        for check in self.checks:
            if check['name'] == check_name:
                return self._execute_check(check)
        
        raise ValueError(f"Check no encontrado: {check_name}")
    
    def run_checks(self, only_critical: bool = False) -> Dict[str, Dict]:
        """Ejecuta todos los checks registrados"""
        results = {}
        
        for check in self.checks:
            if only_critical and not check['critical']:
                continue
            
            # Verificar si es hora de ejecutar este check
            if check['next_run'] and datetime.now() < check['next_run']:
                continue
            
            result = self._execute_check(check)
            results[check['name']] = result
            
            # Programar siguiente ejecución
            check['next_run'] = datetime.now() + timedelta(seconds=check['interval'])
        
        return results
    
    def _execute_check(self, check: Dict) -> Dict[str, Any]:
        """Ejecuta un check individual"""
        check_name = check['name']
        start_time = time.time()
        
        try:
            # Ejecutar función de check
            check['function']()
            elapsed = time.time() - start_time
            
            # Actualizar estado del check
            check['last_run'] = datetime.now()
            check['last_status'] = 'healthy'
            check['last_error'] = None
            check['response_time'] = elapsed
            
            # Registrar métrica
            self._record_metric(f"{check_name}_response_time", elapsed)
            
            logger.debug(f"Check {check_name}: HEALTHY ({elapsed:.2f}s)")
            
            return {
                'status': 'healthy',
                'response_time': elapsed,
                'timestamp': datetime.now().isoformat(),
                'message': f"{check_name} funcionando correctamente"
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            
            # Actualizar estado del check
            check['last_run'] = datetime.now()
            check['last_status'] = 'unhealthy'
            check['last_error'] = str(e)
            check['response_time'] = elapsed
            
            logger.warning(f"Check {check_name}: UNHEALTHY - {str(e)[:100]}")
            
            return {
                'status': 'unhealthy',
                'response_time': elapsed,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'message': f"Error en {check_name}: {str(e)[:100]}"
            }
    
    def check_database(self):
        """Check de conexión a base de datos"""
        from supabase import create_client
        from modules.config_manager import get_config
        
        config = get_config()
        supabase_url = config.get('database.url')
        supabase_key = config.get('database.key')
        
        if not supabase_url or not supabase_key:
            raise Exception("Configuración de base de datos faltante")
        
        # Intentar conexión
        client = create_client(supabase_url, supabase_key)
        
        # Query simple para verificar conexión
        response = client.from_('daily_kpis').select('count', count='exact').limit(1).execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error en base de datos: {response.error}")
    
    def check_storage(self):
        """Check de almacenamiento"""
        from modules.config_manager import get_config
        
        config = get_config()
        required_dirs = [
            config.get('paths.data_dir'),
            config.get('paths.images_dir'),
            config.get('paths.backup_dir'),
            config.get('paths.logs_dir')
        ]
        
        for dir_path in required_dirs:
            if dir_path:
                path = Path(dir_path)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                
                # Verificar permisos de escritura
                test_file = path / 'health_check.tmp'
                try:
                    test_file.write_text(str(datetime.now()))
                    test_file.unlink()
                except Exception as e:
                    raise Exception(f"Sin permisos en {dir_path}: {e}")
    
    def check_apis(self):
        """Check de APIs externas"""
        from modules.config_manager import get_config
        import google.generativeai as genai
        
        config = get_config()
        api_key = config.get('apis.gemini.api_key')
        
        if api_key:
            genai.configure(api_key=api_key)
            
            try:
                # Intento simple de conexión
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Hello")
                if not response.text:
                    raise Exception("Respuesta vacía de Gemini API")
            except Exception as e:
                raise Exception(f"Error en Gemini API: {e}")
    
    def check_memory(self):
        """Check de uso de memoria"""
        memory = psutil.virtual_memory()
        
        # Registrar métrica
        self._record_metric('memory_percent', memory.percent)
        
        # Alertar si uso de memoria es muy alto
        if memory.percent > 90:
            raise Exception(f"Uso de memoria muy alto: {memory.percent}%")
        elif memory.percent > 80:
            logger.warning(f"Uso de memoria elevado: {memory.percent}%")
    
    def check_disk(self):
        """Check de uso de disco"""
        disk = psutil.disk_usage('/')
        
        # Registrar métrica
        self._record_metric('disk_percent', disk.percent)
        
        # Alertar si uso de disco es muy alto
        if disk.percent > 95:
            raise Exception(f"Uso de disco muy alto: {disk.percent}%")
        elif disk.percent > 85:
            logger.warning(f"Uso de disco elevado: {disk.percent}%")
    
    def _record_metric(self, name: str, value: float):
        """Registra una métrica en el historial"""
        if name not in self.metrics_history:
            self.metrics_history[name] = []
        
        self.metrics_history[name].append({
            'timestamp': datetime.now(),
            'value': value
        })
        
        # Limitar tamaño del historial
        if len(self.metrics_history[name]) > self.max_history_size:
            self.metrics_history[name] = self.metrics_history[name][-self.max_history_size:]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Obtiene estado de salud completo del sistema"""
        checks_results = self.run_checks()
        
        # Calcular salud general
        critical_checks = [c for c in checks_results.values() if c['status'] == 'unhealthy']
        all_critical_healthy = all(
            check['last_status'] == 'healthy' 
            for check in self.checks 
            if check['critical']
        )
        
        health_percentage = self._calculate_health_percentage(checks_results)
        
        # Obtener métricas del sistema
        system_metrics = self._get_system_metrics()
        
        # Construir respuesta
        status = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': health_percentage,
            'status': 'healthy' if all_critical_healthy else 'unhealthy',
            'critical_issues': len(critical_checks),
            'checks': checks_results,
            'system_metrics': system_metrics,
            'summary': self._generate_summary(checks_results, system_metrics)
        }
        
        # Guardar en historial
        self.status_history.append(status)
        if len(self.status_history) > self.max_history_size:
            self.status_history = self.status_history[-self.max_history_size:]
        
        return status
    
    def _calculate_health_percentage(self, checks_results: Dict) -> float:
        """Calcula porcentaje de salud basado en checks"""
        if not checks_results:
            return 100.0
        
        healthy_checks = sum(1 for c in checks_results.values() if c['status'] == 'healthy')
        total_checks = len(checks_results)
        
        return (healthy_checks / total_checks * 100) if total_checks > 0 else 0
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Obtiene métricas del sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Obtener métricas de red si están disponibles
            net_io = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'bytes_sent_mb': net_io.bytes_sent / (1024**2),
                'bytes_recv_mb': net_io.bytes_recv / (1024**2),
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas del sistema: {e}")
            return {}
    
    def _generate_summary(self, checks_results: Dict, system_metrics: Dict) -> Dict[str, str]:
        """Genera resumen ejecutivo del estado"""
        issues = []
        warnings = []
        
        # Analizar checks
        for check_name, result in checks_results.items():
            if result['status'] == 'unhealthy':
                issues.append(f"{check_name}: {result.get('error', 'Error desconocido')}")
        
        # Analizar métricas del sistema
        if system_metrics.get('cpu_percent', 0) > 80:
            warnings.append(f"CPU alto: {system_metrics['cpu_percent']}%")
        
        if system_metrics.get('memory_percent', 0) > 85:
            warnings.append(f"Memoria alta: {system_metrics['memory_percent']}%")
        
        if system_metrics.get('disk_percent', 0) > 90:
            warnings.append(f"Disco casi lleno: {system_metrics['disk_percent']}%")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'recommendations': self._generate_recommendations(issues, warnings)
        }
    
    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Genera recomendaciones basadas en issues y warnings"""
        recommendations = []
        
        if any('database' in issue.lower() for issue in issues):
            recommendations.append("Verificar conexión a base de datos y credenciales")
        
        if any('memory' in warning.lower() for warning in warnings):
            recommendations.append("Considerar aumentar memoria o optimizar uso")
        
        if any('disk' in warning.lower() for warning in warnings):
            recommendations.append("Limpiar archivos temporales y hacer espacio en disco")
        
        if not recommendations:
            recommendations.append("Sistema funcionando correctamente")
        
        return recommendations
    
    def start_monitoring(self, interval: Optional[int] = None):
        """Inicia monitoreo continuo en segundo plano"""
        if self.is_monitoring:
            logger.warning("Monitoreo ya está en ejecución")
            return
        
        if interval:
            self.check_interval = interval
        
        self.is_monitoring = True
        
        def monitoring_loop():
            logger.info(f"🚀 Iniciando monitoreo de salud (intervalo: {self.check_interval}s)")
            
            while self.is_monitoring:
                try:
                    self.get_health_status()
                except Exception as e:
                    logger.error(f"Error en loop de monitoreo: {e}")
                
                time.sleep(self.check_interval)
            
            logger.info("🛑 Monitoreo detenido")
        
        self.monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Detiene el monitoreo continuo"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def get_history(self, hours: int = 24) -> List[Dict]:
        """Obtiene historial de estados de salud"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            status for status in self.status_history
            if datetime.fromisoformat(status['timestamp']) > cutoff
        ]
    
    def get_metrics_trend(self, metric_name: str, hours: int = 24) -> Dict:
        """Obtiene tendencia de una métrica específica"""
        if metric_name not in self.metrics_history:
            return {'error': f'Métrica no encontrada: {metric_name}'}
        
        cutoff = datetime.now() - timedelta(hours=hours)
        metrics = [
            m for m in self.metrics_history[metric_name]
            if m['timestamp'] > cutoff
        ]
        
        if not metrics:
            return {'error': f'No hay datos para {metric_name} en las últimas {hours} horas'}
        
        values = [m['value'] for m in metrics]
        timestamps = [m['timestamp'] for m in metrics]
        
        return {
            'metric': metric_name,
            'values': values,
            'timestamps': timestamps,
            'average': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'current': values[-1] if values else None,
            'trend': self._calculate_trend(values)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calcula tendencia de una serie de valores"""
        if len(values) < 2:
            return 'estable'
        
        # Usar regresión lineal simple
        from statistics import mean
        n = len(values)
        x = list(range(n))
        y = values
        
        x_mean = mean(x)
        y_mean = mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'estable'
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return 'ascendente'
        elif slope < -0.1:
            return 'descendente'
        else:
            return 'estable'
    
    def generate_report(self, hours: int = 24) -> Dict:
        """Genera reporte completo de salud"""
        current_status = self.get_health_status()
        history = self.get_history(hours)
        
        # Calcular estadísticas
        if history:
            health_values = [s['overall_health'] for s in history]
            avg_health = sum(health_values) / len(health_values)
        else:
            avg_health = current_status['overall_health']
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'period_hours': hours,
            'current_status': current_status,
            'average_health': avg_health,
            'history_summary': {
                'total_checks': len(history),
                'healthy_percentage': self._calculate_healthy_percentage(history),
                'trend': self._calculate_health_trend(history)
            },
            'recommendations': current_status['summary']['recommendations']
        }
    
    def _calculate_healthy_percentage(self, history: List[Dict]) -> float:
        """Calcula porcentaje de tiempo saludable"""
        if not history:
            return 0.0
        
        healthy_count = sum(1 for status in history if status['status'] == 'healthy')
        return (healthy_count / len(history)) * 100
    
    def _calculate_health_trend(self, history: List[Dict]) -> str:
        """Calcula tendencia de salud"""
        if len(history) < 2:
            return 'insuficientes datos'
        
        health_values = [s['overall_health'] for s in history[-10:]]  # Últimos 10
        return self._calculate_trend(health_values)

# Singleton global
_health_monitor_instance = None

def get_health_monitor() -> HealthMonitor:
    """Obtiene la instancia singleton de HealthMonitor"""
    global _health_monitor_instance
    if _health_monitor_instance is None:
        _health_monitor_instance = HealthMonitor()
    return _health_monitor_instance

def init_health_monitoring(interval: int = 60):
    """Inicializa y comienza el monitoreo de salud"""
    monitor = get_health_monitor()
    monitor.start_monitoring(interval)
    return monitor

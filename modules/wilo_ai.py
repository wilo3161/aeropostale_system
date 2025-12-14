# modules/wilo_ai.py
"""
Módulo principal de WILO AI para el sistema Aeropostale.
"""

import logging
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import pandas as pd
from pathlib import Path

from modules.config_manager import get_config
from modules.error_handler import get_error_handler
from modules.health_monitor import get_health_monitor
from modules.database import get_database
from modules.cache import get_cache_manager

logger = logging.getLogger(__name__)

class SistemaMonitorProactivo:
    """Sistema de monitoreo proactivo de correos y KPIs"""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path('data_wilo/email_config.json')
        self.config = self._load_config()
        self.error_handler = get_error_handler()
        self.db = get_database()
        
    def _load_config(self) -> Dict:
        """Carga la configuración de correo"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def escaneo_correos_continuo(self):
        """Escaneo continuo de correos en busca de novedades"""
        try:
            logger.info("Iniciando escaneo de correos...")
            
            # Aquí iría la lógica real de escaneo de correos
            # Por ahora, simulamos con un archivo de ejemplo
            from modulo_novedades_correo_mejorado import analizar_correo_con_ia
            
            # Ejemplo: analizar un correo de ejemplo
            correo_ejemplo = {
                'subject': 'Re: Problema con envío a tienda XYZ',
                'body': 'Buen día, hay un problema con el envío a la tienda XYZ...',
                'from': 'logistica@proveedor.com'
            }
            
            resultado = analizar_correo_con_ia(correo_ejemplo)
            
            if resultado and resultado.get('accion_requerida'):
                self._procesar_accion_correo(resultado)
            
            logger.info("Escaneo de correos completado")
            return resultado
            
        except Exception as e:
            self.error_handler.handle(e, user_context="Error en escaneo de correos")
            return None
    
    def _procesar_accion_correo(self, resultado: Dict):
        """Procesa la acción requerida por el análisis de correo"""
        accion = resultado.get('accion_requerida')
        
        if accion == 'alertar_logistica':
            self._enviar_alerta_logistica(resultado)
        elif accion == 'crear_ticket':
            self._crear_ticket_soporte(resultado)
        elif accion == 'actualizar_kpi':
            self._actualizar_kpi_desde_correo(resultado)
    
    def _enviar_alerta_logistica(self, datos: Dict):
        """Envía alerta al equipo de logística"""
        logger.warning(f"ALERTA LOGÍSTICA: {datos.get('resumen')}")
        # Aquí se integraría con el sistema de alertas (WhatsApp, email, etc.)
    
    def _crear_ticket_soporte(self, datos: Dict):
        """Crea un ticket de soporte"""
        logger.info(f"Creando ticket de soporte: {datos.get('resumen')}")
        # Aquí se integraría con el sistema de tickets
    
    def _actualizar_kpi_desde_correo(self, datos: Dict):
        """Actualiza KPIs basado en información de correo"""
        logger.info(f"Actualizando KPI desde correo: {datos.get('resumen')}")
        # Aquí se actualizarían los KPIs en la base de datos
    
    def analisis_kpis_automatico(self):
        """Análisis automático de KPIs para detectar anomalías"""
        try:
            logger.info("Iniciando análisis automático de KPIs...")
            
            # Obtener KPIs de la última semana
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=7)
            
            df_kpis = self.db.cargar_historico_kpis(
                fecha_inicio=str(fecha_inicio),
                fecha_fin=str(fecha_fin)
            )
            
            if df_kpis.empty:
                logger.warning("No hay datos de KPIs para analizar")
                return
            
            # Detectar anomalías
            anomalias = self._detectar_anomalias_kpis(df_kpis)
            
            if anomalias:
                logger.warning(f"Se detectaron {len(anomalias)} anomalías en KPIs")
                self._procesar_anomalias_kpis(anomalias)
            else:
                logger.info("No se detectaron anomalías en KPIs")
            
        except Exception as e:
            self.error_handler.handle(e, user_context="Error en análisis de KPIs")
    
    def _detectar_anomalias_kpis(self, df_kpis: pd.DataFrame) -> List[Dict]:
        """Detecta anomalías en los datos de KPIs"""
        anomalias = []
        
        # Agrupar por trabajador y actividad
        for (nombre, actividad), grupo in df_kpis.groupby(['nombre', 'actividad']):
            # Calcular estadísticas
            media = grupo['cantidad'].mean()
            std = grupo['cantidad'].std()
            
            # Detectar valores atípicos (más de 2 desviaciones estándar)
            for _, fila in grupo.iterrows():
                if std > 0 and abs(fila['cantidad'] - media) > 2 * std:
                    anomalias.append({
                        'fecha': fila['fecha'],
                        'nombre': nombre,
                        'actividad': actividad,
                        'cantidad': fila['cantidad'],
                        'media': media,
                        'desviacion': std,
                        'tipo': 'valor_atipico'
                    })
        
        return anomalias
    
    def _procesar_anomalias_kpis(self, anomalias: List[Dict]):
        """Procesa las anomalías detectadas en KPIs"""
        for anomalia in anomalias:
            # Aquí se podrían generar alertas o ajustar metas automáticamente
            logger.warning(
                f"Anomalía detectada: {anomalia['nombre']} - {anomalia['actividad']} "
                f"en {anomalia['fecha']}: {anomalia['cantidad']} (media: {anomalia['media']:.2f})"
            )


class MotorRespuestasAutomaticas:
    """Motor de respuestas automáticas a correos"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.plantillas = self._cargar_plantillas()
    
    def _cargar_plantillas(self) -> Dict:
        """Carga plantillas de respuestas automáticas"""
        plantillas_path = Path('data_wilo/plantillas_respuestas.json')
        
        if plantillas_path.exists():
            with open(plantillas_path, 'r') as f:
                return json.load(f)
        
        # Plantillas por defecto
        return {
            'confirmacion_recepcion': {
                'asunto': 'Confirmación de recepción: {tema}',
                'cuerpo': 'Hemos recibido su mensaje sobre "{tema}".\n\n'
                         'Nuestro equipo lo revisará y le dará seguimiento.\n\n'
                         'Gracias por contactarnos.\n\nSaludos,\nEquipo de Logística Aeropostale'
            },
            'alerta_logistica': {
                'asunto': 'ALERTA: {problema}',
                'cuerpo': 'Se ha detectado una alerta en el sistema:\n\n'
                         'Problema: {problema}\n'
                         'Ubicación: {ubicacion}\n'
                         'Impacto: {impacto}\n\n'
                         'Acciones tomadas: {acciones}\n\n'
                         'Estaremos monitoreando la situación.'
            }
        }
    
    def generar_respuesta_automatica(self, tipo: str, datos: Dict) -> Optional[Dict]:
        """Genera una respuesta automática basada en plantillas"""
        try:
            if tipo not in self.plantillas:
                logger.error(f"Tipo de plantilla no encontrado: {tipo}")
                return None
            
            plantilla = self.plantillas[tipo]
            
            # Reemplazar variables en la plantilla
            asunto = plantilla['asunto'].format(**datos)
            cuerpo = plantilla['cuerpo'].format(**datos)
            
            return {
                'asunto': asunto,
                'cuerpo': cuerpo,
                'tipo': tipo,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.error_handler.handle(e, user_context="Error generando respuesta automática")
            return None
    
    def enviar_respuesta(self, respuesta: Dict, destinatario: str):
        """Envía una respuesta por correo"""
        try:
            # Aquí se integraría con el servidor de correo
            logger.info(f"Enviando respuesta a {destinatario}: {respuesta['asunto']}")
            
            # Simulación de envío
            logger.debug(f"Cuerpo del correo:\n{respuesta['cuerpo']}")
            
            return True
            
        except Exception as e:
            self.error_handler.handle(e, user_context="Error enviando respuesta")
            return False


class SistemaAlertasWhatsApp:
    """Sistema de alertas por WhatsApp"""
    
    def __init__(self):
        self.config = get_config()
        self.error_handler = get_error_handler()
        self._inicializar_cliente()
    
    def _inicializar_cliente(self):
        """Inicializa el cliente de WhatsApp"""
        # Aquí se inicializaría la conexión con la API de WhatsApp
        # Por ahora, solo simulamos
        self.cliente_inicializado = True
    
    def enviar_alerta_inteligente(self, tipo: str, datos: Dict, urgencia: str = 'media'):
        """Envía una alerta inteligente por WhatsApp"""
        try:
            if not self.cliente_inicializado:
                logger.error("Cliente de WhatsApp no inicializado")
                return False
            
            # Formatear mensaje según tipo y urgencia
            mensaje = self._formatear_mensaje_alerta(tipo, datos, urgencia)
            
            # Obtener destinatarios según urgencia
            destinatarios = self._obtener_destinatarios(urgencia)
            
            # Enviar a cada destinatario
            for destinatario in destinatarios:
                self._enviar_mensaje_whatsapp(destinatario, mensaje)
            
            logger.info(f"Alerta de {tipo} enviada a {len(destinatarios)} destinatarios")
            return True
            
        except Exception as e:
            self.error_handler.handle(e, user_context="Error enviando alerta por WhatsApp")
            return False
    
    def _formatear_mensaje_alerta(self, tipo: str, datos: Dict, urgencia: str) -> str:
        """Formatea el mensaje de alerta"""
        # Emojis según urgencia
        emojis = {
            'alta': '🔴',
            'media': '🟡',
            'baja': '🟢'
        }
        
        emoji = emojis.get(urgencia, '⚪')
        
        # Plantillas de mensaje
        plantillas = {
            'reporte_diario': (
                f"{emoji} *REPORTE DIARIO AEROPOSTALE*\n"
                f"Fecha: {datos.get('fecha', 'N/A')}\n"
                f"KPI Transferencias: {datos.get('kpi_transferencias', 'N/A')}%\n"
                f"KPI Distribución: {datos.get('kpi_distribucion', 'N/A')}%\n"
                f"KPI Arreglos: {datos.get('kpi_arreglos', 'N/A')}%\n"
                f"Alertas activas: {datos.get('alertas_activas', '0')}\n"
                f"Problemas críticos: {datos.get('problemas_criticos', '0')}\n"
                f"Recomendación: {datos.get('recomendacion', 'N/A')}\n"
                f"Dashboard: {datos.get('link_dashboard', 'N/A')}"
            ),
            'critico': (
                f"{emoji} *ALERTA CRÍTICA AEROPOSTALE*\n"
                f"Problema: {datos.get('problema', 'N/A')}\n"
                f"Ubicación: {datos.get('ubicacion', 'N/A')}\n"
                f"Impacto: {datos.get('impacto', 'N/A')}\n"
                f"Acción 1: {datos.get('accion1', 'N/A')}\n"
                f"Acción 2: {datos.get('accion2', 'N/A')}\n"
                f"Paso 1: {datos.get('paso1', 'N/A')}\n"
                f"Paso 2: {datos.get('paso2', 'N/A')}\n"
                f"Tiempo límite: {datos.get('tiempo_limite', 'N/A')}\n"
                f"Contacto: {datos.get('contacto', 'N/A')}"
            ),
            'advertencia': (
                f"{emoji} *ADVERTENCIA AEROPOSTALE*\n"
                f"Tipo: {datos.get('tipo', 'N/A')}\n"
                f"Descripción: {datos.get('descripcion', 'N/A')}\n"
                f"Recomendación: {datos.get('recomendacion', 'N/A')}\n"
                f"Próxima revisión: {datos.get('proxima_revision', 'N/A')}"
            )
        }
        
        return plantillas.get(tipo, f"{emoji} Alerta: {datos}")
    
    def _obtener_destinatarios(self, urgencia: str) -> List[str]:
        """Obtiene la lista de destinatarios según la urgencia"""
        # En producción, esto vendría de una base de datos o configuración
        destinatarios = {
            'alta': ['+593991234567', '+593987654321'],  # Jefes y gerentes
            'media': ['+593991234567'],  # Supervisores
            'baja': ['+593991234567']  # Operativos
        }
        
        return destinatarios.get(urgencia, [])
    
    def _enviar_mensaje_whatsapp(self, destinatario: str, mensaje: str):
        """Envía un mensaje por WhatsApp (simulado)"""
        # En producción, aquí se usaría una API como Twilio o WhatsApp Business API
        logger.debug(f"Enviando WhatsApp a {destinatario}: {mensaje[:50]}...")


class SistemaAprendizajeWilo:
    """Sistema de aprendizaje automático de WILO AI"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.dataset_acciones = self._cargar_dataset()
        self.modelo = None
        
    def _cargar_dataset(self) -> List[Dict]:
        """Carga el dataset de aprendizaje"""
        dataset_path = Path('data_wilo/dataset_aprendizaje.json')
        
        if dataset_path.exists():
            with open(dataset_path, 'r') as f:
                return json.load(f)
        
        return []
    
    def registrar_accion(self, contexto: Dict, accion: str, resultado: str):
        """Registra una acción tomada para aprendizaje futuro"""
        registro = {
            'timestamp': datetime.now().isoformat(),
            'contexto': contexto,
            'accion': accion,
            'resultado': resultado,
            'feedback': None
        }
        
        self.dataset_acciones.append(registro)
        self._guardar_dataset()
        
        logger.info(f"Acción registrada para aprendizaje: {accion}")
    
    def _guardar_dataset(self):
        """Guarda el dataset en disco"""
        dataset_path = Path('data_wilo/dataset_aprendizaje.json')
        dataset_path.parent.mkdir(exist_ok=True)
        
        with open(dataset_path, 'w') as f:
            json.dump(self.dataset_acciones, f, indent=2)
    
    def entrenar_modelo_decisiones(self):
        """Entrena un modelo para tomar decisiones basadas en el historial"""
        try:
            if len(self.dataset_acciones) < 10:
                logger.info("Dataset insuficiente para entrenar modelo")
                return False
            
            logger.info("Entrenando modelo de decisiones...")
            
            # Aquí iría el código real de entrenamiento de ML
            # Por ahora, simulamos con lógica simple
            
            # Analizar patrones en el dataset
            patrones = self._analizar_patrones_acciones()
            
            # Crear modelo simple basado en reglas
            self.modelo = {
                'patrones': patrones,
                'ultimo_entrenamiento': datetime.now().isoformat(),
                'total_registros': len(self.dataset_acciones)
            }
            
            logger.info(f"Modelo entrenado con {len(self.dataset_acciones)} registros")
            return True
            
        except Exception as e:
            self.error_handler.handle(e, user_context="Error entrenando modelo")
            return False
    
    def _analizar_patrones_acciones(self) -> Dict:
        """Analiza patrones en las acciones registradas"""
        patrones = {}
        
        for registro in self.dataset_acciones:
            contexto = registro['contexto']
            accion = registro['accion']
            resultado = registro['resultado']
            
            # Crear una clave basada en el contexto
            clave = self._generar_clave_contexto(contexto)
            
            if clave not in patrones:
                patrones[clave] = {
                    'acciones': {},
                    'total': 0
                }
            
            if accion not in patrones[clave]['acciones']:
                patrones[clave]['acciones'][accion] = {
                    'exitos': 0,
                    'fallos': 0,
                    'total': 0
                }
            
            accion_data = patrones[clave]['acciones'][accion]
            accion_data['total'] += 1
            
            if resultado == 'exito':
                accion_data['exitos'] += 1
            else:
                accion_data['fallos'] += 1
            
            patrones[clave]['total'] += 1
        
        return patrones
    
    def _generar_clave_contexto(self, contexto: Dict) -> str:
        """Genera una clave única para un contexto"""
        # Simplificamos el contexto a una cadena
        return str(sorted(contexto.items()))
    
    def sugerir_accion(self, contexto: Dict) -> Optional[str]:
        """Sugiere una acción basada en el contexto y el modelo"""
        if not self.modelo:
            logger.warning("Modelo no entrenado, no se puede sugerir acción")
            return None
        
        clave = self._generar_clave_contexto(contexto)
        patrones = self.modelo['patrones']
        
        if clave in patrones:
            # Encontrar la acción con mayor tasa de éxito
            mejor_accion = None
            mejor_tasa = -1
            
            for accion, datos in patrones[clave]['acciones'].items():
                if datos['total'] > 0:
                    tasa_exito = datos['exitos'] / datos['total']
                    if tasa_exito > mejor_tasa:
                        mejor_tasa = tasa_exito
                        mejor_accion = accion
            
            return mejor_accion
        
        return None


class WiloAIManager:
    """Gestor principal de WILO AI"""
    
    def __init__(self):
        self.components = {}
        self.is_running = False
        self.thread = None
        self.error_handler = get_error_handler()
        
    def initialize(self) -> bool:
        """Inicializa todos los componentes de WILO AI"""
        try:
            logger.info("Inicializando WILO AI...")
            
            # Inicializar componentes
            self.components = {
                'monitor': SistemaMonitorProactivo(),
                'respuestas': MotorRespuestasAutomaticas(),
                'whatsapp': SistemaAlertasWhatsApp(),
                'aprendizaje': SistemaAprendizajeWilo()
            }
            
            logger.info("✅ WILO AI inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando WILO AI: {e}")
            return False
    
    def start_background_monitoring(self):
        """Inicia monitoreo en segundo plano"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.thread.start()
            logger.info("🔄 Monitoreo WILO AI iniciado")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.is_running:
            try:
                # 1. Monitoreo de correos
                self.components['monitor'].escaneo_correos_continuo()
                
                # 2. Análisis de KPIs
                self.components['monitor'].analisis_kpis_automatico()
                
                # 3. Aprendizaje automático
                if len(self.components['aprendizaje'].dataset_acciones) % 10 == 0:
                    self.components['aprendizaje'].entrenar_modelo_decisiones()
                
                # 4. Reporte periódico
                if datetime.now().hour == 8:  # 8 AM
                    self._send_daily_report()
                
                time.sleep(300)  # Esperar 5 minutos
                
            except Exception as e:
                logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(60)  # Esperar 1 minuto en caso de error
    
    def _send_daily_report(self):
        """Envía reporte diario automático"""
        try:
            # Obtener datos del día anterior
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Aquí se obtendrían los datos reales del sistema
            # Por ahora, simulamos
            datos_reporte = {
                'fecha': yesterday,
                'kpi_transferencias': "95.5",
                'kpi_distribucion': "88.2",
                'kpi_arreglos': "92.7",
                'alertas_activas': "2",
                'problemas_criticos': "0",
                'recomendacion': "Revisar distribución de carga",
                'link_dashboard': "https://kpi-aeropostale.streamlit.app"
            }
            
            # Enviar por WhatsApp
            self.components['whatsapp'].enviar_alerta_inteligente(
                tipo='reporte_diario',
                datos=datos_reporte,
                urgencia='baja'
            )
            
            logger.info("Reporte diario enviado")
                
        except Exception as e:
            logger.error(f"Error enviando reporte diario: {e}")
    
    def get_status(self) -> Dict:
        """Obtiene estado de WILO AI"""
        return {
            'is_running': self.is_running,
            'components': list(self.components.keys()),
            'learning_records': len(self.components['aprendizaje'].dataset_acciones) if 'aprendizaje' in self.components else 0,
            'model_trained': self.components['aprendizaje'].modelo is not None if 'aprendizaje' in self.components else False
        }
    
    def stop(self):
        """Detiene WILO AI"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 WILO AI detenido")


# Singleton global
_wilo_ai_manager = None

def get_wilo_ai_manager() -> WiloAIManager:
    """Obtiene la instancia singleton de WiloAIManager"""
    global _wilo_ai_manager
    if _wilo_ai_manager is None:
        _wilo_ai_manager = WiloAIManager()
    return _wilo_ai_manager

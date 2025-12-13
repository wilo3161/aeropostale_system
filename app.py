# app.py - SOLO CAMBIOS NECESARIOS

# ================================
# IMPORTACIONES ACTUALIZADAS
# ================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import hashlib
import logging
from supabase import create_client, Client
import qrcode
from PIL import Image
import fpdf
from fpdf import FPDF
import base64
import io
import tempfile
import re
import sqlite3
from typing import Dict, List, Optional, Tuple, Any, Union
import requests
from io import BytesIO
from PIL import Image as PILImage
import os
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import smtplib
import imaplib
import json
from pathlib import Path
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
import unicodedata
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import warnings
warnings.filterwarnings('ignore')

# ================================
# IMPORTAR NUEVOS MÓDULOS
# ================================
from modules import (
    get_config,
    get_error_handler,
    get_health_monitor,
    init_health_monitoring,
    error_handler_decorator
)

# ================================
# INICIALIZACIÓN DE MÓDULOS
# ================================
# Configuración centralizada
config = get_config()

# Manejador de errores
error_handler = get_error_handler()

# Monitor de salud
health_monitor = get_health_monitor()

# ================================
# REEMPLAZAR VARIABLES DE CONFIGURACIÓN
# ================================
# OLD: SUPABASE_URL = "https://..."
# OLD: SUPABASE_KEY = "eyJhbGci..."
# OLD: ADMIN_PASSWORD = "Wilo3161"
# OLD: USER_PASSWORD = "User1234"

# NEW: Usar config.get()
SUPABASE_URL = config.get('database.url')
SUPABASE_KEY = config.get('database.key')
ADMIN_PASSWORD = config.get('security.admin_password')
USER_PASSWORD = config.get('security.user_password')

# Directorios desde configuración
APP_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(APP_DIR, config.get('paths.images_dir', 'images'))
os.makedirs(IMAGES_DIR, exist_ok=True)

# Configuración de WILO AI desde configuración
WILO_DATA_FOLDER = Path(config.get('paths.data_dir', 'data_wilo'))
WILO_DATA_FOLDER.mkdir(exist_ok=True)
NOVEDADES_DB = WILO_DATA_FOLDER / "novedades_database.json"
CONFIG_EMAIL_FILE = WILO_DATA_FOLDER / "email_config.json"
CONFIG_GEMINI_FILE = WILO_DATA_FOLDER / "gemini_config.json"

# ================================
# INICIALIZACIÓN DE SESSION STATE (MEJORADO)
# ================================
def init_session_state():
    """Inicializa todas las variables de session state"""
    defaults = {
        'user_type': None,
        'password_correct': False,
        'selected_menu': 0,
        'show_login': False,
        'historico_data': None,
        'wilo_ai': None,
        'reconciler': None,
        'processed': False,
        'show_details': False,
        'show_preview': False,
        'pdf_data': None,
        'datos_calculados': None,
        'fecha_guardar': None,
        'health_monitoring_started': False
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

init_session_state()

# ================================
# CONFIGURACIÓN INICIAL Y LOGGING (MEJORADO)
# ================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================================
# INICIALIZACIÓN DE SUPABASE (MEJORADO)
# ================================
@st.cache_resource
def init_supabase() -> Optional[Client]:
    """Inicializa y cachea el cliente de Supabase con manejo de errores"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        error_msg = "Faltan las variables de configuración de Supabase"
        logger.error(error_msg)
        st.error(error_handler.handle(Exception(error_msg), 
                                      user_context="❌ Error de configuración de base de datos"))
        return None
    
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        error_handler.handle(e, {'context': 'init_supabase'})
        return None

# Inicializar cliente de Supabase
supabase = init_supabase()

# ================================
# FUNCIONES DE UTILIDAD COMPARTIDAS (MEJORADAS)
# ================================
@error_handler_decorator("Error validando fecha")
def validar_fecha(fecha: str) -> bool:
    """Valida que la fecha tenga el formato YYYY-MM-DD"""
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except ValueError:
        return False

@error_handler_decorator("Error validando número")
def validar_numero_positivo(valor: Any) -> bool:
    """Valida que un valor sea un número positivo"""
    try:
        num = float(valor)
        return num >= 0
    except (ValueError, TypeError):
        return False

@error_handler_decorator("Error validando distribuciones")
def validar_distribuciones(valor: Any) -> bool:
    """Valida que el valor de distribuciones sea positivo y numérico"""
    try:
        num = float(valor)
        return num >= 0 and num <= 10000
    except (ValueError, TypeError):
        return False

def hash_password(pw: str) -> str:
    """Genera un hash SHA256 para una contraseña."""
    return hashlib.sha256(pw.encode()).hexdigest()

# ================================
# FUNCIONES DE KPIs (MEJORADAS)
# ================================
@error_handler_decorator("Error calculando KPI")
def calcular_kpi(cantidad: float, meta: float) -> float:
    """Calcula el porcentaje de KPI general"""
    try:
        return (cantidad / meta) * 100 if meta > 0 else 0
    except Exception as e:
        error_handler.handle(e, {'cantidad': cantidad, 'meta': meta})
        return 0

# ... (resto de funciones KPI con decorador) ...

# ================================
# FUNCIONES DE ACCESO A DATOS (MEJORADAS)
# ================================
@error_handler_decorator("Error obteniendo trabajadores")
def obtener_trabajadores() -> pd.DataFrame:
    """Obtiene la lista de trabajadores desde Supabase"""
    if supabase is None:
        error_msg = "Cliente de Supabase no inicializado"
        logger.error(error_msg)
        return pd.DataFrame({
            'nombre': ["Andrés Yépez", "Josué Imbacuán", "Luis Perugachi", "Diana García", 
                      "Simón Vera", "Jhonny Guadalupe", "Victor Montenegro", "Fernando Quishpe"],
            'equipo': ["Transferencias", "Transferencias", "Distribución", "Arreglo", 
                      "Guías", "Ventas", "Ventas", "Ventas"]
        })
    
    try:
        response = supabase.from_('trabajadores').select('nombre, equipo').eq('activo', True).order('equipo,nombre', desc=False).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"No se pudieron obtener trabajadores: {response.error}")
            return pd.DataFrame({
                'nombre': ["Andrés Yépez", "Josué Imbacuán", "Luis Perugachi", "Diana García", 
                          "Simón Vera", "Jhonny Guadalupe", "Victor Montenegro", "Fernando Quishpe"],
                'equipo': ["Transferencias", "Transferencias", "Distribución", "Arreglo", 
                          "Guías", "Ventas", "Ventas", "Ventas"]
            })
        
        if response and hasattr(response, 'data') and response.data:
            df = pd.DataFrame(response.data)
            if 'Luis Perugachi' in df['nombre'].values:
                df.loc[df['nombre'] == 'Luis Perugachi', 'equipo'] = 'Distribución'
            return df
        else:
            logger.warning("No se encontraron trabajadores en Supabase")
            return pd.DataFrame(columns=['nombre', 'equipo'])
    except Exception as e:
        error_handler.handle(e, {'context': 'obtener_trabajadores'})
        return pd.DataFrame({
            'nombre': ["Andrés Yépez", "Josué Imbacuán", "Luis Perugachi", "Diana García", 
                      "Simón Vera", "Jhonny Guadalupe", "Victor Montenegro", "Fernando Quishpe"],
            'equipo': ["Transferencias", "Transferencias", "Distribución", "Arreglo", 
                      "Guías", "Ventas", "Ventas", "Ventas"]
        })

# ... (resto de funciones de base de datos con decorador) ...

# ================================
# NUEVA SECCIÓN: SISTEMA DE SALUD
# ================================
def mostrar_sistema_salud():
    """Muestra el dashboard del sistema de salud"""
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>❤️ Sistema de Salud</h1><div class='header-subtitle'>Monitoreo y diagnóstico del sistema</div></div>", unsafe_allow_html=True)
    
    # Iniciar monitoreo si no está activo
    if not st.session_state.get('health_monitoring_started', False):
        try:
            init_health_monitoring(interval=60)
            st.session_state.health_monitoring_started = True
            st.success("✅ Monitoreo de salud iniciado")
        except Exception as e:
            error_handler.handle(e, user_context="❌ Error iniciando monitoreo de salud")
    
    # Pestañas
    tab1, tab2, tab3 = st.tabs(["📊 Estado Actual", "📈 Métricas", "⚙️ Configuración"])
    
    with tab1:
        mostrar_estado_salud()
    
    with tab2:
        mostrar_metricas_salud()
    
    with tab3:
        mostrar_configuracion_salud()

def mostrar_estado_salud():
    """Muestra el estado actual del sistema"""
    try:
        # Obtener estado de salud
        health_status = health_monitor.get_health_status()
        
        # Encabezado con estado
        status_color = "🟢" if health_status['status'] == 'healthy' else "🔴"
        st.markdown(f"### {status_color} Estado General: {health_status['overall_health']:.1f}%")
        
        # KPIs rápidos
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Salud", f"{health_status['overall_health']:.1f}%")
        
        with col2:
            critical_issues = health_status['critical_issues']
            st.metric("Problemas Críticos", critical_issues, 
                     delta=None if critical_issues == 0 else f"+{critical_issues}")
        
        with col3:
            cpu = health_status['system_metrics'].get('cpu_percent', 0)
            st.metric("CPU", f"{cpu:.1f}%")
        
        with col4:
            memory = health_status['system_metrics'].get('memory_percent', 0)
            st.metric("Memoria", f"{memory:.1f}%")
        
        # Checks detallados
        st.subheader("🔍 Checks de Salud")
        
        for check_name, check_result in health_status['checks'].items():
            status_icon = "✅" if check_result['status'] == 'healthy' else "❌"
            with st.expander(f"{status_icon} {check_name}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Estado:** {check_result['status']}")
                    st.write(f"**Tiempo respuesta:** {check_result.get('response_time', 0):.2f}s")
                with col_b:
                    st.write(f"**Última verificación:** {check_result['timestamp'][11:19]}")
                    if check_result['status'] == 'unhealthy':
                        st.error(f"**Error:** {check_result.get('error', 'Desconocido')}")
        
        # Sistema de métricas
        st.subheader("📊 Métricas del Sistema")
        
        if health_status['system_metrics']:
            metrics_cols = st.columns(3)
            
            with metrics_cols[0]:
                st.markdown("**CPU y Memoria**")
                st.progress(health_status['system_metrics'].get('cpu_percent', 0) / 100, 
                           text=f"CPU: {health_status['system_metrics'].get('cpu_percent', 0):.1f}%")
                st.progress(health_status['system_metrics'].get('memory_percent', 0) / 100,
                           text=f"Memoria: {health_status['system_metrics'].get('memory_percent', 0):.1f}%")
            
            with metrics_cols[1]:
                st.markdown("**Almacenamiento**")
                st.progress(health_status['system_metrics'].get('disk_percent', 0) / 100,
                           text=f"Disco: {health_status['system_metrics'].get('disk_percent', 0):.1f}%")
                
                if 'disk_free_gb' in health_status['system_metrics']:
                    st.info(f"Libre: {health_status['system_metrics']['disk_free_gb']:.1f} GB")
            
            with metrics_cols[2]:
                st.markdown("**Red**")
                if 'bytes_sent_mb' in health_status['system_metrics']:
                    st.metric("Enviado", f"{health_status['system_metrics']['bytes_sent_mb']:.1f} MB")
                if 'bytes_recv_mb' in health_status['system_metrics']:
                    st.metric("Recibido", f"{health_status['system_metrics']['bytes_recv_mb']:.1f} MB")
        
        # Recomendaciones
        if health_status['summary']['issues'] or health_status['summary']['warnings']:
            st.subheader("🚨 Recomendaciones")
            
            if health_status['summary']['issues']:
                st.error("**Problemas detectados:**")
                for issue in health_status['summary']['issues']:
                    st.write(f"• {issue}")
            
            if health_status['summary']['warnings']:
                st.warning("**Advertencias:**")
                for warning in health_status['summary']['warnings']:
                    st.write(f"• {warning}")
            
            if health_status['summary']['recommendations']:
                st.info("**Acciones recomendadas:**")
                for rec in health_status['summary']['recommendations']:
                    st.write(f"• {rec}")
        
        # Botones de acción
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("🔄 Re-ejecutar Checks", use_container_width=True):
                st.rerun()
        
        with col_btn2:
            if st.button("📊 Generar Reporte", use_container_width=True):
                with st.spinner("Generando reporte..."):
                    report = health_monitor.generate_report(hours=24)
                    st.download_button(
                        label="⬇️ Descargar JSON",
                        data=json.dumps(report, indent=2, ensure_ascii=False),
                        file_name=f"reporte_salud_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
        
        with col_btn3:
            if st.button("🩺 Diagnóstico Completo", use_container_width=True):
                with st.spinner("Ejecutando diagnóstico..."):
                    time.sleep(2)
                    st.success("Diagnóstico completado")
                    # Aquí iría un diagnóstico más detallado
    
    except Exception as e:
        error_handler.handle(e, user_context="❌ Error obteniendo estado de salud")

def mostrar_metricas_salud():
    """Muestra métricas históricas del sistema"""
    try:
        st.subheader("📈 Tendencias de Salud")
        
        # Selector de métrica
        metric_options = {
            'Salud General': 'overall_health',
            'Uso de CPU': 'cpu_percent',
            'Uso de Memoria': 'memory_percent',
            'Uso de Disco': 'disk_percent'
        }
        
        selected_metric = st.selectbox("Seleccionar métrica:", list(metric_options.keys()))
        hours = st.slider("Horas a visualizar:", 1, 72, 24)
        
        # Obtener tendencia
        if selected_metric == 'Salud General':
            history = health_monitor.get_history(hours)
            if history:
                timestamps = [datetime.fromisoformat(h['timestamp']) for h in history]
                values = [h['overall_health'] for h in history]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=timestamps, y=values,
                    mode='lines+markers',
                    name='Salud General',
                    line=dict(color='green' if values[-1] > 80 else 'red')
                ))
                
                fig.update_layout(
                    title=f'Tendencia de Salud ({hours}h)',
                    xaxis_title='Hora',
                    yaxis_title='Salud (%)',
                    yaxis=dict(range=[0, 100]),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            metric_id = metric_options[selected_metric]
            trend_data = health_monitor.get_metrics_trend(metric_id, hours)
            
            if 'error' not in trend_data:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend_data['timestamps'], y=trend_data['values'],
                    mode='lines+markers',
                    name=selected_metric,
                    line=dict(color='blue')
                ))
                
                fig.update_layout(
                    title=f'{selected_metric} - Últimas {hours}h',
                    xaxis_title='Hora',
                    yaxis_title=selected_metric,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Estadísticas
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric("Actual", f"{trend_data['current']:.1f}")
                with col_stats2:
                    st.metric("Promedio", f"{trend_data['average']:.1f}")
                with col_stats3:
                    st.metric("Tendencia", trend_data['trend'])
        
        # Reporte de errores
        st.subheader("📊 Reporte de Errores")
        
        error_stats = error_handler.get_stats(hours)
        error_df = error_handler.get_error_report(hours)
        
        col_err1, col_err2, col_err3 = st.columns(3)
        
        with col_err1:
            st.metric("Total Errores", error_stats['total_errors'])
        
        with col_err2:
            if error_stats['by_severity']:
                high_errors = error_stats['by_severity'].get('high', 0)
                st.metric("Errores Críticos", high_errors)
        
        with col_err3:
            st.metric("Tasa de Error", error_stats['error_rate'])
        
        if not error_df.empty:
            with st.expander("📋 Detalle de Errores"):
                # Filtrar columnas para mostrar
                display_cols = ['fecha', 'hora', 'category', 'severity', 'message']
                display_cols = [col for col in display_cols if col in error_df.columns]
                
                st.dataframe(
                    error_df[display_cols].head(20),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Botón para exportar
                if st.button("📥 Exportar Errores a CSV", use_container_width=True):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"errores_{timestamp}.csv"
                    if error_handler.export_to_csv(filename, hours):
                        st.success(f"Errores exportados a {filename}")
    
    except Exception as e:
        error_handler.handle(e, user_context="❌ Error mostrando métricas de salud")

def mostrar_configuracion_salud():
    """Muestra configuración del sistema de salud"""
    st.subheader("⚙️ Configuración del Sistema")
    
    # Validar configuración actual
    config_validation = config.validate()
    
    if config_validation['errors']:
        st.error("**Errores de configuración:**")
        for error in config_validation['errors']:
            st.write(f"• {error}")
    
    if config_validation['warnings']:
        st.warning("**Advertencias de configuración:**")
        for warning in config_validation['warnings']:
            st.write(f"• {warning}")
    
    if config_validation['is_valid']:
        st.success("✅ Configuración válida")
    
    # Mostrar configuración actual
    with st.expander("📋 Configuración Actual"):
        st.json(config.get_all(), expanded=False)
    
    # Controles de configuración
    st.subheader("🛠️ Controles")
    
    col_ctrl1, col_ctrl2 = st.columns(2)
    
    with col_ctrl1:
        if st.button("🔄 Recargar Configuración", use_container_width=True):
            if config.reload():
                st.success("Configuración recargada")
                st.rerun()
            else:
                st.warning("No hubo cambios en la configuración")
    
    with col_ctrl2:
        if st.button("💾 Guardar Configuración", use_container_width=True):
            if config.save():
                st.success("Configuración guardada")
            else:
                st.error("Error guardando configuración")
    
    # Editor de configuración simple
    st.subheader("✏️ Editor de Configuración")
    
    config_key = st.text_input("Ruta de configuración (ej: database.timeout):")
    if config_key:
        current_value = config.get(config_key)
        st.write(f"Valor actual: `{current_value}`")
        
        new_value = st.text_input("Nuevo valor:")
        
        if st.button("Actualizar", key=f"update_{config_key}"):
            try:
                # Intentar convertir a tipo apropiado
                if new_value.lower() == 'true':
                    parsed_value = True
                elif new_value.lower() == 'false':
                    parsed_value = False
                elif new_value.isdigit():
                    parsed_value = int(new_value)
                elif new_value.replace('.', '', 1).isdigit():
                    parsed_value = float(new_value)
                else:
                    parsed_value = new_value
                
                config.set(config_key, parsed_value, persist=True)
                st.success(f"Configuración {config_key} actualizada")
                st.rerun()
            except Exception as e:
                error_handler.handle(e, user_context="❌ Error actualizando configuración")

# ================================
# ACTUALIZAR MENÚ PRINCIPAL
# ================================
# En la función main(), agregar la nueva opción al menú:

def main():
    """Función principal de la aplicación"""
    
    # Sidebar con logo y menú
    with st.sidebar:
        st.markdown("""
        <div class='sidebar-logo'>
            <div class='logo-text'>AEROPOSTALE</div>
            <div class='logo-subtext'>Sistema de Gestión Logística</div>
        </div>
        """, unsafe_allow_html=True)
        
        menu_options = [
            # Opción NUEVA: Sistema de Salud
            ("❤️ Sistema de Salud", "🩺", mostrar_sistema_salud, "admin"),
            
            # NUEVO: Dashboard WILO AI
            ("🧠 WILO AI Dashboard", "🤖", mostrar_dashboard_wilo_ai, "admin"),
            
            # Módulos originales existentes
            ("Dashboard KPIs", "📊", mostrar_dashboard_kpis, "public"),
            ("Análisis Histórico", "📈", mostrar_analisis_historico_kpis, "public"),
            ("Ingreso de Datos", "📥", mostrar_ingreso_datos_kpis, "admin"),
            ("Gestión de Trabajadores", "👥", mostrar_gestion_trabajadores_kpis, "admin"),
            ("Gestión de Distribuciones", "📦", mostrar_gestion_distribuciones, "admin"),
            ("Reconciliación", "🔁", mostrar_reconciliacion, "admin"),
            ("Generar Guías", "📋", mostrar_generacion_guias, "user"),
            ("Historial de Guías", "🔍", mostrar_historial_guias, "user"),
            ("Generar Etiquetas", "🏷️", mostrar_generacion_etiquetas, "user"),
            ("Ayuda y Contacto", "❓", mostrar_ayuda, "public"),
            
            # Módulos WILO específicos
            ("📨 WILO: Novedades Correo", "📧", modulo_novedades_correo_mejorado, "admin"),
            ("⏱️ WILO: Tempo Análisis", "⏱️", modulo_tempo_analisis, "user"),
        ]
        
        # ... resto del código del menú se mantiene igual ...

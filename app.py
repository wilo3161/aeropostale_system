# app.py - INTEGRACIÓN COMPLETA DE MÓDULOS FASE 2

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
# IMPORTAR TODOS LOS MÓDULOS
# ================================
from modules import (
    get_config,
    get_error_handler,
    get_health_monitor,
    get_database,
    get_cache_manager,
    get_backup_system,
    cached,
    error_handler_decorator,
    init_health_monitoring
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

# Base de datos optimizada
db = get_database()

# Gestor de caché
cache_manager = get_cache_manager()

# Sistema de backup
backup_system = get_backup_system()

# ================================
# VARIABLES DE CONFIGURACIÓN
# ================================
SUPABASE_URL = config.get('database.url')
SUPABASE_KEY = config.get('database.key')
ADMIN_PASSWORD = config.get('security.admin_password')
USER_PASSWORD = config.get('security.user_password')

# Directorios desde configuración
APP_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(APP_DIR, config.get('paths.images_dir', 'images'))
os.makedirs(IMAGES_DIR, exist_ok=True)

# Configuración de WILO AI
WILO_DATA_FOLDER = Path(config.get('paths.data_dir', 'data_wilo'))
WILO_DATA_FOLDER.mkdir(exist_ok=True)
NOVEDADES_DB = WILO_DATA_FOLDER / "novedades_database.json"
CONFIG_EMAIL_FILE = WILO_DATA_FOLDER / "email_config.json"
CONFIG_GEMINI_FILE = WILO_DATA_FOLDER / "gemini_config.json"

# ================================
# REEMPLAZAR FUNCIONES DE BASE DE DATOS
# ================================
# Todas las funciones que usaban supabase directamente ahora usarán 'db'

# Ejemplo de reemplazo:
# OLD: obtener_trabajadores() -> supabase.from_('trabajadores')...
# NEW: db.obtener_trabajadores()

# ================================
# FUNCIONES OPTIMIZADAS CON CACHÉ
# ================================
@cached(ttl=300, tags=['kpis', 'dashboard'])
def obtener_trabajadores_cached() -> pd.DataFrame:
    """Obtiene trabajadores con caché"""
    return db.obtener_trabajadores()

@cached(ttl=600, tags=['kpis', 'historico'])
def cargar_historico_kpis_cached(fecha_inicio: str = None, fecha_fin: str = None, 
                                 trabajador: str = None) -> pd.DataFrame:
    """Carga histórico con caché"""
    return db.cargar_historico_kpis(fecha_inicio, fecha_fin, trabajador)

@cached(ttl=300, tags=['distribuciones'])
def obtener_distribuciones_semana_cached(fecha_inicio_semana: str) -> Dict:
    """Obtiene distribuciones con caché"""
    return db.obtener_distribuciones_semana(fecha_inicio_semana)

@cached(ttl=300, tags=['guias'])
def obtener_historial_guias_cached(limit: int = 100) -> pd.DataFrame:
    """Obtiene historial de guías con caché"""
    return db.obtener_historial_guias(limit)

# ================================
# NUEVA SECCIÓN: SISTEMA DE BACKUP
# ================================
def mostrar_sistema_backup():
    """Muestra el dashboard del sistema de backup"""
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>💾 Sistema de Backup</h1><div class='header-subtitle'>Respaldo y restauración de datos</div></div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Estado", "🔄 Operaciones", "⚙️ Configuración"])
    
    with tab1:
        mostrar_estado_backup()
    
    with tab2:
        mostrar_operaciones_backup()
    
    with tab3:
        mostrar_configuracion_backup()

def mostrar_estado_backup():
    """Muestra el estado del sistema de backup"""
    try:
        # Estadísticas
        stats = backup_system.get_backup_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Backups", stats['total_backups'])
        
        with col2:
            st.metric("Espacio Usado", f"{stats['total_size_gb']:.2f} GB")
        
        with col3:
            if stats['newest_backup']:
                newest = datetime.fromisoformat(stats['newest_backup'])
                st.metric("Más Reciente", newest.strftime("%d/%m %H:%M"))
        
        with col4:
            st.metric("Retención", f"{stats['retention_days']} días")
        
        # Lista de backups
        st.subheader("📋 Backups Disponibles")
        backups = backup_system.list_backups()
        
        if backups:
            # Crear DataFrame para visualización
            backup_data = []
            for backup in backups[:10]:  # Mostrar solo los 10 más recientes
                created = datetime.fromisoformat(backup['created'])
                backup_data.append({
                    'Nombre': backup['filename'],
                    'Tipo': backup['type'],
                    'Tamaño (MB)': f"{backup['size_mb']:.1f}",
                    'Creado': created.strftime("%Y-%m-%d %H:%M"),
                    'Descripción': backup['description'][:50] + '...' if len(backup['description']) > 50 else backup['description']
                })
            
            df_backups = pd.DataFrame(backup_data)
            st.dataframe(df_backups, use_container_width=True, hide_index=True)
            
            # Mostrar más detalles
            with st.expander("📊 Estadísticas por Tipo"):
                if stats['by_type']:
                    for backup_type, type_stats in stats['by_type'].items():
                        st.write(f"**{backup_type}**: {type_stats['count']} backups ({type_stats['total_size_mb']:.1f} MB)")
        else:
            st.info("ℹ️ No hay backups disponibles")
        
        # Espacio en disco
        st.subheader("💾 Espacio en Disco")
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            col_disk1, col_disk2, col_disk3 = st.columns(3)
            
            with col_disk1:
                st.metric("Total", f"{total / (1024**3):.1f} GB")
            
            with col_disk2:
                st.metric("Usado", f"{used / (1024**3):.1f} GB")
            
            with col_disk3:
                st.metric("Libre", f"{free / (1024**3):.1f} GB")
            
            # Barra de progreso
            usage_percent = (used / total) * 100
            st.progress(usage_percent / 100, text=f"Uso de disco: {usage_percent:.1f}%")
            
            if usage_percent > 90:
                st.error("⚠️ Disco casi lleno. Considere limpiar backups antiguos.")
            elif usage_percent > 80:
                st.warning("⚠️ Uso de disco elevado.")
        
        except Exception as e:
            error_handler.handle(e, user_context="Error obteniendo información de disco")
    
    except Exception as e:
        error_handler.handle(e, user_context="Error mostrando estado de backup")

def mostrar_operaciones_backup():
    """Muestra operaciones de backup/restore"""
    st.subheader("🔄 Operaciones de Backup")
    
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        # Crear backup manual
        st.markdown("#### 📥 Crear Backup")
        
        backup_type = st.selectbox("Tipo de backup:", 
                                  ["full", "incremental", "database_only"],
                                  key="backup_type_select")
        
        description = st.text_input("Descripción (opcional):", 
                                   key="backup_description")
        
        if st.button("🚀 Crear Backup Ahora", use_container_width=True):
            with st.spinner("Creando backup..."):
                backup_file = backup_system.create_backup(backup_type, description)
                
                if backup_file:
                    st.success(f"✅ Backup creado: {backup_file.name}")
                    
                    # Mostrar detalles
                    with st.expander("📋 Detalles del Backup"):
                        st.write(f"**Archivo:** {backup_file.name}")
                        st.write(f"**Tamaño:** {backup_file.stat().st_size / (1024*1024):.2f} MB")
                        st.write(f"**Ruta:** {backup_file}")
                        
                        # Botón para descargar
                        with open(backup_file, 'rb') as f:
                            st.download_button(
                                label="⬇️ Descargar Backup",
                                data=f,
                                file_name=backup_file.name,
                                mime="application/zip",
                                use_container_width=True
                            )
                else:
                    st.error("❌ Error creando backup")
    
    with col_op2:
        # Restaurar backup
        st.markdown("#### 📤 Restaurar Backup")
        
        backups = backup_system.list_backups()
        if backups:
            backup_options = {b['filename']: b for b in backups}
            selected_backup = st.selectbox("Seleccionar backup:", 
                                          list(backup_options.keys()),
                                          key="restore_backup_select")
            
            restore_type = st.selectbox("Tipo de restauración:",
                                       ["full", "database_only", "configs_only"],
                                       key="restore_type_select")
            
            st.warning("⚠️ **ADVERTENCIA:** La restauración sobrescribirá datos existentes.")
            
            if st.button("🔙 Restaurar Backup", type="secondary", use_container_width=True):
                confirm = st.checkbox("Confirmo que deseo restaurar este backup")
                
                if confirm:
                    backup_info = backup_options[selected_backup]
                    
                    with st.spinner(f"Restaurando {selected_backup}..."):
                        success = backup_system.restore_backup(backup_info['path'], restore_type)
                        
                        if success:
                            st.success("✅ Backup restaurado exitosamente")
                            st.info("ℹ️ Es posible que necesite reiniciar la aplicación para ver los cambios.")
                        else:
                            st.error("❌ Error restaurando backup")
                else:
                    st.info("Por favor, confirme la restauración marcando la casilla.")
        else:
            st.info("No hay backups disponibles para restaurar")
    
    # Limpieza manual
    st.subheader("🧹 Limpieza de Backups")
    
    col_clean1, col_clean2 = st.columns(2)
    
    with col_clean1:
        if st.button("🗑️ Limpiar Backups Antiguos", use_container_width=True):
            with st.spinner("Limpiando backups antiguos..."):
                backup_system._clean_old_backups()
                st.success("✅ Backups antiguos limpiados")
                st.rerun()
    
    with col_clean2:
        if st.button("🧪 Probar Sistema de Backup", use_container_width=True):
            with st.spinner("Probando sistema de backup..."):
                # Crear backup de prueba pequeño
                test_file = backup_system.create_backup("database_only", "test_system")
                if test_file:
                    st.success("✅ Sistema de backup funcionando correctamente")
                    
                    # Eliminar backup de prueba
                    test_file.unlink(missing_ok=True)
                else:
                    st.error("❌ Error en sistema de backup")

def mostrar_configuracion_backup():
    """Muestra configuración del sistema de backup"""
    st.subheader("⚙️ Configuración de Backup")
    
    # Configuración actual
    with st.expander("📋 Configuración Actual"):
        st.json(backup_system.backup_config, expanded=False)
    
    # Programar backup automático
    st.markdown("#### 📅 Programar Backup Automático")
    
    col_sched1, col_sched2 = st.columns(2)
    
    with col_sched1:
        auto_hour = st.slider("Hora del día:", 0, 23, 2,
                             help="Hora en la que se ejecutará el backup automático (24h)")
    
    with col_sched2:
        auto_type = st.selectbox("Tipo automático:", 
                                ["full", "incremental", "database_only"],
                                help="Tipo de backup que se creará automáticamente")
    
    if st.button("💾 Programar Backup Automático", use_container_width=True):
        backup_system.schedule_backup(auto_hour, auto_type)
        st.success(f"✅ Backup automático programado para las {auto_hour:02d}:00")
    
    # Configuración de retención
    st.markdown("#### ⏱️ Configuración de Retención")
    
    col_ret1, col_ret2 = st.columns(2)
    
    with col_ret1:
        retention_days = st.number_input("Días de retención:", 
                                        min_value=1, max_value=365, 
                                        value=backup_system.retention_days)
    
    with col_ret2:
        max_backups = st.number_input("Máximo de backups:", 
                                     min_value=1, max_value=100,
                                     value=backup_system.max_backups)
    
    if st.button("🔄 Actualizar Configuración", use_container_width=True):
        backup_system.retention_days = retention_days
        backup_system.max_backups = max_backups
        st.success("✅ Configuración actualizada")

# ================================
# NUEVA SECCIÓN: SISTEMA DE CACHÉ
# ================================
def mostrar_sistema_cache():
    """Muestra el dashboard del sistema de caché"""
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>⚡ Sistema de Caché</h1><div class='header-subtitle'>Optimización y rendimiento</div></div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Estado", "🔍 Contenido", "⚙️ Configuración"])
    
    with tab1:
        mostrar_estado_cache()
    
    with tab2:
        mostrar_contenido_cache()
    
    with tab3:
        mostrar_configuracion_cache()

def mostrar_estado_cache():
    """Muestra el estado del sistema de caché"""
    try:
        # Estadísticas globales
        global_stats = cache_manager.get_global_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Namespaces", global_stats['total_namespaces'])
        
        with col2:
            st.metric("Entradas Totales", global_stats['total_entries'])
        
        with col3:
            st.metric("Hit Rate Global", global_stats['global_hit_rate'])
        
        with col4:
            # Uso de memoria estimado
            total_memory = 0
            for namespace_stats in global_stats['namespaces'].values():
                memory_str = namespace_stats.get('memory_usage', '0 B')
                if 'KB' in memory_str:
                    total_memory += float(memory_str.replace(' KB', '')) * 1024
                elif 'MB' in memory_str:
                    total_memory += float(memory_str.replace(' MB', '')) * 1024 * 1024
                elif 'B' in memory_str:
                    total_memory += float(memory_str.replace(' B', ''))
            
            if total_memory < 1024:
                memory_display = f"{total_memory:.0f} B"
            elif total_memory < 1024 * 1024:
                memory_display = f"{total_memory / 1024:.1f} KB"
            else:
                memory_display = f"{total_memory / (1024 * 1024):.1f} MB"
            
            st.metric("Uso de Memoria", memory_display)
        
        # Gráfico de eficiencia por namespace
        st.subheader("📈 Eficiencia por Namespace")
        
        if global_stats['namespaces']:
            namespaces = list(global_stats['namespaces'].keys())
            hit_rates = []
            
            for namespace in namespaces:
                stats = global_stats['namespaces'][namespace]
                total = stats['hits'] + stats['misses']
                hit_rate = (stats['hits'] / total * 100) if total > 0 else 0
                hit_rates.append(hit_rate)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=namespaces,
                    y=hit_rates,
                    text=[f"{rate:.1f}%" for rate in hit_rates],
                    textposition='auto',
                    marker_color=['green' if rate > 70 else 'orange' if rate > 40 else 'red' for rate in hit_rates]
                )
            ])
            
            fig.update_layout(
                title='Hit Rate por Namespace',
                xaxis_title='Namespace',
                yaxis_title='Hit Rate (%)',
                yaxis=dict(range=[0, 100])
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Estadísticas detalladas por namespace
        st.subheader("📋 Estadísticas Detalladas")
        
        for namespace, stats in global_stats['namespaces'].items():
            with st.expander(f"📁 {namespace}"):
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                with col_stat1:
                    st.metric("Hits", stats['hits'])
                    st.metric("Misses", stats['misses'])
                
                with col_stat2:
                    st.metric("Tasa de Acierto", stats['hit_rate'])
                    st.metric("Eficiencia", stats['efficiency'])
                
                with col_stat3:
                    st.metric("Tamaño", stats['size'])
                    st.metric("Memoria", stats['memory_usage'])
    
    except Exception as e:
        error_handler.handle(e, user_context="Error mostrando estado de caché")

def mostrar_contenido_cache():
    """Muestra el contenido del caché"""
    st.subheader("🔍 Explorar Contenido del Caché")
    
    # Seleccionar namespace
    global_stats = cache_manager.get_global_stats()
    namespaces = list(global_stats['namespaces'].keys())
    
    if not namespaces:
        st.info("No hay namespaces de caché disponibles")
        return
    
    selected_namespace = st.selectbox("Seleccionar namespace:", namespaces)
    cache_instance = cache_manager.get_namespace(selected_namespace)
    
    # Buscar en caché
    search_term = st.text_input("🔎 Buscar por clave o patrón:", 
                               placeholder="Ej: kpis_*, *trabajadores*")
    
    if search_term:
        keys = [k for k in cache_instance.get_keys() if search_term in k]
    else:
        keys = cache_instance.get_keys()
    
    if keys:
        st.write(f"**{len(keys)} entradas encontradas**")
        
        # Paginación
        items_per_page = 20
        total_pages = (len(keys) + items_per_page - 1) // items_per_page
        page = st.number_input("Página:", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(keys))
        
        # Mostrar entradas de la página actual
        for i in range(start_idx, end_idx):
            key = keys[i]
            entry = cache_instance.cache.get(key)
            
            if entry:
                with st.expander(f"🔑 {key[:50]}..." if len(key) > 50 else f"🔑 {key}"):
                    col_entry1, col_entry2 = st.columns(2)
                    
                    with col_entry1:
                        st.write(f"**Clave:** `{key}`")
                        st.write(f"**Creado:** {entry.created_at.strftime('%H:%M:%S')}")
                        st.write(f"**Último acceso:** {entry.last_accessed.strftime('%H:%M:%S')}")
                        st.write(f"**Accesos:** {entry.access_count}")
                    
                    with col_entry2:
                        st.write(f"**TTL:** {entry.ttl}s")
                        st.write(f"**Expira en:** {entry.ttl - (datetime.now() - entry.created_at).total_seconds():.0f}s")
                        st.write(f"**Etiquetas:** {', '.join(entry.tags) if entry.tags else 'Ninguna'}")
                        
                        # Previsualización del valor
                        st.write("**Valor (preview):**")
                        value_preview = str(entry.value)
                        if len(value_preview) > 200:
                            st.text(value_preview[:200] + "...")
                        else:
                            st.text(value_preview)
                    
                    # Botones de acción
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button("🗑️ Invalidar", key=f"invalidate_{key}", use_container_width=True):
                            cache_instance.invalidate(key)
                            st.success("✅ Entrada invalidada")
                            st.rerun()
                    
                    with col_act2:
                        if st.button("📋 Ver Completo", key=f"view_{key}", use_container_width=True):
                            st.json(entry.value, expanded=True)
        
        # Controles de paginación
        if total_pages > 1:
            st.write(f"Página {page} de {total_pages}")
    else:
        st.info("No se encontraron entradas en el caché")

def mostrar_configuracion_cache():
    """Muestra configuración del sistema de caché"""
    st.subheader("⚙️ Configuración del Caché")
    
    # Estadísticas de la base de datos
    st.markdown("#### 🗄️ Estadísticas de Base de Datos")
    try:
        db_stats = db.orm.get_stats()
        
        col_db1, col_db2, col_db3 = st.columns(3)
        
        with col_db1:
            st.metric("Consultas Totales", db_stats['total_queries'])
            st.metric("Fallos", db_stats['failed_queries'])
        
        with col_db2:
            st.metric("Hit Rate DB", db_stats['cache_hit_rate'])
            st.metric("Tiempo Respuesta", f"{db_stats['avg_response_time']:.2f}s")
        
        with col_db3:
            st.metric("Tamaño Caché DB", db_stats['cache_size'])
            st.metric("Conexiones Activas", db_stats['connections_in_use'])
    
    except Exception as e:
        error_handler.handle(e, user_context="Error obteniendo estadísticas de DB")
    
    # Controles de caché
    st.markdown("#### 🎛️ Controles de Caché")
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    
    with col_ctrl1:
        if st.button("🔄 Refrescar Caché DB", use_container_width=True):
            db.orm.clear_cache()
            st.success("✅ Caché de base de datos refrescado")
    
    with col_ctrl2:
        if st.button("🗑️ Limpiar Todo el Caché", use_container_width=True):
            cache_manager.cache.clear()
            for namespace in cache_manager.namespaces.values():
                namespace.clear()
            st.success("✅ Todo el caché limpiado")
    
    with col_ctrl3:
        invalidate_tag = st.text_input("Invalidar por etiqueta:", placeholder="Ej: kpis")
        if st.button("🏷️ Invalidar por Etiqueta", use_container_width=True):
            if invalidate_tag:
                invalidated_count = 0
                for namespace in cache_manager.namespaces.values():
                    invalidated_count += namespace.invalidate_by_tag(invalidate_tag)
                st.success(f"✅ Invalidadas {invalidated_count} entradas con tag '{invalidate_tag}'")
    
    # Configuración de invalidación automática
    st.markdown("#### ⚡ Invalidación Automática")
    
    auto_invalidate = st.checkbox("Invalidar caché automáticamente al guardar datos", value=True)
    
    if auto_invalidate:
        st.info("ℹ️ El caché se invalidará automáticamente cuando se modifiquen datos.")
    
    # Monitoreo en tiempo real
    st.markdown("#### 📊 Monitoreo en Tiempo Real")
    
    if st.button("📈 Actualizar Métricas", use_container_width=True):
        st.rerun()

# ================================
# ACTUALIZAR FUNCIONES EXISTENTES PARA USAR NUEVOS MÓDULOS
# ================================

# Reemplazar todas las llamadas a funciones antiguas por las nuevas:

def mostrar_dashboard_kpis():
    """Muestra el dashboard principal con KPIs (OPTIMIZADO)"""
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>📊 Dashboard de KPIs Aeropostale</h1><div class='header-subtitle'>Control Logístico en Tiempo Real</div></div>", unsafe_allow_html=True)
    
    # Usar base de datos optimizada
    if 'historico_data' not in st.session_state:
        with st.spinner("Cargando datos históricos..."):
            # Usar función con caché
            st.session_state.historico_data = cargar_historico_kpis_cached()
    
    df = st.session_state.historico_data
    # ... resto del código igual pero usando db en lugar de supabase directo ...

def mostrar_ingreso_datos_kpis():
    """Muestra la interfaz para ingresar datos de KPIs (OPTIMIZADO)"""
    if not verificar_password("admin"):
        solicitar_autenticacion("admin")
        return
    
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>📥 Ingreso de Datos de KPIs</h1><div class='header-subtitle'>Registro diario de producción</div></div>", unsafe_allow_html=True)
    
    # Usar base de datos optimizada
    df_trabajadores = obtener_trabajadores_cached()
    # ... resto del código usando db.guardar_datos_kpis() ...

def mostrar_gestion_distribuciones():
    """Muestra la interfaz para gestionar distribuciones semanales (OPTIMIZADO)"""
    if not verificar_password("admin"):
        solicitar_autenticacion("admin")
        return
    
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>📊 Gestión de Distribuciones Semanales</h1></div>", unsafe_allow_html=True)
    
    # Usar funciones optimizadas
    fecha_inicio_semana_str = (datetime.now().date() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
    distribuciones_existentes = obtener_distribuciones_semana_cached(fecha_inicio_semana_str)
    
    # ... resto del código usando db.guardar_distribuciones_semanales() ...

def mostrar_generacion_guias():
    """Muestra la interfaz para generar guías de envío (OPTIMIZADO)"""
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>📦 Generación de Guías de Envío</h1><div class='header-subtitle'>Sistema de etiquetado logístico</div></div>", unsafe_allow_html=True)
    
    # Usar funciones optimizadas
    tiendas = db.obtener_tiendas()  # Necesitaríamos agregar esta función a AeropostaleDB
    # ... resto del código usando db.guardar_guia() ...

def mostrar_historial_guias():
    """Muestra el historial de guías generadas (OPTIMIZADO)"""
    if not verificar_password("user"):
        if st.session_state.user_type is None:
            solicitar_autenticacion("user")
        return
    
    st.markdown("<div class='dashboard-header'><h1 class='header-title'>🔍 Historial de Guías de Envío</h1><div class='header-subtitle'>Registro y seguimiento de envíos</div></div>", unsafe_allow_html=True)
    
    # Usar función con caché
    df_guias = obtener_historial_guias_cached(limit=1000)
    # ... resto del código usando db.eliminar_guia() ...

# ================================
# ACTUALIZAR MENÚ PRINCIPAL
# ================================
def main():
    """Función principal de la aplicación"""
    
    # Sidebar con logo y menú
    with st.sidebar:
        st.markdown("""
        <div class='sidebar-logo'>
            <div class='logo-text'>AEROPOSTALE</div>
            <div class='logo-subtext'>Sistema de Gestión Logística v2.0</div>
        </div>
        """, unsafe_allow_html=True)
        
        menu_options = [
            # Nuevos módulos de Fase 2
            ("💾 Sistema de Backup", "💾", mostrar_sistema_backup, "admin"),
            ("⚡ Sistema de Caché", "⚡", mostrar_sistema_cache, "admin"),
            
            # Módulos de Fase 1
            ("❤️ Sistema de Salud", "🩺", mostrar_sistema_salud, "admin"),
            
            # Dashboard WILO AI
            ("🧠 WILO AI Dashboard", "🤖", mostrar_dashboard_wilo_ai, "admin"),
            
            # Módulos originales existentes (optimizados)
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
        
        # Mostrar opciones del menú según permisos
        for i, (label, icon, _, permiso) in enumerate(menu_options):
            mostrar_opcion = False
            
            if permiso == "public":
                mostrar_opcion = True
            elif permiso == "user" and st.session_state.user_type in ["user", "admin"]:
                mostrar_opcion = True
            elif permiso == "admin" and st.session_state.user_type == "admin":
                mostrar_opcion = True
            
            if mostrar_opcion:
                selected = st.button(
                    f"{icon} {label}",
                    key=f"menu_{i}",
                    use_container_width=True
                )
                if selected:
                    st.session_state.selected_menu = i
        
        # Botones de autenticación
        st.markdown("---")
        if st.session_state.user_type is None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👤 Acceso Usuario", use_container_width=True):
                    st.session_state.show_login = True
                    st.session_state.login_type = "user"
            with col2:
                if st.button("🔧 Acceso Admin", use_container_width=True):
                    st.session_state.show_login = True
                    st.session_state.login_type = "admin"
        else:
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                st.session_state.user_type = None
                st.session_state.password_correct = False
                st.session_state.selected_menu = 0
                st.session_state.show_login = False
                st.rerun()
            
            tipo_usuario = "Administrador" if st.session_state.user_type == "admin" else "Usuario"
            st.markdown(f"""
            <div class="alert-banner alert-info" style="margin-top: 20px;">
                <strong>👤 Usuario:</strong> {tipo_usuario}
            </div>
            """, unsafe_allow_html=True)
    
    # Mostrar formulario de autenticación si es necesario
    if st.session_state.get('show_login', False):
        solicitar_autenticacion(st.session_state.get('login_type', 'user'))
        return
    
    # Verificar que selected_menu esté dentro del rango válido
    if st.session_state.selected_menu >= len(menu_options):
        st.session_state.selected_menu = 0
    
    # Obtener y ejecutar la función seleccionada
    label, icon, func, permiso = menu_options[st.session_state.selected_menu]
    
    if permiso == "public":
        func()
    elif permiso == "user" and st.session_state.user_type in ["user", "admin"]:
        func()
    elif permiso == "admin" and st.session_state.user_type == "admin":
        func()
    else:
        if not st.session_state.get('show_login', False):
            st.error("🔒 Acceso restringido. Necesita autenticarse para acceder a esta sección.")
        
        if permiso == "admin" and not st.session_state.get('show_login', False):
            st.session_state.show_login = True
            st.session_state.login_type = "admin"
            st.rerun()
        elif not st.session_state.get('show_login', False):
            st.session_state.show_login = True
            st.session_state.login_type = "user"
            st.rerun()
    
    # Footer
    st.markdown("""
    <div class="footer">
        Sistema de KPIs Aeropostale v2.0 | © 2025 Aeropostale. Todos los derechos reservados.<br>
        Desarrollado por: <a href="mailto:wilson.perez@aeropostale.com" class="footer-link">Wilson Pérez</a>
    </div>
    """, unsafe_allow_html=True)

# ================================
# INICIALIZACIÓN DE SISTEMAS EN SEGUNDO PLANO
# ================================
def init_background_systems():
    """Inicializa sistemas que corren en segundo plano"""
    try:
        # ... (código anterior) ...
        
        # Inicializar WILO AI si está habilitado
        config = get_config()
        if config.get('features.wilo_ai_enabled', True):
            wilo_ai = get_wilo_ai_manager()
            if wilo_ai.initialize():
                wilo_ai.start_background_monitoring()
                logger.info("✅ WILO AI iniciado en segundo plano")
            else:
                logger.warning("⚠️ No se pudo inicializar WILO AI")
        
        # Programar backup automático (solo si está habilitado)
        config = get_config()
        if config.get('features.auto_backup', True):
            backup_system.schedule_backup(hour=2, backup_type="incremental")
            logger.info("✅ Backup automático programado")
        
        # Iniciar limpieza periódica de caché
        def cache_cleanup():
            while True:
                time.sleep(3600)  # Cada hora
                try:
                    # Limpiar caché de funciones que no se han usado en 24h
                    cache_manager.cache._cleanup_expired()
                    logger.debug("Limpieza periódica de caché ejecutada")
                except Exception as e:
                    logger.error(f"Error en limpieza de caché: {e}")
        
        cleanup_thread = threading.Thread(target=cache_cleanup, daemon=True)
        cleanup_thread.start()
        
    except Exception as e:
        error_handler.handle(e, user_context="Error inicializando sistemas en segundo plano")

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == "__main__":
    try:
        # Inicializar sistemas en segundo plano
        init_background_systems()
        
        # Ejecutar aplicación principal
        main()
        
    except Exception as e:
        st.error(f"Error crítico en la aplicación: {e}")
        logger.error(f"Error en main: {e}", exc_info=True)
        
        # Intentar crear un backup de emergencia
        try:
            emergency_backup = backup_system.create_backup(
                "full", 
                f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if emergency_backup:
                logger.info(f"Backup de emergencia creado: {emergency_backup}")
        except:
            logger.error("No se pudo crear backup de emergencia")

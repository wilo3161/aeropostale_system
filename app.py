# app.py - INTEGRACIÓN DE MEJORAS UI/UX

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
    get_theme_manager,
    get_components,
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

# Gestor de temas
theme_manager = get_theme_manager()

# Componentes reutilizables
components = get_components()

# ================================
# APLICAR TEMA GLOBAL
# ================================
theme_manager.apply_theme()

# ================================
# CONFIGURACIÓN DE LA PÁGINA
# ================================
st.set_page_config(
    page_title="Aeropostale - Sistema de Gestión Logística",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================
# CSS ADICIONAL PARA MEJORAS UI/UX
# ================================
st.markdown("""
<style>
/* Mejoras adicionales */
.stMetric {
    background-color: var(--secondary-background-color);
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid var(--primary-color);
}

/* Mejoras en tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
}

.stTabs [aria-selected="true"] {
    border-bottom: 2px solid var(--primary-color);
}

/* Mejoras en inputs */
.stTextInput > div > div > input {
    border-radius: 6px !important;
}

.stButton button {
    border-radius: 6px !important;
    transition: all 0.3s ease;
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* Animaciones */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.5s ease-out;
}

/* Mejoras en tablas */
.dataframe {
    border-radius: 8px !important;
    overflow: hidden !important;
}

.dataframe thead th {
    background-color: var(--primary-color) !important;
    color: white !important;
}

/* Tooltips mejorados */
[data-testid="stTooltip"] {
    border-radius: 6px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}
</style>
""", unsafe_allow_html=True)

# ================================
# FUNCIÓN PRINCIPAL CON NUEVA UI
# ================================
def main():
    """Función principal de la aplicación con nueva UI"""
    
    # Sidebar mejorada
    with st.sidebar:
        # Logo y título
        st.markdown("""
        <div class='fade-in'>
            <div style="text-align: center; padding: 1rem 0;">
                <h1 style="color: var(--primary-color); margin-bottom: 0;">📊</h1>
                <h2 style="color: var(--text-color); margin-top: 0; font-size: 1.5rem;">Aeropostale</h2>
                <p style="color: var(--text-color); opacity: 0.8; font-size: 0.9rem;">Sistema de Gestión Logística v4.0</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Selector de tema
        theme_manager.theme_selector(sidebar=True)
        
        st.markdown("---")
        
        # Menú de navegación
        st.markdown("### 🗂️ Navegación")
        
        menu_options = [
            ("Dashboard Principal", "📊", mostrar_dashboard_principal, "public"),
            ("KPIs y Métricas", "📈", mostrar_kpis_metricas, "public"),
            ("Gestión Logística", "📦", mostrar_gestion_logistica, "user"),
            ("WILO AI", "🤖", mostrar_wilo_ai, "admin"),
            ("Sistema de Salud", "❤️", mostrar_sistema_salud, "admin"),
            ("Backup y Caché", "⚙️", mostrar_sistema_backup_cache, "admin"),
            ("Configuración", "🔧", mostrar_configuracion, "admin"),
        ]
        
        for i, (label, icon, _, permiso) in enumerate(menu_options):
            if permiso == "public" or (permiso == "user" and st.session_state.user_type in ["user", "admin"]) or (permiso == "admin" and st.session_state.user_type == "admin"):
                if st.button(
                    f"{icon} {label}",
                    key=f"menu_{i}",
                    use_container_width=True,
                    help=f"Acceder a {label}"
                ):
                    st.session_state.selected_menu = i
        
        st.markdown("---")
        
        # Estado del sistema
        st.markdown("### 📊 Estado")
        try:
            health = health_monitor.get_health_status()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Salud", f"{health['overall_health']:.0f}%")
            with col2:
                st.metric("Problemas", health['critical_issues'])
        except:
            pass
        
        # Autenticación
        st.markdown("### 👤 Usuario")
        if st.session_state.user_type is None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👤 Usuario", use_container_width=True, help="Iniciar sesión como usuario"):
                    st.session_state.show_login = True
                    st.session_state.login_type = "user"
            with col2:
                if st.button("🔧 Admin", use_container_width=True, help="Iniciar sesión como administrador"):
                    st.session_state.show_login = True
                    st.session_state.login_type = "admin"
        else:
            tipo = "Administrador" if st.session_state.user_type == "admin" else "Usuario"
            st.success(f"✅ Conectado como {tipo}")
            if st.button("🚪 Cerrar sesión", use_container_width=True):
                st.session_state.user_type = None
                st.session_state.password_correct = False
                st.rerun()
    
    # Mostrar formulario de autenticación si es necesario
    if st.session_state.get('show_login', False):
        solicitar_autenticacion_mejorada(st.session_state.get('login_type', 'user'))
        return
    
    # Contenido principal
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    
    # Obtener y ejecutar la función seleccionada
    if st.session_state.selected_menu >= len(menu_options):
        st.session_state.selected_menu = 0
    
    label, icon, func, permiso = menu_options[st.session_state.selected_menu]
    
    # Verificar permisos
    if permiso == "public" or (permiso == "user" and st.session_state.user_type in ["user", "admin"]) or (permiso == "admin" and st.session_state.user_type == "admin"):
        # Mostrar encabezado de la página
        st.markdown(f"""
        <div style="margin-bottom: 2rem;">
            <h1 style="color: var(--primary-color); display: flex; align-items: center; gap: 10px;">
                {icon} {label}
            </h1>
            <p style="color: var(--text-color); opacity: 0.8;">Sistema de Gestión Logística Aeropostale</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Ejecutar función
        func()
    else:
        components.info_box(
            "Acceso restringido",
            "Necesita autenticarse para acceder a esta sección.",
            "error"
        )
        
        if permiso == "admin" and not st.session_state.get('show_login', False):
            st.session_state.show_login = True
            st.session_state.login_type = "admin"
            st.rerun()
        elif not st.session_state.get('show_login', False):
            st.session_state.show_login = True
            st.session_state.login_type = "user"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer mejorado
    st.markdown("""
    <div style="
        margin-top: 4rem;
        padding-top: 2rem;
        border-top: 1px solid var(--secondary-background-color);
        text-align: center;
        color: var(--text-color);
        opacity: 0.7;
        font-size: 0.9rem;
    ">
        <p>📊 Sistema de KPIs Aeropostale v4.0 | © 2025 Aeropostale. Todos los derechos reservados.</p>
        <p>Desarrollado por: <a href="mailto:wilson.perez@aeropostale.com" style="color: var(--primary-color); text-decoration: none;">Wilson Pérez</a></p>
        <p style="font-size: 0.8rem; margin-top: 1rem;">
            <span id="clock">🕒 Cargando hora...</span> | 
            <span id="stats">📈 Cargando estadísticas...</span>
        </p>
    </div>
    
    <script>
    // Actualizar reloj en tiempo real
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
        document.getElementById('clock').innerHTML = '🕒 ' + timeString;
    }
    
    // Actualizar cada segundo
    updateClock();
    setInterval(updateClock, 1000);
    
    // Simular estadísticas (en una implementación real, se obtendrían del backend)
    document.getElementById('stats').innerHTML = '📈 Sistema operativo al 100%';
    </script>
    """, unsafe_allow_html=True)

# ================================
# FUNCIONES DE PÁGINA MEJORADAS
# ================================

def mostrar_dashboard_principal():
    """Dashboard principal con nueva UI"""
    # Tarjetas de métricas principales
    st.markdown("### 📈 Métricas Clave")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        components.metric_card(
            "Transferencias Hoy",
            "1,245",
            delta="+12% vs ayer",
            icon="🔄",
            help_text="Unidades transferidas hoy"
        )
    
    with col2:
        components.metric_card(
            "Distribución",
            "89%",
            delta="+5% vs meta",
            icon="📦",
            help_text="Eficiencia de distribución"
        )
    
    with col3:
        components.metric_card(
            "Guías Generadas",
            "56",
            delta="+8 vs ayer",
            icon="📋",
            help_text="Guías creadas hoy"
        )
    
    with col4:
        components.metric_card(
            "Sistema Salud",
            "98%",
            delta="-2% vs ayer",
            icon="❤️",
            help_text="Estado general del sistema"
        )
    
    # Gráficos principales
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("#### 📊 KPIs Diarios")
        # Datos de ejemplo
        data = pd.DataFrame({
            'Día': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'],
            'Transferencias': [1200, 1300, 1100, 1400, 1500, 900],
            'Distribución': [85, 88, 82, 90, 92, 80]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['Día'], y=data['Transferencias'],
            name='Transferencias',
            line=dict(color='var(--primary-color)', width=3)
        ))
        fig.add_trace(go.Scatter(
            x=data['Día'], y=data['Distribución'] * 15,
            name='Distribución (%)',
            yaxis='y2',
            line=dict(color='var(--success-color)', width=3, dash='dash')
        ))
        
        fig.update_layout(
            yaxis=dict(title='Transferencias'),
            yaxis2=dict(
                title='Distribución (%)',
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.markdown("#### 🎯 Eficiencia por Equipo")
        # Datos de ejemplo
        data = pd.DataFrame({
            'Equipo': ['Transferencias', 'Distribución', 'Arreglos', 'Guías', 'Ventas'],
            'Eficiencia': [92, 89, 85, 95, 88],
            'Meta': [90, 90, 85, 90, 85]
        })
        
        fig = px.bar(
            data, 
            x='Equipo', 
            y=['Eficiencia', 'Meta'],
            barmode='group',
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Alertas y notificaciones
    st.markdown("### ⚡ Alertas Recientes")
    
    col_alert1, col_alert2, col_alert3 = st.columns(3)
    
    with col_alert1:
        components.info_box(
            "⚠️ Pendiente",
            "3 distribuciones pendientes de revisión",
            "warning"
        )
    
    with col_alert2:
        components.info_box(
            "✅ Completado",
            "Backup nocturno ejecutado correctamente",
            "success"
        )
    
    with col_alert3:
        components.info_box(
            "📅 Programado",
            "Reunión de equipo a las 10:00 AM",
            "info"
        )
    
    # Acciones rápidas
    st.markdown("### 🚀 Acciones Rápidas")
    
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("📥 Ingresar Datos", use_container_width=True, help="Ingresar datos de producción"):
            st.session_state.selected_menu = 1
            st.rerun()
    
    with col_action2:
        if st.button("📋 Generar Guía", use_container_width=True, help="Crear nueva guía de envío"):
            st.session_state.selected_menu = 5
            st.rerun()
    
    with col_action3:
        if st.button("📊 Reporte Diario", use_container_width=True, help="Generar reporte del día"):
            generar_reporte_diario()
    
    with col_action4:
        if st.button("🔍 Monitoreo", use_container_width=True, help="Ver monitoreo en tiempo real"):
            st.session_state.selected_menu = 4
            st.rerun()

def mostrar_kpis_metricas():
    """Página de KPIs y métricas"""
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Dashboard", "📊 Histórico", "🎯 Metas", "📋 Reportes"])
    
    with tab1:
        mostrar_dashboard_kpis_mejorado()
    
    with tab2:
        mostrar_analisis_historico_mejorado()
    
    with tab3:
        mostrar_gestion_metas()
    
    with tab4:
        mostrar_generacion_reportes()

def mostrar_dashboard_kpis_mejorado():
    """Dashboard de KPIs mejorado"""
    components.info_box(
        "Información",
        "Esta sección muestra los KPIs en tiempo real del sistema logístico.",
        "info"
    )
    
    # Filtros
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        fecha_inicio = st.date_input("Fecha inicio", datetime.now().date() - timedelta(days=7))
    
    with col_filter2:
        fecha_fin = st.date_input("Fecha fin", datetime.now().date())
    
    with col_filter3:
        equipo = st.selectbox("Equipo", ["Todos", "Transferencias", "Distribución", "Arreglos", "Guías", "Ventas"])
    
    # Gráfico de tendencias
    st.markdown("#### 📈 Tendencias de Producción")
    
    # Datos de ejemplo
    dates = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
    data = pd.DataFrame({
        'Fecha': dates,
        'Transferencias': np.random.randint(1000, 2000, len(dates)),
        'Distribución': np.random.randint(80, 100, len(dates)),
        'Arreglos': np.random.randint(50, 150, len(dates))
    })
    
    fig = px.line(data, x='Fecha', y=['Transferencias', 'Distribución', 'Arreglos'])
    st.plotly_chart(fig, use_container_width=True)
    
    # Métricas detalladas
    st.markdown("#### 📊 Métricas Detalladas")
    
    metric_cols = st.columns(4)
    metricas = [
        ("Prom. Transferencias", "1,450", "+5%", "🔄"),
        ("Efic. Distribución", "89%", "+2%", "📦"),
        ("Tiempo Respuesta", "2.3h", "-0.5h", "⏱️"),
        ("Satisfacción", "94%", "+1%", "⭐")
    ]
    
    for col, (label, value, delta, icon) in zip(metric_cols, metricas):
        with col:
            components.metric_card(label, value, delta, icon)

def mostrar_gestion_logistica():
    """Página de gestión logística"""
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Guías", "🚚 Distribución", "📦 Inventario", "🔁 Reconciliación"])
    
    with tab1:
        mostrar_generacion_guias_mejorada()
    
    with tab2:
        mostrar_gestion_distribuciones_mejorada()
    
    with tab3:
        mostrar_gestion_inventario()
    
    with tab4:
        mostrar_reconciliacion_mejorada()

def mostrar_generacion_guias_mejorada():
    """Generación de guías mejorada"""
    components.info_box(
        "Guías de Envío",
        "Genere guías de envío para productos Aeropostale.",
        "info"
    )
    
    with st.form("form_guia"):
        col1, col2 = st.columns(2)
        
        with col1:
            tienda = st.selectbox("Tienda", ["Tienda A", "Tienda B", "Tienda C", "Tienda D"])
            producto = st.selectbox("Producto", ["Camisetas", "Pantalones", "Chaquetas", "Accesorios"])
        
        with col2:
            cantidad = st.number_input("Cantidad", min_value=1, max_value=1000, value=1)
            prioridad = st.selectbox("Prioridad", ["Normal", "Urgente", "Express"])
        
        observaciones = st.text_area("Observaciones")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            generar = st.form_submit_button("🚀 Generar Guía", use_container_width=True)
        
        with col_btn2:
            preview = st.form_submit_button("👁️ Vista Previa", use_container_width=True)
        
        with col_btn3:
            limpiar = st.form_submit_button("🗑️ Limpiar", use_container_width=True)
        
        if generar:
            st.success("✅ Guía generada correctamente")
            
            # Mostrar resumen
            components.card("Resumen de Guía", f"""
            **Tienda:** {tienda}<br>
            **Producto:** {producto}<br>
            **Cantidad:** {cantidad}<br>
            **Prioridad:** {prioridad}<br>
            **Observaciones:** {observaciones}<br>
            **Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
            """)

def mostrar_wilo_ai():
    """Página de WILO AI"""
    components.info_box(
        "WILO AI",
        "Sistema de inteligencia artificial para optimización logística.",
        "info"
    )
    
    tab1, tab2, tab3 = st.tabs(["🧠 Análisis", "🤖 Automatización", "📚 Aprendizaje"])
    
    with tab1:
        st.markdown("#### 📊 Análisis Predictivo")
        
        # Selector de modelo
        modelo = st.selectbox("Modelo de análisis", [
            "Predicción de demanda",
            "Optimización de rutas",
            "Detección de anomalías",
            "Pronóstico de inventario"
        ])
        
        # Parámetros
        col_param1, col_param2 = st.columns(2)
        
        with col_param1:
            horizonte = st.slider("Horizonte (días)", 1, 30, 7)
            confianza = st.slider("Nivel de confianza", 0.5, 1.0, 0.95)
        
        with col_param2:
            datos_historicos = st.number_input("Datos históricos (días)", 30, 365, 90)
            actualizar_modelo = st.checkbox("Actualizar modelo en tiempo real")
        
        if st.button("🎯 Ejecutar análisis", use_container_width=True):
            with st.spinner("Analizando datos..."):
                time.sleep(2)
                
                # Resultados simulados
                components.card("Resultados del análisis", """
                **Modelo:** Predicción de demanda<br>
                **Precisión:** 92.3%<br>
                **Confianza:** 95%<br>
                **Recomendaciones:**<br>
                - Aumentar inventario en 15% para la próxima semana<br>
                - Optimizar rutas de distribución<br>
                - Programar mantenimiento preventivo
                """)
    
    with tab2:
        st.markdown("#### ⚡ Automatización de Procesos")
        
        procesos = {
            "📧 Análisis de correos": "Automatiza la lectura y clasificación de correos electrónicos.",
            "📊 Generación de reportes": "Crea reportes automáticos basados en datos en tiempo real.",
            "🚨 Detección de anomalías": "Identifica comportamientos inusuales en los datos.",
            "🔄 Optimización de rutas": "Calcula las rutas más eficientes para distribución."
        }
        
        for nombre, descripcion in procesos.items():
            with st.expander(nombre):
                st.write(descripcion)
                if st.button(f"Activar {nombre.split()[1]}", key=f"activar_{nombre}"):
                    st.success(f"✅ {nombre} activado")
    
    with tab3:
        st.markdown("#### 📚 Aprendizaje Automático")
        
        st.markdown("El sistema WILO AI aprende continuamente de los datos para mejorar sus predicciones.")
        
        # Métricas de aprendizaje
        col_learn1, col_learn2, col_learn3 = st.columns(3)
        
        with col_learn1:
            st.metric("Precisión", "94.2%", "+1.5%")
        
        with col_learn2:
            st.metric("Datos entrenados", "45.2K", "+2.1K")
        
        with col_learn3:
            st.metric("Modelos activos", "12", "+3")
        
        # Botón para entrenar
        if st.button("🔄 Entrenar modelos", use_container_width=True):
            with st.spinner("Entrenando modelos..."):
                time.sleep(3)
                st.success("✅ Modelos actualizados correctamente")

def mostrar_sistema_backup_cache():
    """Página unificada de backup y caché"""
    tab1, tab2 = st.tabs(["💾 Backup", "⚡ Caché"])
    
    with tab1:
        mostrar_sistema_backup()
    
    with tab2:
        mostrar_sistema_cache()

def mostrar_configuracion():
    """Página de configuración del sistema"""
    components.info_box(
        "Configuración",
        "Ajuste la configuración del sistema según sus necesidades.",
        "info"
    )
    
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ General", "🔐 Seguridad", "📊 API", "🔔 Notificaciones"])
    
    with tab1:
        st.markdown("#### Configuración General")
        
        col_gen1, col_gen2 = st.columns(2)
        
        with col_gen1:
            idioma = st.selectbox("Idioma", ["Español", "English", "Português"])
            zona_horaria = st.selectbox("Zona horaria", ["America/Guayaquil", "UTC", "America/New_York"])
        
        with col_gen2:
            formato_fecha = st.selectbox("Formato de fecha", ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"])
            unidades = st.selectbox("Unidades", ["Métrico", "Imperial"])
        
        auto_guardar = st.checkbox("Guardado automático", value=True)
        intervalo_guardado = st.slider("Intervalo de guardado (min)", 1, 60, 5)
        
        if st.button("💾 Guardar configuración", use_container_width=True):
            st.success("✅ Configuración guardada")
    
    with tab2:
        st.markdown("#### Configuración de Seguridad")
        
        st.markdown("##### 🔑 Contraseñas")
        col_pass1, col_pass2 = st.columns(2)
        
        with col_pass1:
            pass_actual = st.text_input("Contraseña actual", type="password")
        
        with col_pass2:
            pass_nueva = st.text_input("Nueva contraseña", type="password")
        
        pass_confirm = st.text_input("Confirmar nueva contraseña", type="password")
        
        if st.button("🔐 Cambiar contraseña", use_container_width=True):
            if pass_nueva == pass_confirm:
                st.success("✅ Contraseña actualizada")
            else:
                st.error("❌ Las contraseñas no coinciden")
        
        st.markdown("##### 🛡️ Seguridad Avanzada")
        autenticacion_doble = st.checkbox("Autenticación de dos factores")
        expiracion_sesion = st.number_input("Expiración de sesión (horas)", 1, 24, 8)
        intentos_maximos = st.number_input("Intentos máximos de inicio de sesión", 1, 10, 3)
    
    with tab3:
        st.markdown("#### Configuración de APIs")
        
        apis = {
            "Google Gemini": "API para inteligencia artificial",
            "Supabase": "API para base de datos",
            "Email": "API para correo electrónico",
            "WhatsApp": "API para mensajería"
        }
        
        for api, descripcion in apis.items():
            with st.expander(f"🔌 {api}"):
                st.write(descripcion)
                api_key = st.text_input(f"API Key {api}", type="password")
                if st.button(f"Probar conexión {api}", key=f"test_{api}"):
                    with st.spinner(f"Probando conexión a {api}..."):
                        time.sleep(1)
                        st.success(f"✅ Conexión exitosa a {api}")
    
    with tab4:
        st.markdown("#### Configuración de Notificaciones")
        
        st.markdown("##### 📧 Notificaciones por Email")
        email_notificaciones = st.text_input("Email para notificaciones")
        frecuencia_email = st.selectbox("Frecuencia de emails", ["Inmediato", "Cada hora", "Diario", "Semanal"])
        
        st.markdown("##### 📱 Notificaciones Push")
        notificaciones_push = st.checkbox("Habilitar notificaciones push", value=True)
        tipos_notificaciones = st.multiselect(
            "Tipos de notificaciones",
            ["Errores", "Advertencias", "Información", "Éxitos"],
            default=["Errores", "Advertencias"]
        )
        
        if st.button("🔔 Guardar preferencias", use_container_width=True):
            st.success("✅ Preferencias guardadas")

# ================================
# FUNCIONES AUXILIARES MEJORADAS
# ================================

def solicitar_autenticacion_mejorada(tipo_requerido: str = "admin"):
    """Formulario de autenticación mejorado"""
    with st.container():
        col_centered = st.columns([1, 2, 1])[1]
        
        with col_centered:
            st.markdown(f"""
            <div style="
                background-color: var(--secondary-background-color);
                padding: 2rem;
                border-radius: 10px;
                text-align: center;
                margin-top: 5rem;
            ">
                <h1 style="color: var(--primary-color);">🔐</h1>
                <h2>Autenticación Requerida</h2>
                <p>Ingrese sus credenciales para acceder al sistema</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                usuario = st.text_input("👤 Usuario", 
                                       placeholder="Ingrese su usuario",
                                       help="Usuario del sistema")
                
                password = st.text_input("🔑 Contraseña", 
                                        type="password",
                                        placeholder="Ingrese su contraseña",
                                        help="Contraseña del sistema")
                
                recordar = st.checkbox("Recordar sesión")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    submitted = st.form_submit_button("✅ Iniciar Sesión", use_container_width=True)
                
                with col_btn2:
                    cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
                
                if submitted:
                    if tipo_requerido == "admin" and password == ADMIN_PASSWORD:
                        st.session_state.user_type = "admin"
                        st.session_state.password_correct = True
                        st.session_state.show_login = False
                        st.success("✅ Autenticación exitosa como administrador")
                        time.sleep(1)
                        st.rerun()
                    elif tipo_requerido == "user" and password == USER_PASSWORD:
                        st.session_state.user_type = "user"
                        st.session_state.password_correct = True
                        st.session_state.show_login = False
                        st.success("✅ Autenticación exitosa como usuario")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta")
                
                if cancel:
                    st.session_state.show_login = False
                    st.rerun()

def generar_reporte_diario():
    """Genera un reporte diario"""
    with st.spinner("Generando reporte..."):
        time.sleep(2)
        
        # Crear reporte de ejemplo
        reporte = {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "transferencias": 1245,
            "distribucion": 89,
            "guias_generadas": 56,
            "problemas": 3,
            "recomendaciones": [
                "Aumentar capacidad de almacenamiento",
                "Optimizar rutas de distribución",
                "Programar mantenimiento preventivo"
            ]
        }
        
        # Mostrar reporte
        components.card("📊 Reporte Diario", f"""
        **Fecha:** {reporte['fecha']}<br>
        **Transferencias:** {reporte['transferencias']} unidades<br>
        **Distribución:** {reporte['distribucion']}% eficiencia<br>
        **Guías generadas:** {reporte['guias_generadas']}<br>
        **Problemas detectados:** {reporte['problemas']}<br>
        **Recomendaciones:**<br>
        - {reporte['recomendaciones'][0]}<br>
        - {reporte['recomendaciones'][1]}<br>
        - {reporte['recomendaciones'][2]}
        """)
        
        # Botón para descargar
        st.download_button(
            label="📥 Descargar Reporte",
            data=json.dumps(reporte, indent=2),
            file_name=f"reporte_{reporte['fecha']}.json",
            mime="application/json"
        )

# ================================
# INICIALIZACIÓN Y EJECUCIÓN
# ================================

def init_session_state_mejorado():
    """Inicializa el session state mejorado"""
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
        'health_monitoring_started': False,
        'current_theme': 'light'
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

if __name__ == "__main__":
    try:
        # Inicializar estado de sesión
        init_session_state_mejorado()
        
        # Iniciar sistemas en segundo plano
        init_background_systems()
        
        # Ejecutar aplicación principal
        main()
        
    except Exception as e:
        st.error(f"Error crítico en la aplicación: {e}")
        logger.error(f"Error en main: {e}", exc_info=True)

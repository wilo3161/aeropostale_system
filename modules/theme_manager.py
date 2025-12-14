# modules/theme_manager.py
"""
Gestor de temas para la aplicación Aeropostale.
Permite cambiar entre modo claro y oscuro.
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional

class ThemeManager:
    """Gestor de temas para la aplicación"""
    
    def __init__(self, theme_config_file: str = "theme_config.json"):
        self.theme_config_file = Path(theme_config_file)
        self.themes = {
            "light": {
                "primary_color": "#1E3A8A",
                "background_color": "#FFFFFF",
                "secondary_background_color": "#F0F2F6",
                "text_color": "#262730",
                "font": "sans-serif",
                "sidebar_background": "#F0F2F6",
                "sidebar_text": "#262730",
                "success_color": "#00C853",
                "warning_color": "#FF9800",
                "error_color": "#FF5252",
                "info_color": "#2196F3"
            },
            "dark": {
                "primary_color": "#60A5FA",
                "background_color": "#0E1117",
                "secondary_background_color": "#262730",
                "text_color": "#FAFAFA",
                "font": "sans-serif",
                "sidebar_background": "#262730",
                "sidebar_text": "#FAFAFA",
                "success_color": "#00E676",
                "warning_color": "#FFB74D",
                "error_color": "#FF5252",
                "info_color": "#64B5F6"
            },
            "corporate": {
                "primary_color": "#1A56DB",
                "background_color": "#FFFFFF",
                "secondary_background_color": "#F5F7FB",
                "text_color": "#111928",
                "font": "sans-serif",
                "sidebar_background": "#1A56DB",
                "sidebar_text": "#FFFFFF",
                "success_color": "#0E9F6E",
                "warning_color": "#F59E0B",
                "error_color": "#F05252",
                "info_color": "#3F83F8"
            }
        }
        self.current_theme = "light"
        self._load_theme()
    
    def _load_theme(self):
        """Carga la configuración del tema desde archivo"""
        try:
            if self.theme_config_file.exists():
                with open(self.theme_config_file, 'r') as f:
                    config = json.load(f)
                    self.current_theme = config.get('current_theme', 'light')
        except Exception:
            pass
    
    def save_theme(self):
        """Guarda la configuración del tema en archivo"""
        try:
            with open(self.theme_config_file, 'w') as f:
                json.dump({'current_theme': self.current_theme}, f)
        except Exception:
            pass
    
    def set_theme(self, theme_name: str):
        """Cambia el tema actual"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.save_theme()
            return True
        return False
    
    def get_theme(self, theme_name: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene la configuración de un tema"""
        if theme_name is None:
            theme_name = self.current_theme
        return self.themes.get(theme_name, self.themes["light"])
    
    def get_css(self, theme_name: Optional[str] = None) -> str:
        """Genera CSS personalizado para el tema"""
        theme = self.get_theme(theme_name)
        
        css = f"""
        <style>
        :root {{
            --primary-color: {theme['primary_color']};
            --background-color: {theme['background_color']};
            --secondary-background-color: {theme['secondary_background_color']};
            --text-color: {theme['text_color']};
            --font: {theme['font']};
            --sidebar-background: {theme['sidebar_background']};
            --sidebar-text: {theme['sidebar_text']};
            --success-color: {theme['success_color']};
            --warning-color: {theme['warning_color']};
            --error-color: {theme['error_color']};
            --info-color: {theme['info_color']};
        }}
        
        /* Aplicar fuentes y colores base */
        html, body, .stApp {{
            font-family: var(--font);
            color: var(--text-color);
            background-color: var(--background-color);
        }}
        
        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: var(--sidebar-background) !important;
        }}
        
        section[data-testid="stSidebar"] * {{
            color: var(--sidebar-text) !important;
        }}
        
        /* Botones */
        .stButton button {{
            background-color: var(--primary-color) !important;
            color: white !important;
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }}
        
        .stButton button:hover {{
            opacity: 0.9;
        }}
        
        /* Encabezados */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--text-color) !important;
        }}
        
        /* Tarjetas y contenedores */
        .card {{
            background-color: var(--secondary-background-color);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid var(--primary-color);
        }}
        
        /* Alertas */
        .stAlert {{
            border-radius: 6px;
            padding: 1rem;
        }}
        
        .alert-success {{
            background-color: var(--success-color) !important;
            color: white !important;
        }}
        
        .alert-warning {{
            background-color: var(--warning-color) !important;
            color: white !important;
        }}
        
        .alert-error {{
            background-color: var(--error-color) !important;
            color: white !important;
        }}
        
        .alert-info {{
            background-color: var(--info-color) !important;
            color: white !important;
        }}
        
        /* DataFrames y tablas */
        .dataframe {{
            background-color: var(--secondary-background-color) !important;
            color: var(--text-color) !important;
        }}
        
        /* Inputs */
        .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox select {{
            background-color: var(--secondary-background-color) !important;
            color: var(--text-color) !important;
            border: 1px solid var(--primary-color) !important;
        }}
        
        /* Pestañas */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: var(--secondary-background-color) !important;
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: var(--secondary-background-color) !important;
            color: var(--text-color) !important;
            border-radius: 4px 4px 0 0;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: var(--primary-color) !important;
            color: white !important;
        }}
        
        /* Tooltips */
        .tooltip {{
            position: relative;
            display: inline-block;
            border-bottom: 1px dotted var(--text-color);
        }}
        
        .tooltip .tooltiptext {{
            visibility: hidden;
            width: 200px;
            background-color: var(--primary-color);
            color: white;
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
        }}
        
        .tooltip:hover .tooltiptext {{
            visibility: visible;
            opacity: 1;
        }}
        
        /* Scrollbar personalizada */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--secondary-background-color);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--primary-color);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--primary-color);
            opacity: 0.8;
        }}
        </style>
        """
        
        return css
    
    def apply_theme(self):
        """Aplica el tema actual a la aplicación"""
        st.markdown(self.get_css(), unsafe_allow_html=True)
    
    def theme_selector(self, sidebar: bool = True):
        """Muestra un selector de tema en la sidebar o main"""
        if sidebar:
            with st.sidebar:
                self._theme_selector_ui()
        else:
            self._theme_selector_ui()
    
    def _theme_selector_ui(self):
        """Interfaz del selector de tema"""
        st.markdown("---")
        st.markdown("### 🎨 Tema")
        
        # Mostrar opciones de tema
        theme_options = {
            "Claro": "light",
            "Oscuro": "dark",
            "Corporativo": "corporate"
        }
        
        selected = st.selectbox(
            "Seleccionar tema:",
            list(theme_options.keys()),
            index=list(theme_options.values()).index(self.current_theme) if self.current_theme in theme_options.values() else 0,
            key="theme_selector"
        )
        
        if st.button("Aplicar Tema", key="apply_theme"):
            self.set_theme(theme_options[selected])
            st.rerun()
        
        # Previsualización colores
        st.markdown("#### Previsualización")
        theme = self.get_theme()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div style="background-color:{theme["primary_color"]}; height:30px; border-radius:4px;"></div>', unsafe_allow_html=True)
            st.caption("Primario")
        with col2:
            st.markdown(f'<div style="background-color:{theme["background_color"]}; height:30px; border-radius:4px; border:1px solid #ccc;"></div>', unsafe_allow_html=True)
            st.caption("Fondo")
        with col3:
            st.markdown(f'<div style="background-color:{theme["success_color"]}; height:30px; border-radius:4px;"></div>', unsafe_allow_html=True)
            st.caption("Éxito")
        with col4:
            st.markdown(f'<div style="background-color:{theme["error_color"]}; height:30px; border-radius:4px;"></div>', unsafe_allow_html=True)
            st.caption("Error")

# Singleton global
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """Obtiene la instancia singleton de ThemeManager"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

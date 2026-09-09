"""
App — Nivel de ríos/quebradas (CORNARE / MARCO)
Estación 49 — San Rafael, Río Guatapé
Wendy — Módulo 5
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Configuración general
# ------------------------------------------------------------------
API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"
LAT_DEFECTO  = 6.2766
LON_DEFECTO  = -75.5901

st.set_page_config(
    page_title="Estación 49 — Río Guatapé",
    page_icon="🌊",
    layout="wide",
)

# ------------------------------------------------------------------
# CSS personalizado
# ------------------------------------------------------------------
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        margin: 6px 0 2px 0;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.82rem;
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-sub {
        font-size: 0.85rem;
        opacity: 0.65;
        margin-top: 4px;
    }
    .semaforo-card {
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c5364;
        margin-bottom: 0px;
        padding-bottom: 4px;
        border-bottom: 2px solid #e0f0f5;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Funciones de consulta
# ------------------------------------------------------------------
def obtener_serie_nivel(codigo, desde, hasta, calidad=1, timeout=30):
    url = f"{API_BASE_URL}/{codigo}/nivel"
    params = {"desde": desde, "hasta": hasta, "calidad": calidad}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"Error de red: {e}"


def obtener_todas_las_paginas(datos_json, timeout=30):
    registros = list(datos_json.get("values", []))
    siguiente_url = datos_json.get("next")
    while siguiente_url:
        try:
            resp = requests.get(siguiente_url, timeout=timeout, verify=False)
        except requests.exceptions.RequestException:
            break
        if resp.status_code != 200:
            break
        pagina = resp.json()
        registros.extend(pagina.get("values", []))
        siguiente_url = pagina.get("next")
    return registros


def calcular_indice_calidad(df):
    if df.empty or len(df) < 2:
        return 0.0, 0, 0
    df_idx = df.set_index("fecha")
    freq = df["fecha"].diff().dropna().mode()
    if len(freq) == 0:
        return 0.0, 0, 0
    freq = freq[0]
    rango = pd.date_range(start=df_idx.index.min(), end=df_idx.index.max(), freq=freq)
    esperados = len(rango)
    huecos = esperados - len(df_idx)
    completitud = max(0.0, 1 - (huecos / esperados)) if esperados > 0 else 0.0
    Q1, Q3 = df["nivel"].quantile(0.25), df["nivel"].quantile(0.75)
    IQR = Q3 - Q1
    es_outlier = (df["nivel"] < Q1 - 1.5 * IQR) | (df["nivel"] > Q3 + 1.5 * IQR) | (df["nivel"] < 0)
    indice = (completitud * 0.7 + (1 - es_outlier.mean()) * 0.3) * 100
    return round(indice, 1), int(huecos), int(es_outlier.sum())


def clasificar_nivel(nivel, p10, p25, p75, p90):
    """Semáforo basado en percentiles de la propia serie."""
    if nivel <= p10:
        return "🔵 Bajo", "#1a6fa8", "#e8f4fd"
    elif nivel <= p25:
        return "🟢 Normal bajo", "#1e8449", "#eafaf1"
    elif nivel <= p75:
        return "🟢 Normal", "#1e8449", "#eafaf1"
    elif nivel <= p90:
        return "🟡 Alto", "#b7950b", "#fef9e7"
    else:
        return "🔴 Alerta", "#c0392b", "#fdedec"


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Color_icon_blue.svg/120px-Color_icon_blue.svg.png", width=40)
st.sidebar.title("Parámetros")
nombre_estudiante = st.sidebar.text_input("Estudiante", "Wendy")
codigo_estacion   = st.sidebar.text_input("Código de estación", "49")
fecha_desde = st.sidebar.date_input("Desde", pd.to_datetime("2026-08-15")).strftime("%Y-%m-%d")
fecha_hasta = st.sidebar.date_input("Hasta", pd.to_datetime("2026-08-31")).strftime("%Y-%m-%d")
calidad     = st.sidebar.selectbox("Calidad", [1, 0], index=0)
consultar   = st.sidebar.button("🔍 Consultar", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Estación 49 · San Rafael · Río Guatapé · CORNARE")

# ------------------------------------------------------------------
# Header principal
# ------------------------------------------------------------------
st.markdown("## 🌊 Estación 49 — San Rafael, Río Guatapé")
st.caption(f"Sistema MARCO · CORNARE · Estudiante: **{nombre_estudiante}**")
st.markdown("---")

# ------------------------------------------------------------------
# Consulta y procesamiento
# ------------------------------------------------------------------
if consultar:
    with st.spinner("Consultando API de CORNARE..."):
        datos_crudos, error = obtener_serie_nivel(codigo_estacion, fecha_desde, fecha_hasta, calidad)

    if error:
        st.error(f"❌ {error}")
        st.stop()

    registros = obtener_todas_las_paginas(datos_crudos)

    if not registros:
        st.warning("No hay registros para este rango. Intenta con otras fechas.")
        st.stop()

    # Construcción del DataFrame
    df = pd.DataFrame(registros)
    df = df.rename(columns={"fecha": "fecha", "nivel": "nivel"})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce")
    df = df.dropna(subset=["fecha", "nivel"]).sort_values("fecha").reset_index(drop=True)

    # Estadísticas base
    nivel_actual  = df["nivel"].iloc[-1]
    nivel_max     = df["nivel"].max()
    nivel_min     = df["nivel"].min()
    nivel_promedio= df["nivel"].mean()
    nivel_std     = df["nivel"].std()
    fecha_actual  = df["fecha"].iloc[-1]
    fecha_max     = df.loc[df["nivel"].idxmax(), "fecha"]

    p10  = df["nivel"].quantile(0.10)
    p25  = df["nivel"].quantile(0.25)
    p75  = df["nivel"].quantile(0.75)
    p90  = df["nivel"].quantile(0.90)

    estado_label, color_fondo, color_claro = clasificar_nivel(nivel_actual, p10, p25, p75, p90)
    delta_promedio = nivel_actual - nivel_promedio
    indice_calidad, huecos, n_outliers = calcular_indice_calidad(df)

    # ==============================================================
    # SECCIÓN 1 — Panel de estado
    # ==============================================================
    st.markdown('<p class="section-title">📊 Panel de estado</p>', unsafe_allow_html=True)
    st.markdown(f"<small>Período: <b>{fecha_desde}</b> al <b>{fecha_hasta}</b> · {len(df):,} lecturas</small>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Fila 1: Nivel actual + Semáforo + Máximo + Calidad
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Nivel actual</div>
            <div class="metric-value">{nivel_actual:.1f}</div>
            <div class="metric-sub">cm &nbsp;|&nbsp; {fecha_actual.strftime('%d-%b %H:%M')} UTC</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        delta_signo = "▲" if delta_promedio >= 0 else "▼"
        delta_color = "#f39c12" if delta_promedio >= 0 else "#3498db"
        st.markdown(f"""
        <div class="semaforo-card" style="background:{color_fondo};">
            <div class="metric-label" style="opacity:0.85;">Estado del río</div>
            <div class="metric-value" style="font-size:1.6rem;">{estado_label}</div>
            <div class="metric-sub" style="color:{delta_color};font-weight:600;">
                {delta_signo} {abs(delta_promedio):.1f} cm vs promedio
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Máximo del período</div>
            <div class="metric-value">{nivel_max:.1f}</div>
            <div class="metric-sub">cm &nbsp;|&nbsp; {fecha_max.strftime('%d-%b %H:%M')} UTC</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        color_calidad = "#27ae60" if indice_calidad >= 90 else "#f39c12" if indice_calidad >= 70 else "#e74c3c"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Índice de calidad</div>
            <div class="metric-value" style="color:{color_calidad};">{indice_calidad}</div>
            <div class="metric-sub">/ 100 &nbsp;·&nbsp; {huecos} huecos detectados</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Fila 2: Gauge + Estadísticas rápidas
    col_gauge, col_stats = st.columns([1.2, 1])

    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=nivel_actual,
            delta={"reference": nivel_promedio, "valueformat": ".1f",
                   "increasing": {"color": "#e74c3c"},
                   "decreasing": {"color": "#27ae60"}},
            number={"suffix": " cm", "font": {"size": 36}},
            title={"text": "Nivel actual vs rango del período", "font": {"size": 14}},
            gauge={
                "axis": {"range": [nivel_min - 10, nivel_max + 10], "tickwidth": 1},
                "bar":  {"color": color_fondo, "thickness": 0.25},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#ddd",
                "steps": [
                    {"range": [nivel_min - 10, p10],  "color": "#d6eaf8"},
                    {"range": [p10, p25],              "color": "#abebc6"},
                    {"range": [p25, p75],              "color": "#82e0aa"},
                    {"range": [p75, p90],              "color": "#f9e79f"},
                    {"range": [p90, nivel_max + 10],   "color": "#f1948a"},
                ],
                "threshold": {
                    "line":  {"color": "#c0392b", "width": 3},
                    "thickness": 0.75,
                    "value": p90,
                },
            },
        ))
        fig_gauge.update_layout(
            height=280,
            margin=dict(t=60, b=20, l=30, r=30),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "sans-serif"},
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_stats:
        st.markdown("<br>", unsafe_allow_html=True)
        stats = {
            "📏 Promedio":    f"{nivel_promedio:.2f} cm",
            "📉 Mínimo":      f"{nivel_min:.2f} cm",
            "📈 Máximo":      f"{nivel_max:.2f} cm",
            "〰️ Desv. std":   f"{nivel_std:.2f} cm",
            "📊 Percentil 25":f"{p25:.2f} cm",
            "📊 Percentil 75":f"{p75:.2f} cm",
            "📊 Percentil 90":f"{p90:.2f} cm",
            "🔢 Lecturas":    f"{len(df):,}",
        }
        for k, v in stats.items():
            c1, c2 = st.columns([1.4, 1])
            c1.markdown(f"<span style='color:#555;font-size:0.88rem;'>{k}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='font-weight:600;font-size:0.88rem;'>{v}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================================
    # SECCIÓN 2 — Serie temporal interactiva
    # ==============================================================
    st.markdown('<p class="section-title">📈 Serie temporal interactiva</p>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Muestreo para rendimiento: máximo 5000 puntos en el gráfico
    df_plot = df.copy()
    if len(df_plot) > 5000:
        step = len(df_plot) // 5000
        df_plot = df_plot.iloc[::step].reset_index(drop=True)

    # Colores por zona según el nivel de cada punto
    def color_zona(n):
        if n <= p10:   return "#3498db"   # azul — bajo
        elif n <= p25: return "#2ecc71"   # verde claro — normal bajo
        elif n <= p75: return "#27ae60"   # verde — normal
        elif n <= p90: return "#f39c12"   # naranja — alto
        else:          return "#e74c3c"   # rojo — alerta

    colores = df_plot["nivel"].apply(color_zona).tolist()

    fig_serie = go.Figure()

    # Banda p25–p75 (zona normal)
    fig_serie.add_trace(go.Scatter(
        x=pd.concat([df_plot["fecha"], df_plot["fecha"].iloc[::-1]]),
        y=pd.concat([
            pd.Series([p75] * len(df_plot)),
            pd.Series([p25] * len(df_plot)).iloc[::-1]
        ]),
        fill="toself",
        fillcolor="rgba(39,174,96,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Zona normal (p25–p75)",
        hoverinfo="skip",
    ))

    # Banda p10–p90 (zona extendida)
    fig_serie.add_trace(go.Scatter(
        x=pd.concat([df_plot["fecha"], df_plot["fecha"].iloc[::-1]]),
        y=pd.concat([
            pd.Series([p90] * len(df_plot)),
            pd.Series([p10] * len(df_plot)).iloc[::-1]
        ]),
        fill="toself",
        fillcolor="rgba(243,156,18,0.07)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Zona extendida (p10–p90)",
        hoverinfo="skip",
    ))

    # Línea principal del nivel
    fig_serie.add_trace(go.Scatter(
        x=df_plot["fecha"],
        y=df_plot["nivel"],
        mode="lines",
        line=dict(color="#2c5364", width=1.2),
        name="Nivel (cm)",
        hovertemplate="<b>%{x|%d-%b %H:%M}</b><br>Nivel: %{y:.1f} cm<extra></extra>",
    ))

    # Línea de promedio
    fig_serie.add_hline(
        y=nivel_promedio,
        line_dash="dot",
        line_color="#7f8c8d",
        line_width=1.5,
        annotation_text=f"Promedio {nivel_promedio:.1f} cm",
        annotation_position="top left",
        annotation_font_size=11,
        annotation_font_color="#7f8c8d",
    )

    # Línea de alerta p90
    fig_serie.add_hline(
        y=p90,
        line_dash="dash",
        line_color="#e74c3c",
        line_width=1,
        annotation_text=f"Alerta p90 ({p90:.1f} cm)",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#e74c3c",
    )

    # Anotación del pico máximo
    idx_max = df["nivel"].idxmax()
    fig_serie.add_annotation(
        x=df.loc[idx_max, "fecha"],
        y=nivel_max,
        text=f"🔺 Pico máximo<br>{nivel_max:.1f} cm",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#c0392b",
        arrowwidth=1.5,
        bgcolor="rgba(231,76,60,0.15)",
        bordercolor="#c0392b",
        borderwidth=1,
        borderpad=4,
        font=dict(size=11, color="#c0392b"),
        ax=40,
        ay=-40,
    )

    fig_serie.update_layout(
        height=420,
        margin=dict(t=30, b=40, l=60, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,0.8)",
        xaxis=dict(
            title="Fecha",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.06)",
            rangeslider=dict(visible=True, thickness=0.06),
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1d",  step="day",  stepmode="backward"),
                    dict(count=3, label="3d",  step="day",  stepmode="backward"),
                    dict(count=7, label="7d",  step="day",  stepmode="backward"),
                    dict(step="all", label="Todo"),
                ],
                bgcolor="#f0f4f8",
                activecolor="#2c5364",
                font=dict(size=11),
            ),
        ),
        yaxis=dict(
            title="Nivel (cm)",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.06)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig_serie, use_container_width=True)

    # Callout informativo debajo del gráfico
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(f"""
        <div style="background:#eafaf1;border-left:4px solid #27ae60;border-radius:8px;padding:10px 14px;">
            <div style="font-size:0.78rem;color:#1e8449;text-transform:uppercase;font-weight:600;">Zona normal</div>
            <div style="font-size:1rem;font-weight:700;color:#1e8449;">{p25:.1f} – {p75:.1f} cm</div>
            <div style="font-size:0.78rem;color:#555;">50% del tiempo el río estuvo aquí</div>
        </div>
        """, unsafe_allow_html=True)
    with col_info2:
        st.markdown(f"""
        <div style="background:#fef9e7;border-left:4px solid #f39c12;border-radius:8px;padding:10px 14px;">
            <div style="font-size:0.78rem;color:#b7950b;text-transform:uppercase;font-weight:600;">Zona alta</div>
            <div style="font-size:1rem;font-weight:700;color:#b7950b;">{p75:.1f} – {p90:.1f} cm</div>
            <div style="font-size:0.78rem;color:#555;">15% del tiempo — nivel elevado</div>
        </div>
        """, unsafe_allow_html=True)
    with col_info3:
        st.markdown(f"""
        <div style="background:#fdedec;border-left:4px solid #e74c3c;border-radius:8px;padding:10px 14px;">
            <div style="font-size:0.78rem;color:#c0392b;text-transform:uppercase;font-weight:600;">Zona alerta</div>
            <div style="font-size:1rem;font-weight:700;color:#c0392b;">> {p90:.1f} cm</div>
            <div style="font-size:0.78rem;color:#555;">10% superior — nivel crítico</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("🚧 Próximamente: Análisis de patrones — heatmap hora × día, perfil diario y distribución del nivel.")

else:
    st.info("👈 Ajusta los parámetros en el sidebar y presiona **Consultar**.")

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
import plotly.express as px
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Configuración general
# ------------------------------------------------------------------
API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

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
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c5364;
        margin-bottom: 0px;
        padding-bottom: 4px;
        border-bottom: 2px solid #e0f0f5;
    }
    .callout {
        border-radius: 8px;
        padding: 10px 14px;
    }
    /* Tabs más anchos y estilizados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: #f0f4f8;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background: #2c5364 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Funciones de consulta
# ------------------------------------------------------------------
def obtener_serie_nivel(codigo, desde, hasta, calidad=1, timeout=30):
    url = f"{API_BASE_URL}/{codigo}/nivel"
    params = {"desde": desde, "hasta": hasta, "calidad": calidad}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
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
        registros.extend(resp.json().get("values", []))
        siguiente_url = resp.json().get("next")
    return registros


def calcular_indice_calidad(df):
    if df.empty or len(df) < 2:
        return 0.0, 0, 0
    freq = df["fecha"].diff().dropna().mode()
    if len(freq) == 0:
        return 0.0, 0, 0
    freq = freq[0]
    rango = pd.date_range(start=df["fecha"].min(), end=df["fecha"].max(), freq=freq)
    esperados = len(rango)
    huecos = esperados - len(df)
    completitud = max(0.0, 1 - (huecos / esperados)) if esperados > 0 else 0.0
    Q1, Q3 = df["nivel"].quantile(0.25), df["nivel"].quantile(0.75)
    IQR = Q3 - Q1
    es_outlier = (df["nivel"] < Q1 - 1.5 * IQR) | (df["nivel"] > Q3 + 1.5 * IQR) | (df["nivel"] < 0)
    indice = (completitud * 0.7 + (1 - es_outlier.mean()) * 0.3) * 100
    return round(indice, 1), int(huecos), int(es_outlier.sum())


def clasificar_nivel(nivel, p10, p25, p75, p90):
    if nivel <= p10:   return "🔵 Bajo",        "#1a6fa8"
    elif nivel <= p25: return "🟢 Normal bajo",  "#1e8449"
    elif nivel <= p75: return "🟢 Normal",       "#1e8449"
    elif nivel <= p90: return "🟡 Alto",         "#b7950b"
    else:              return "🔴 Alerta",       "#c0392b"


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.title("🌊 Parámetros")
nombre_estudiante = st.sidebar.text_input("Estudiante", "Wendy")
codigo_estacion   = st.sidebar.text_input("Código de estación", "49")
fecha_desde = st.sidebar.date_input("Desde", pd.to_datetime("2026-08-15")).strftime("%Y-%m-%d")
fecha_hasta = st.sidebar.date_input("Hasta", pd.to_datetime("2026-08-31")).strftime("%Y-%m-%d")
calidad     = st.sidebar.selectbox("Calidad", [1, 0], index=0)
consultar   = st.sidebar.button("🔍 Consultar", type="primary", use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.caption("Estación 49 · San Rafael · Río Guatapé · CORNARE")

# ------------------------------------------------------------------
# Header
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
        st.warning("No hay registros para este rango.")
        st.stop()

    # DataFrame
    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce")
    df = df.dropna(subset=["fecha", "nivel"]).sort_values("fecha").reset_index(drop=True)

    # Columnas derivadas
    df["hora"]  = df["fecha"].dt.hour
    df["dia"]   = df["fecha"].dt.strftime("%d-%b")
    df["fecha_date"] = df["fecha"].dt.date

    # Estadísticas
    nivel_actual   = df["nivel"].iloc[-1]
    nivel_max      = df["nivel"].max()
    nivel_min      = df["nivel"].min()
    nivel_promedio = df["nivel"].mean()
    nivel_std      = df["nivel"].std()
    fecha_actual   = df["fecha"].iloc[-1]
    fecha_max      = df.loc[df["nivel"].idxmax(), "fecha"]

    p10 = df["nivel"].quantile(0.10)
    p25 = df["nivel"].quantile(0.25)
    p75 = df["nivel"].quantile(0.75)
    p90 = df["nivel"].quantile(0.90)

    estado_label, color_fondo = clasificar_nivel(nivel_actual, p10, p25, p75, p90)
    delta_promedio = nivel_actual - nivel_promedio
    indice_calidad, huecos, n_outliers = calcular_indice_calidad(df)

    # Muestreo para gráficos pesados
    df_plot = df.copy()
    if len(df_plot) > 5000:
        step = len(df_plot) // 5000
        df_plot = df_plot.iloc[::step].reset_index(drop=True)

    # ==============================================================
    # NAVEGACIÓN POR TABS
    # ==============================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Panel de estado",
        "📈 Serie temporal",
        "🔍 Análisis de patrones",
        "🧹 Calidad del dato",
    ])

    # ==============================================================
    # TAB 1 — Panel de estado
    # ==============================================================
    with tab1:
        st.markdown(f"<small>Período: <b>{fecha_desde}</b> al <b>{fecha_hasta}</b> · {len(df):,} lecturas</small>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Nivel actual</div>
                <div class="metric-value">{nivel_actual:.1f}</div>
                <div class="metric-sub">cm · {fecha_actual.strftime('%d-%b %H:%M')} UTC</div>
            </div>""", unsafe_allow_html=True)

        with col2:
            delta_signo = "▲" if delta_promedio >= 0 else "▼"
            delta_color = "#f39c12" if delta_promedio >= 0 else "#3498db"
            st.markdown(f"""
            <div class="semaforo-card" style="background:{color_fondo};">
                <div class="metric-label" style="opacity:0.85;">Estado del río</div>
                <div class="metric-value" style="font-size:1.5rem;">{estado_label}</div>
                <div class="metric-sub" style="color:{delta_color};font-weight:600;">
                    {delta_signo} {abs(delta_promedio):.1f} cm vs promedio
                </div>
            </div>""", unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Máximo del período</div>
                <div class="metric-value">{nivel_max:.1f}</div>
                <div class="metric-sub">cm · {fecha_max.strftime('%d-%b %H:%M')} UTC</div>
            </div>""", unsafe_allow_html=True)

        with col4:
            color_calidad = "#27ae60" if indice_calidad >= 90 else "#f39c12" if indice_calidad >= 70 else "#e74c3c"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Índice de calidad</div>
                <div class="metric-value" style="color:{color_calidad};">{indice_calidad}</div>
                <div class="metric-sub">/ 100 · {huecos} huecos detectados</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

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
                        {"range": [nivel_min - 10, p10], "color": "#d6eaf8"},
                        {"range": [p10, p25],             "color": "#abebc6"},
                        {"range": [p25, p75],             "color": "#82e0aa"},
                        {"range": [p75, p90],             "color": "#f9e79f"},
                        {"range": [p90, nivel_max + 10],  "color": "#f1948a"},
                    ],
                    "threshold": {"line": {"color": "#c0392b", "width": 3}, "thickness": 0.75, "value": p90},
                },
            ))
            fig_gauge.update_layout(
                height=280, margin=dict(t=60, b=20, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)", font={"family": "sans-serif"},
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_stats:
            st.markdown("<br>", unsafe_allow_html=True)
            stats = {
                "📏 Promedio":     f"{nivel_promedio:.2f} cm",
                "📉 Mínimo":       f"{nivel_min:.2f} cm",
                "📈 Máximo":       f"{nivel_max:.2f} cm",
                "〰️ Desv. std":    f"{nivel_std:.2f} cm",
                "📊 Percentil 25": f"{p25:.2f} cm",
                "📊 Percentil 75": f"{p75:.2f} cm",
                "📊 Percentil 90": f"{p90:.2f} cm",
                "🔢 Lecturas":     f"{len(df):,}",
            }
            for k, v in stats.items():
                c1, c2 = st.columns([1.5, 1])
                c1.markdown(f"<span style='color:#555;font-size:0.88rem;'>{k}</span>", unsafe_allow_html=True)
                c2.markdown(f"<span style='font-weight:600;font-size:0.88rem;'>{v}</span>", unsafe_allow_html=True)

    # ==============================================================
    # TAB 2 — Serie temporal interactiva
    # ==============================================================
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)

        fig_serie = go.Figure()

        # Banda p25–p75
        fig_serie.add_trace(go.Scatter(
            x=pd.concat([df_plot["fecha"], df_plot["fecha"].iloc[::-1]]),
            y=pd.concat([pd.Series([p75]*len(df_plot)), pd.Series([p25]*len(df_plot)).iloc[::-1]]),
            fill="toself", fillcolor="rgba(39,174,96,0.12)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Zona normal (p25–p75)", hoverinfo="skip",
        ))

        # Banda p10–p90
        fig_serie.add_trace(go.Scatter(
            x=pd.concat([df_plot["fecha"], df_plot["fecha"].iloc[::-1]]),
            y=pd.concat([pd.Series([p90]*len(df_plot)), pd.Series([p10]*len(df_plot)).iloc[::-1]]),
            fill="toself", fillcolor="rgba(243,156,18,0.07)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Zona extendida (p10–p90)", hoverinfo="skip",
        ))

        # Línea principal
        fig_serie.add_trace(go.Scatter(
            x=df_plot["fecha"], y=df_plot["nivel"],
            mode="lines", line=dict(color="#2c5364", width=1.2),
            name="Nivel (cm)",
            hovertemplate="<b>%{x|%d-%b %H:%M}</b><br>Nivel: %{y:.1f} cm<extra></extra>",
        ))

        fig_serie.add_hline(y=nivel_promedio, line_dash="dot", line_color="#7f8c8d", line_width=1.5,
            annotation_text=f"Promedio {nivel_promedio:.1f} cm",
            annotation_position="top left", annotation_font_size=11, annotation_font_color="#7f8c8d")

        fig_serie.add_hline(y=p90, line_dash="dash", line_color="#e74c3c", line_width=1,
            annotation_text=f"Alerta p90 ({p90:.1f} cm)",
            annotation_position="top right", annotation_font_size=11, annotation_font_color="#e74c3c")

        idx_max = df["nivel"].idxmax()
        fig_serie.add_annotation(
            x=df.loc[idx_max, "fecha"], y=nivel_max,
            text=f"🔺 Pico máximo<br>{nivel_max:.1f} cm",
            showarrow=True, arrowhead=2, arrowcolor="#c0392b", arrowwidth=1.5,
            bgcolor="rgba(231,76,60,0.15)", bordercolor="#c0392b",
            borderwidth=1, borderpad=4, font=dict(size=11, color="#c0392b"),
            ax=40, ay=-40,
        )

        fig_serie.update_layout(
            height=420, margin=dict(t=30, b=40, l=60, r=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,0.8)",
            xaxis=dict(
                title="Fecha", showgrid=True, gridcolor="rgba(0,0,0,0.06)",
                rangeslider=dict(visible=True, thickness=0.06),
                rangeselector=dict(
                    buttons=[
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=3, label="3d", step="day", stepmode="backward"),
                        dict(count=7, label="7d", step="day", stepmode="backward"),
                        dict(step="all", label="Todo"),
                    ],
                    bgcolor="#f0f4f8", activecolor="#2c5364", font=dict(size=11),
                ),
            ),
            yaxis=dict(title="Nivel (cm)", showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
            hovermode="x unified",
        )
        st.plotly_chart(fig_serie, use_container_width=True)

        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            st.markdown(f"""
            <div style="background:#eafaf1;border-left:4px solid #27ae60;border-radius:8px;padding:10px 14px;">
                <div style="font-size:0.78rem;color:#1e8449;text-transform:uppercase;font-weight:600;">Zona normal</div>
                <div style="font-size:1rem;font-weight:700;color:#1e8449;">{p25:.1f} – {p75:.1f} cm</div>
                <div style="font-size:0.78rem;color:#555;">50% del tiempo el río estuvo aquí</div>
            </div>""", unsafe_allow_html=True)
        with col_i2:
            st.markdown(f"""
            <div style="background:#fef9e7;border-left:4px solid #f39c12;border-radius:8px;padding:10px 14px;">
                <div style="font-size:0.78rem;color:#b7950b;text-transform:uppercase;font-weight:600;">Zona alta</div>
                <div style="font-size:1rem;font-weight:700;color:#b7950b;">{p75:.1f} – {p90:.1f} cm</div>
                <div style="font-size:0.78rem;color:#555;">15% del tiempo — nivel elevado</div>
            </div>""", unsafe_allow_html=True)
        with col_i3:
            st.markdown(f"""
            <div style="background:#fdedec;border-left:4px solid #e74c3c;border-radius:8px;padding:10px 14px;">
                <div style="font-size:0.78rem;color:#c0392b;text-transform:uppercase;font-weight:600;">Zona alerta</div>
                <div style="font-size:1rem;font-weight:700;color:#c0392b;">> {p90:.1f} cm</div>
                <div style="font-size:0.78rem;color:#555;">10% superior — nivel crítico</div>
            </div>""", unsafe_allow_html=True)

    # ==============================================================
    # TAB 3 — Análisis de patrones
    # ==============================================================
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)

        # --- Heatmap hora x día ---
        st.markdown('<p class="section-title">🗓️ Heatmap — Nivel promedio por hora y día</p>', unsafe_allow_html=True)
        st.markdown("<small>Cada celda muestra el nivel promedio (cm) para esa hora y ese día. Colores más cálidos = nivel más alto.</small>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        pivot = df.groupby(["dia", "hora"])["nivel"].mean().reset_index()
        # Mantener orden cronológico de días
        orden_dias = df.drop_duplicates("dia").sort_values("fecha")["dia"].tolist()
        pivot["dia"] = pd.Categorical(pivot["dia"], categories=orden_dias, ordered=True)
        pivot = pivot.sort_values(["dia", "hora"])
        heatmap_matrix = pivot.pivot(index="hora", columns="dia", values="nivel")

        fig_heat = go.Figure(go.Heatmap(
            z=heatmap_matrix.values,
            x=heatmap_matrix.columns.tolist(),
            y=heatmap_matrix.index.tolist(),
            colorscale=[
                [0.0,  "#d6eaf8"],
                [0.35, "#82e0aa"],
                [0.65, "#f9e79f"],
                [0.85, "#f0b27a"],
                [1.0,  "#e74c3c"],
            ],
            hovertemplate="Día: %{x}<br>Hora: %{y}:00<br>Nivel promedio: %{z:.1f} cm<extra></extra>",
            colorbar=dict(title="Nivel (cm)", thickness=14, len=0.8),
        ))
        fig_heat.update_layout(
            height=420,
            margin=dict(t=20, b=60, l=60, r=40),
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Día", tickangle=-35, tickfont=dict(size=10)),
            yaxis=dict(title="Hora del día", tickmode="linear", tick0=0, dtick=2,
                       ticktext=[f"{h:02d}:00" for h in range(0, 24, 2)],
                       tickvals=list(range(0, 24, 2))),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_perfil, col_hist = st.columns(2)

        # --- Perfil diario promedio ---
        with col_perfil:
            st.markdown('<p class="section-title">🕐 Perfil diario promedio</p>', unsafe_allow_html=True)
            st.markdown("<small>Nivel promedio para cada hora del día durante todo el período.</small>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            perfil = df.groupby("hora")["nivel"].agg(["mean", "std"]).reset_index()
            perfil.columns = ["hora", "media", "std"]

            fig_perfil = go.Figure()
            # Banda de variabilidad (media ± std)
            fig_perfil.add_trace(go.Scatter(
                x=pd.concat([perfil["hora"], perfil["hora"].iloc[::-1]]),
                y=pd.concat([perfil["media"] + perfil["std"], (perfil["media"] - perfil["std"]).iloc[::-1]]),
                fill="toself", fillcolor="rgba(44,83,100,0.12)",
                line=dict(color="rgba(0,0,0,0)"),
                name="±1 std", hoverinfo="skip",
            ))
            fig_perfil.add_trace(go.Scatter(
                x=perfil["hora"], y=perfil["media"],
                mode="lines+markers",
                line=dict(color="#2c5364", width=2.5),
                marker=dict(size=6, color="#2c5364"),
                name="Nivel promedio",
                hovertemplate="Hora %{x}:00<br>Promedio: %{y:.1f} cm<extra></extra>",
            ))
            # Marca el mínimo y máximo del perfil
            hora_min = perfil.loc[perfil["media"].idxmin(), "hora"]
            hora_max = perfil.loc[perfil["media"].idxmax(), "hora"]
            fig_perfil.add_annotation(x=hora_min, y=perfil["media"].min(),
                text=f"Mínimo<br>{perfil['media'].min():.1f} cm",
                showarrow=True, arrowhead=2, ay=40, font=dict(size=10, color="#1a6fa8"), arrowcolor="#1a6fa8")
            fig_perfil.add_annotation(x=hora_max, y=perfil["media"].max(),
                text=f"Máximo<br>{perfil['media'].max():.1f} cm",
                showarrow=True, arrowhead=2, ay=-40, font=dict(size=10, color="#c0392b"), arrowcolor="#c0392b")

            fig_perfil.update_layout(
                height=320, margin=dict(t=20, b=40, l=50, r=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,0.8)",
                xaxis=dict(title="Hora del día", tickmode="linear", tick0=0, dtick=3,
                           ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)],
                           tickvals=list(range(0, 24, 3))),
                yaxis=dict(title="Nivel (cm)", showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
                showlegend=False,
            )
            st.plotly_chart(fig_perfil, use_container_width=True)

        # --- Histograma con zonas ---
        with col_hist:
            st.markdown('<p class="section-title">📊 Distribución del nivel</p>', unsafe_allow_html=True)
            st.markdown("<small>Frecuencia de cada rango de nivel durante el período.</small>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=df["nivel"], nbinsx=40,
                marker=dict(color="#2c5364", opacity=0.75, line=dict(color="white", width=0.5)),
                name="Frecuencia",
                hovertemplate="Nivel: %{x:.1f} cm<br>Frecuencia: %{y}<extra></extra>",
            ))
            # Líneas de percentiles
            for val, label, color in [
                (p10,  "p10",  "#3498db"),
                (p25,  "p25",  "#27ae60"),
                (p75,  "p75",  "#f39c12"),
                (p90,  "p90",  "#e74c3c"),
                (nivel_promedio, "Promedio", "#7f8c8d"),
            ]:
                fig_hist.add_vline(x=val, line_dash="dash", line_color=color, line_width=1.5,
                    annotation_text=f"{label}<br>{val:.0f}", annotation_font_size=9,
                    annotation_font_color=color, annotation_position="top")

            fig_hist.update_layout(
                height=320, margin=dict(t=40, b=40, l=50, r=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,0.8)",
                xaxis=dict(title="Nivel (cm)", showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
                yaxis=dict(title="Frecuencia", showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
                showlegend=False,
                bargap=0.05,
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        # --- Top 5 eventos pico ---
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">🔺 Top 5 — Eventos de nivel más alto</p>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        top5 = df.nlargest(5, "nivel")[["fecha", "nivel"]].copy()
        top5["Ranking"] = ["🥇 1°", "🥈 2°", "🥉 3°", "4°", "5°"]
        top5["Fecha y hora"] = top5["fecha"].dt.strftime("%d-%b-%Y %H:%M UTC")
        top5["Nivel (cm)"] = top5["nivel"].round(2)
        top5["Estado"] = top5["nivel"].apply(lambda n: clasificar_nivel(n, p10, p25, p75, p90)[0])
        top5 = top5[["Ranking", "Fecha y hora", "Nivel (cm)", "Estado"]].reset_index(drop=True)
        st.dataframe(top5, use_container_width=True, hide_index=True)

    # ==============================================================
    # TAB 4 — Calidad del dato
    # ==============================================================
    with tab4:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">🧹 Resumen de calidad del dato</p>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Índice de calidad</div>
                <div class="metric-value" style="color:{'#27ae60' if indice_calidad>=90 else '#f39c12'};">{indice_calidad}</div>
                <div class="metric-sub">/ 100</div>
            </div>""", unsafe_allow_html=True)
        with col_q2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Huecos detectados</div>
                <div class="metric-value">{huecos}</div>
                <div class="metric-sub">minutos sin reporte</div>
            </div>""", unsafe_allow_html=True)
        with col_q3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Outliers (IQR)</div>
                <div class="metric-value">{n_outliers}</div>
                <div class="metric-sub">de {len(df):,} lecturas</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Huecos por día
        st.markdown('<p class="section-title">📅 Huecos de reporte por día</p>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        df_fecha = df.copy()
        df_fecha["fecha_date"] = df_fecha["fecha"].dt.date
        lecturas_por_dia = df_fecha.groupby("fecha_date")["nivel"].count().reset_index()
        lecturas_por_dia.columns = ["fecha", "lecturas"]
        lecturas_por_dia["esperadas"] = 1440  # 1 por minuto
        lecturas_por_dia["huecos"] = lecturas_por_dia["esperadas"] - lecturas_por_dia["lecturas"]
        lecturas_por_dia["completitud"] = (lecturas_por_dia["lecturas"] / 1440 * 100).round(1)

        fig_huecos = go.Figure()
        fig_huecos.add_trace(go.Bar(
            x=lecturas_por_dia["fecha"].astype(str),
            y=lecturas_por_dia["lecturas"],
            name="Lecturas recibidas",
            marker_color="#2c5364",
            hovertemplate="Día: %{x}<br>Lecturas: %{y}<extra></extra>",
        ))
        fig_huecos.add_trace(go.Bar(
            x=lecturas_por_dia["fecha"].astype(str),
            y=lecturas_por_dia["huecos"],
            name="Huecos",
            marker_color="#e74c3c",
            hovertemplate="Día: %{x}<br>Huecos: %{y}<extra></extra>",
        ))
        fig_huecos.update_layout(
            barmode="stack", height=320,
            margin=dict(t=20, b=60, l=50, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,0.8)",
            xaxis=dict(title="Día", tickangle=-35, tickfont=dict(size=10)),
            yaxis=dict(title="Minutos", showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
            legend=dict(orientation="h", y=1.08, x=0),
        )
        st.plotly_chart(fig_huecos, use_container_width=True)

        with st.expander("📋 Ver tabla de completitud por día"):
            tabla = lecturas_por_dia[["fecha", "lecturas", "huecos", "completitud"]].copy()
            tabla.columns = ["Fecha", "Lecturas recibidas", "Huecos (min)", "Completitud (%)"]
            st.dataframe(tabla, use_container_width=True, hide_index=True)

        with st.expander("📋 Ver datos crudos"):
            st.dataframe(df[["fecha", "nivel", "muestra", "calidad"]].head(500), use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV completo", csv,
                           file_name=f"nivel_estacion_{codigo_estacion}.csv", mime="text/csv")

else:
    st.info("👈 Ajusta los parámetros en el sidebar y presiona **Consultar**.")

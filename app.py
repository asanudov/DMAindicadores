import io
import tempfile
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import unicodedata

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable,
)

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="Dashboard de Indicadores en un DMA",
    layout="wide"
)

# =====================================================
# ESTILOS CSS PERSONALIZADOS
# =====================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Akt:wght=400;500;600;700&display=swap');

    /* 1. FUENTE GLOBAL */
    html, body, [class*="css"], h1, h2, h3, .stMarkdown, .kpi-box {
        font-family: 'Akt', sans-serif !important;
    }

    /* 2. ELIMINAR CABECERA Y SUBIR CONTENIDO AL MÁXIMO */
    header[data-testid="stHeader"] {
        visibility: hidden;
        display: none !important;
    }

    [data-testid="stAppViewContainer"] {
        padding-top: 0rem !important;
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 0.5rem !important;
        margin-top: 0rem !important;
    }

    /* --- JERARQUÍA DE TÍTULOS --- */
    h1 {
        font-size: 26px !important;
        margin-top: 0px !important;
        margin-bottom: 8px !important;
        padding-top: 0px !important;
        color: #1E293B;
        line-height: 1.2 !important;
    }

    h3, .section-subtitle {
        font-size: 18px !important;
        margin-top: 5px !important;
        margin-bottom: 8px !important;
        padding-bottom: 0px !important;
        color: #1E293B;
        font-weight: 600 !important;
    }

    /* Alertas de Suministro */
    .alerta-suministro {
        background-color: #FFEAEA;
        color: #CC0000;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
        border: 1px solid #FFAAAA;
    }

    .alerta-tandeo {
        background-color: #EAF2FF;
        color: #0044CC;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
        border: 1px solid #AABFFF;
    }

    .alerta-valvula {
        background-color: #FFF6E5;
        color: #B36B00;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
        border: 1px solid #FFD98A;
    }

    .alerta-info {
        background-color: #F1F5F9;
        color: #475569;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
        border: 1px solid #CBD5E1;
    }

    .alerta-ventana {
        background-color: #EAF7EE;
        color: #1F7A4D;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
        border: 1px solid #8FD9A8;
    }

    /* Sustituto compacto para st.divider() */
    .compact-divider {
        border-top: 1px solid #e6e6e6;
        margin-top: 12px;
        margin-bottom: 12px;
    }

    /* 3. ESTILOS DE LA TABLA RESUMEN */
    table {
        width: 100%;
        border-collapse: collapse;
    }
    table thead th {
        background-color: #D1E5F0 !important;
        color: #1E293B !important;
        text-align: left !important;
        padding: 8px !important;
        border: 1px solid #e6e6e6 !important;
        font-size: 14px;
    }
    table td {
        font-size: 13px;
    }

    /* 4. SIDEBAR ELEMENTOS */
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] header {
        display: none !important;
    }
    [data-testid="collapsedControl"] { display: none !important; }

    div.stButton > button {
        width: 100%;
        margin-top: 10px;
    }

    /* 5. KPI BOX - TÍTULO NEGRITA, VALOR NORMAL */
    .kpi-box, .kpi-periodo {
        background-color: #f8f9fa;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 10px;
        height: 90px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-title {
        font-size: 13px;
        font-weight: 700 !important;
        margin-bottom: 3px;
    }
    .kpi-value {
        font-size: 17px;
        font-weight: 400 !important;
    }

    /* Estilo específico para Periodo (C6) */
    .kpi-periodo .kpi-title { font-size: 11px; font-weight: 700 !important; }
    .kpi-periodo .kpi-value { font-size: 12px; font-weight: 400 !important; line-height: 1.2; }

    /* KPI destacado de ahorro proyectado */
    .kpi-ahorro {
        background-color: #EAF7EE !important;
        border: 1px solid #8FD9A8 !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================
# PARÁMETROS DE CLASIFICACIÓN (ajustables)
# =====================================================

UMBRAL_P1 = 0.15               # bar. Por debajo de esto se considera "P1 en cero" (sector cerrado / sin presión)
FRAC_DIAS_TANDEO = 0.6          # fracción mínima de días del periodo que deben mostrar el evento para considerarlo recurrente
TOL_HORA_TANDEO = 2.0           # horas. Tolerancia de dispersión en la hora de inicio del evento para considerarlo "misma hora todos los días"
CV_DURACION_TANDEO = 0.5        # coeficiente de variación máximo de la duración de los eventos para considerarlos "misma duración"
MIN_DIAS_ANALISIS = 2           # con menos días no se puede evaluar recurrencia/periodicidad de forma confiable
VENTANA_PICO_MIN = 60           # minutos tras el cierre en que se busca el pico de apertura (tandeo)

UMBRAL_Q_CIERRE = 0.05          # lps. Caudal prácticamente exacto en 0 (más estricto que el umbral de tandeo/falla)
MIN_DURACION_CIERRE_MIN = 30    # minutos. Duración mínima para no confundir un cierre real con ruido de una sola lectura

PSI_A_BAR = 0.0689476           # factor de conversión 1 psi = 0.0689476 bar
UMBRAL_PSI_DETECCION = 25       # bar. Si el promedio de una serie de presión supera esto, se asume que viene en psi y se convierte

FACTOR_ANUAL_LPS_A_M3 = 3600 * 24 * 365 / 1000   # convierte una diferencia de caudal sostenida (lps) a m³/año
FACTOR_DIARIO_LPS_A_M3 = 3600 * 24 / 1000        # convierte una diferencia de caudal sostenida (lps) a m³/día
MIN_NOCHES_REGRESION_N1 = 4     # mínimo de noches con P2/Q válidos en ambos periodos para ajustar N1 por regresión

MIN_DIAS_VENTANA_VALIDA = 5     # días mínimos que debe tener un tramo continuo sin tandeos/fallas/cierres para usarlo como ventana de análisis
MARGEN_EVENTO_VENTANA_MIN = 30  # minutos. Solo los eventos de al menos esta duración cuentan como "día problemático" al buscar la ventana

# =====================================================
# FUNCIONES DE APOYO
# =====================================================

def normalizar(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto


def clasificar_variable(var):
    v = normalizar(var)
    if "p1" in v or "presion 1" in v or "aguas arriba" in v:
        return "P1"
    if "p2" in v or "presion 2" in v or "aguas abajo" in v:
        return "P2"
    if "q" in v or "caudal" in v:
        return "Q"
    return None


def convertir_si_es_psi(serie_df, umbral_bar=UMBRAL_PSI_DETECCION):
    """
    Si el promedio de la serie de presión supera el umbral (poco realista en bar para un DMA),
    se asume que los datos vienen en psi y se convierten a bar. Devuelve (serie_convertida, fue_psi).
    """
    if serie_df.empty:
        return serie_df, False
    if serie_df["Valor"].mean() > umbral_bar:
        serie_df = serie_df.copy()
        serie_df["Valor"] = serie_df["Valor"] * PSI_A_BAR
        return serie_df, True
    return serie_df, False


def construir_eventos_cero(serie_df, umbral):
    """Agrupa lecturas consecutivas por debajo del umbral en 'eventos' (inicio, fin, duración)."""
    if serie_df.empty:
        return pd.DataFrame(columns=["inicio", "fin", "duracion_h", "fecha", "hora_inicio"])

    d = serie_df.sort_values("FechaHora").copy()
    d["EsCero"] = d["Valor"] < umbral
    d["grupo"] = (d["EsCero"] != d["EsCero"].shift()).cumsum()

    eventos = d[d["EsCero"]].groupby("grupo").agg(inicio=("FechaHora", "min"), fin=("FechaHora", "max")).reset_index(drop=True)
    if eventos.empty:
        return eventos

    intervalo = d["FechaHora"].diff().dt.total_seconds().median()
    intervalo = intervalo if pd.notna(intervalo) and intervalo > 0 else 0

    eventos["duracion_h"] = (eventos["fin"] - eventos["inicio"]).dt.total_seconds() / 3600 + intervalo / 3600
    eventos["fecha"] = eventos["inicio"].dt.date
    eventos["hora_inicio"] = eventos["inicio"].dt.hour + eventos["inicio"].dt.minute / 60
    return eventos


def _desviacion_horaria_circular(horas):
    """Desviación estándar 'circular' de horas del día (0-24h), para que 23:50 y 00:10 se traten como cercanas."""
    angulos = horas.to_numpy() / 24 * 2 * np.pi
    sin_m, cos_m = np.mean(np.sin(angulos)), np.mean(np.cos(angulos))
    r = min(np.sqrt(sin_m ** 2 + cos_m ** 2), 0.9999)
    if r <= 0:
        return np.inf
    return np.sqrt(-2 * np.log(r)) / (2 * np.pi) * 24


def clasificar_patron(eventos, dias_totales):
    """
    Devuelve: "sin_eventos", "tandeo" o "falla_operacional".

    Tandeo -> P1 cae a 0 de forma recurrente y a horas similares todos los días (patrón/periodicidad).
    Falla op. -> P1 cae a 0 de forma esporádica, sin patrón horario y con duraciones dispares.
    """
    if eventos.empty:
        return "sin_eventos"
    if dias_totales < MIN_DIAS_ANALISIS or len(eventos) < 2:
        return "falla_operacional"

    frac_dias = eventos["fecha"].nunique() / dias_totales
    dispersion_hora = _desviacion_horaria_circular(eventos["hora_inicio"])
    dur_media = eventos["duracion_h"].mean()
    cv_duracion = eventos["duracion_h"].std(ddof=0) / dur_media if dur_media > 0 else np.inf

    es_recurrente = frac_dias >= FRAC_DIAS_TANDEO
    es_misma_hora = dispersion_hora <= TOL_HORA_TANDEO
    es_misma_duracion = cv_duracion <= CV_DURACION_TANDEO

    if es_recurrente and es_misma_hora and es_misma_duracion:
        return "tandeo"
    return "falla_operacional"


def marcar_cerrado(df, eventos, margen_min=0):
    """Marca True en las filas de df cuyo FechaHora cae dentro de alguna ventana de evento (P1≈0)."""
    cerrado = pd.Series(False, index=df.index)
    if df.empty or eventos.empty:
        return cerrado
    margen = pd.Timedelta(minutes=margen_min)
    for _, ev in eventos.iterrows():
        cerrado |= (df["FechaHora"] >= ev["inicio"] - margen) & (df["FechaHora"] <= ev["fin"] + margen)
    return cerrado


def construir_eventos_cierre_valvula(q_df, p1_df, umbral_q=UMBRAL_Q_CIERRE, umbral_p1=UMBRAL_P1, min_dur_min=MIN_DURACION_CIERRE_MIN):
    """
    Detecta cierres de válvula por condición de trabajo fuera de rango: tramos donde Q cae
    prácticamente a 0 de forma sostenida MIENTRAS P1 se mantiene normal (no es un corte de
    suministro, es la válvula cerrando con presión presente aguas arriba).
    """
    eventos_q = construir_eventos_cero(q_df, umbral_q)
    if eventos_q.empty or p1_df.empty:
        return eventos_q.iloc[0:0]

    validos = []
    for _, ev in eventos_q.iterrows():
        if ev["duracion_h"] * 60 < min_dur_min:
            continue
        p1_ventana = p1_df[(p1_df["FechaHora"] >= ev["inicio"]) & (p1_df["FechaHora"] <= ev["fin"])]
        if p1_ventana.empty or p1_ventana["Valor"].min() >= umbral_p1:
            validos.append(ev)
    return pd.DataFrame(validos) if validos else eventos_q.iloc[0:0]


def calcular_pico_apertura(q_df, eventos, ventana_min=VENTANA_PICO_MIN):
    """Para tandeo: promedio del caudal pico registrado justo al reabrir cada ciclo."""
    if q_df.empty or eventos.empty:
        return None
    picos = []
    for _, ev in eventos.iterrows():
        ventana = q_df[(q_df["FechaHora"] > ev["fin"]) & (q_df["FechaHora"] <= ev["fin"] + pd.Timedelta(minutes=ventana_min))]
        if not ventana.empty:
            picos.append(ventana["Valor"].max())
    return float(np.mean(picos)) if picos else None


def calcular_valles_nocturnos(q_abierto, p2_abierto=None):
    """
    Detecta el valle nocturno de caudal en cada ciclo mediodía-a-mediodía (en vez de una ventana
    fija, p.ej. 2-4am): se ubica el punto más bajo del ciclo y se expande hacia atrás y hacia
    adelante mientras el caudal se mantenga por debajo del nivel promedio del ciclo — eso delimita
    el tramo real desde que empieza a bajar en la noche hasta que empieza a subir en la madrugada.

    Devuelve, por noche: fecha_ciclo, Q_valle (MNF de esa noche), P2_valle (presión aguas abajo
    promedio en ese mismo tramo, para la regresión N1), inicio/fin (timestamps reales del tramo,
    para poder reportar el horario que se consideró "nocturno").
    """
    cols = ["fecha_ciclo", "Q_valle", "P2_valle", "inicio", "fin"]
    if q_abierto.empty:
        return pd.DataFrame(columns=cols)

    df = q_abierto.sort_values("FechaHora").copy()
    df["CicloNoche"] = (df["FechaHora"] - pd.Timedelta(hours=12)).dt.date

    filas = []
    for fecha_ciclo, grupo in df.groupby("CicloNoche"):
        if len(grupo) < 3:
            continue
        grupo = grupo.sort_values("FechaHora").reset_index(drop=True)

        suavizado = grupo["Valor"].rolling(3, center=True, min_periods=1).mean()
        idx_min = suavizado.idxmin()
        umbral_valle = suavizado.mean()

        ini = idx_min
        while ini > 0 and suavizado[ini - 1] <= umbral_valle:
            ini -= 1
        fin = idx_min
        while fin < len(suavizado) - 1 and suavizado[fin + 1] <= umbral_valle:
            fin += 1

        valle = grupo.loc[ini:fin, "Valor"]
        if valle.empty:
            continue

        t_ini, t_fin = grupo.loc[ini, "FechaHora"], grupo.loc[fin, "FechaHora"]
        p2_valle = np.nan
        if p2_abierto is not None and not p2_abierto.empty:
            ventana_p2 = p2_abierto[(p2_abierto["FechaHora"] >= t_ini) & (p2_abierto["FechaHora"] <= t_fin)]
            if not ventana_p2.empty:
                p2_valle = float(ventana_p2["Valor"].mean())

        filas.append({
            "fecha_ciclo": fecha_ciclo, "Q_valle": float(valle.min()), "P2_valle": p2_valle,
            "inicio": t_ini, "fin": t_fin,
        })
    return pd.DataFrame(filas)


def calcular_mnf(q_abierto):
    """MNF = media aritmética del caudal mínimo de cada 'valle nocturno' (ver calcular_valles_nocturnos)."""
    valles = calcular_valles_nocturnos(q_abierto)
    if valles.empty:
        return None
    return float(valles["Q_valle"].mean())


def ventana_nocturna_promedio(valles):
    """
    A partir de los tramos [inicio, fin] detectados noche a noche, calcula una ventana horaria
    "típica" (hora de inicio y fin promedio, y duración promedio) para reportarle al usuario, en
    una sola frase, qué horario consideró la plataforma como "nocturno". Mide cada inicio/fin como
    horas transcurridas desde el mediodía del ciclo (escala monótona 0-24h) para evitar el problema
    de promediar horas de reloj que cruzan la medianoche.
    """
    if valles is None or valles.empty:
        return None
    validos = valles.dropna(subset=["inicio", "fin"])
    if validos.empty:
        return None
    noon = pd.to_datetime(validos["fecha_ciclo"]) + pd.Timedelta(hours=12)
    h_ini = (validos["inicio"] - noon).dt.total_seconds() / 3600
    h_fin = (validos["fin"] - noon).dt.total_seconds() / 3600
    prom_ini = h_ini.mean() % 24
    prom_fin = h_fin.mean() % 24
    duracion_h = float((h_fin - h_ini).mean())

    def _fmt(horas_desde_noon):
        total_min = int(round((horas_desde_noon % 24) * 60))
        hh, mm = divmod(total_min, 60)
        hh = (hh + 12) % 24
        return f"{hh:02d}:{mm:02d}"

    return {
        "inicio": _fmt(prom_ini),
        "fin": _fmt(prom_fin),
        "duracion_h": duracion_h,
        "n_noches": int(len(validos)),
    }


def estimar_n1(valles_previo, valles_posterior, min_puntos=MIN_NOCHES_REGRESION_N1):
    """Exponente N1 de FAVAD (q = c·h^N1) por regresión log-log Q vs. P aguas abajo, noche a noche."""
    def _validos(v, etiqueta):
        if v is None or v.empty:
            return pd.DataFrame(columns=["fecha_ciclo", "Q_valle", "P2_valle", "Periodo"])
        v = v.dropna(subset=["Q_valle", "P2_valle"])
        v = v[(v["Q_valle"] > 0) & (v["P2_valle"] > 0)].copy()
        v["Periodo"] = etiqueta
        return v

    comb = pd.concat([_validos(valles_previo, "Previo"), _validos(valles_posterior, "Posterior")], ignore_index=True)
    if comb.empty or comb["Periodo"].nunique() < 2:
        return None
    if len(comb) >= min_puntos:
        x = np.log(comb["P2_valle"].to_numpy())
        y = np.log(comb["Q_valle"].to_numpy())
        n1, intercepto = np.polyfit(x, y, 1)
        r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
        return {"n1": float(n1), "intercepto": float(intercepto), "r2": r2, "n_puntos": len(comb),
                "metodo": "regresion", "datos": comb}
    prom_previo = comb[comb["Periodo"] == "Previo"]
    prom_post = comb[comb["Periodo"] == "Posterior"]
    if prom_previo.empty or prom_post.empty:
        return None
    q0, p0 = prom_previo["Q_valle"].mean(), prom_previo["P2_valle"].mean()
    q1, p1v = prom_post["Q_valle"].mean(), prom_post["P2_valle"].mean()
    if p0 <= 0 or p1v <= 0 or p0 == p1v:
        return None
    n1 = float(np.log(q1 / q0) / np.log(p1v / p0))
    return {"n1": n1, "intercepto": None, "r2": None, "n_puntos": len(comb),
            "metodo": "2 puntos (aproximado)", "datos": comb}


def estimar_carl_uarl(mnf_lps, ili):
    """
    Usa el Índice de Fugas de Infraestructura (ILI) que el usuario conoce de antemano (no se
    calcula aquí a partir de longitud de red / número de acometidas / presión: eso requeriría
    datos de catastro de red que esta plataforma no solicita) para poner el MNF en contexto:

        ILI = CARL / UARL   (Lambert et al., metodología IWA)

    CARL = pérdidas reales anuales actuales, UARL = pérdidas reales anuales inevitables (piso
    técnico de un sistema de ese tamaño, bien mantenido). Aquí el CARL se aproxima con el MNF del
    periodo "previo" extrapolado de forma plana a un año (probablemente sobreestimado, porque no
    se separa el consumo legítimo nocturno de la fuga). Con eso y el ILI dado se despeja el UARL.
    """
    if mnf_lps is None or ili is None or ili <= 0:
        return None
    carl = mnf_lps * FACTOR_ANUAL_LPS_A_M3
    uarl = carl / ili
    margen_teorico = max(carl - uarl, 0.0)
    return {"ili": float(ili), "carl_aprox": float(carl), "uarl": float(uarl), "margen_teorico": float(margen_teorico)}


def encontrar_ventana_valida(f_min, f_max, eventos_p1, eventos_valvula,
                              min_dias=MIN_DIAS_VENTANA_VALIDA, margen_min=MARGEN_EVENTO_VENTANA_MIN):
    """
    Dentro de todo el archivo, busca el tramo continuo de días más largo que no tenga tandeos,
    fallas operacionales (P1≈0) ni cierres de válvula — para no mezclar, en un mismo promedio,
    un periodo inestable (por ejemplo mientras se ajustaba la operación del sector) con el
    periodo realmente representativo. Si no hay un tramo de al menos `min_dias` días sin estos
    eventos, devuelve None y se usa el archivo completo (comportamiento anterior).

    Solo cuentan como "día problemático" los eventos de al menos `margen_min` minutos, para no
    fragmentar un tramo bueno por una sola lectura ruidosa de 15-30 minutos.
    En empates de longitud, se prefiere el tramo más reciente (más cercano al final del archivo).
    """
    if f_min is None or f_max is None:
        return None
    dias = pd.date_range(f_min.normalize(), f_max.normalize(), freq="D")
    if len(dias) < min_dias:
        return None

    malo = pd.Series(False, index=range(len(dias)))
    for eventos in (eventos_p1, eventos_valvula):
        if eventos is None or eventos.empty:
            continue
        largos = eventos[eventos["duracion_h"] * 60 >= margen_min]
        for _, ev in largos.iterrows():
            ini_d = ev["inicio"].normalize()
            fin_d = ev["fin"].normalize()
            malo[(dias >= ini_d) & (dias <= fin_d)] = True

    mejor_ini = mejor_fin = None
    mejor_len = 0
    i, n = 0, len(dias)
    while i < n:
        if malo.iloc[i]:
            i += 1
            continue
        j = i
        while j < n and not malo.iloc[j]:
            j += 1
        largo = j - i
        if largo >= mejor_len:
            mejor_len = largo
            mejor_ini, mejor_fin = dias[i], dias[j - 1]
        i = j

    if mejor_len < min_dias:
        return None
    return mejor_ini, mejor_fin + pd.Timedelta(hours=23, minutes=59, seconds=59)


def procesar_archivo(archivo):
    """Lee un Excel de ConDor y devuelve un dict con todos los indicadores/insumos para renderizar el dashboard."""
    df_raw = pd.read_excel(archivo)
    df_raw.columns = df_raw.columns.str.strip()
    df_raw = df_raw.rename(columns={"Data Logger": "Variable", "Fecha y hora": "FechaHora", "Media": "Valor"})
    df_raw["FechaHora"] = pd.to_datetime(df_raw["FechaHora"], dayfirst=True)
    df_raw["Valor"] = df_raw["Valor"].astype(str).str.replace(",", ".", regex=False).astype(float)
    df_raw["Tipo"] = df_raw["Variable"].apply(clasificar_variable)

    # Extraer dataframes independientes por variable
    p1 = df_raw[df_raw["Tipo"] == "P1"].sort_values("FechaHora").copy()
    p2 = df_raw[df_raw["Tipo"] == "P2"].sort_values("FechaHora").copy()
    q = df_raw[df_raw["Tipo"] == "Q"].sort_values("FechaHora").copy()

    # Detección y conversión automática de psi a bar (algunos ConDor reportan presión en psi)
    p1, p1_fue_psi = convertir_si_es_psi(p1)
    p2, p2_fue_psi = convertir_si_es_psi(p2)
    hay_conversion_psi = p1_fue_psi or p2_fue_psi

    f_min_archivo = df_raw["FechaHora"].min() if not df_raw.empty else None
    f_max_archivo = df_raw["FechaHora"].max() if not df_raw.empty else None

    # --- Selección automática de la ventana de análisis válida ---
    # Se detectan primero los eventos sobre TODO el archivo, para ubicar el tramo continuo más
    # largo sin tandeos/fallas/cierres de válvula, y se restringe el resto del análisis a ese
    # tramo (ver encontrar_ventana_valida). Si el archivo ya es estable de principio a fin, la
    # ventana coincide con el archivo completo y no cambia nada del comportamiento anterior.
    eventos_p1_archivo = construir_eventos_cero(p1, UMBRAL_P1)
    eventos_valvula_archivo = construir_eventos_cierre_valvula(q, p1)
    ventana = encontrar_ventana_valida(f_min_archivo, f_max_archivo, eventos_p1_archivo, eventos_valvula_archivo)

    ventana_restringida = False
    dias_excluidos_antes = dias_excluidos_despues = 0
    if ventana is not None:
        v_ini, v_fin = ventana
        if v_ini > f_min_archivo or v_fin < f_max_archivo:
            ventana_restringida = True
            dias_excluidos_antes = max((v_ini - f_min_archivo).days, 0)
            dias_excluidos_despues = max((f_max_archivo - v_fin).days, 0)
            p1 = p1[(p1["FechaHora"] >= v_ini) & (p1["FechaHora"] <= v_fin)]
            p2 = p2[(p2["FechaHora"] >= v_ini) & (p2["FechaHora"] <= v_fin)]
            q = q[(q["FechaHora"] >= v_ini) & (q["FechaHora"] <= v_fin)]

    # Detección de eventos de P1≈0 y clasificación de patrón (tandeo vs falla operacional),
    # ya dentro de la ventana de análisis seleccionada (o del archivo completo si no se restringió).
    dias_totales = p1["FechaHora"].dt.date.nunique() if not p1.empty else (q["FechaHora"].dt.date.nunique() if not q.empty else 0)
    eventos_p1 = construir_eventos_cero(p1, UMBRAL_P1)
    patron = clasificar_patron(eventos_p1, dias_totales)

    es_tandeo = patron == "tandeo"
    hay_falla_operacional = patron == "falla_operacional"

    # Cierres de válvula por condición de trabajo fuera de rango: Q≈0 sostenido con P1 normal.
    eventos_valvula = construir_eventos_cierre_valvula(q, p1)
    hay_cierre_valvula = not eventos_valvula.empty

    # Ventanas de "cerrado" proyectadas sobre cada serie, para excluirlas del cálculo de indicadores
    p1["Cerrado"] = marcar_cerrado(p1, eventos_p1) if not p1.empty else False
    p2["Cerrado"] = marcar_cerrado(p2, eventos_p1) if not p2.empty else False
    q["Cerrado"] = (marcar_cerrado(q, eventos_p1) | marcar_cerrado(q, eventos_valvula)) if not q.empty else False

    p1_abierto = p1[~p1["Cerrado"]] if not p1.empty else p1
    p2_abierto = p2[~p2["Cerrado"]] if not p2.empty else p2
    q_abierto = q[~q["Cerrado"]] if not q.empty else q

    # Cálculos Generales de Indicadores (KPIs) — excluyendo tramos "cerrados" en todos los escenarios
    p1_prom = p1_abierto["Valor"].mean() if not p1_abierto.empty else 0.0
    p2_prom = p2_abierto["Valor"].mean() if not p2_abierto.empty else 0.0
    q_prom = q_abierto[q_abierto["Valor"] > 0.1]["Valor"].mean() if not q_abierto.empty else 0.0

    q_pico_apertura = calcular_pico_apertura(q, eventos_p1) if es_tandeo else None

    # Volumen: se integra sobre la serie completa (es un totalizador del periodo, no un promedio representativo)
    if not q.empty:
        q["Delta_t"] = q["FechaHora"].diff().dt.total_seconds().fillna(0)
        volumen = (q["Valor"] * q["Delta_t"] / 1000).sum()
        f_min_raw, f_max_raw = q["FechaHora"].min(), q["FechaHora"].max()
        f_min = f_min_raw.strftime('%d/%m/%Y')
        f_max = f_max_raw.strftime('%d/%m/%Y')
    else:
        volumen = 0.0
        f_min_raw = f_max_raw = None
        f_min = f_max = "-/-/-"

    if not q_abierto.empty:
        f_min_valido, f_max_valido = q_abierto["FechaHora"].min(), q_abierto["FechaHora"].max()
    else:
        f_min_valido = f_max_valido = None

    # MNF y "valles nocturnos": media/serie del caudal mínimo de cada ciclo noche-mañana, sobre
    # los tramos "abiertos", junto con la presión aguas abajo y el horario real de cada valle
    # (necesarios para el exponente N1, la ventana horaria típica, y el reporte PDF).
    valles_nocturnos = calcular_valles_nocturnos(q_abierto, p2_abierto)
    nmf = float(valles_nocturnos["Q_valle"].mean()) if not valles_nocturnos.empty else None
    ventana_nocturna = ventana_nocturna_promedio(valles_nocturnos)

    ventana_nota = None
    if ventana_restringida:
        partes = []
        if dias_excluidos_antes > 0:
            partes.append(f"{dias_excluidos_antes} día(s) antes del {f_min}")
        if dias_excluidos_despues > 0:
            partes.append(f"{dias_excluidos_despues} día(s) después del {f_max}")
        ventana_nota = (
            f"🔎 Ventana de análisis ajustada automáticamente: se excluyeron "
            f"{' y '.join(partes)} por tandeos, fallas operacionales o cierres de válvula "
            f"frecuentes en ese tramo. Se analizó el periodo {f_min} – {f_max} "
            f"({dias_totales} días), el tramo continuo más largo sin esos problemas."
        )

    return {
        "p1_prom": p1_prom, "p2_prom": p2_prom, "q_prom": q_prom, "volumen": volumen,
        "nmf": nmf, "f_min": f_min, "f_max": f_max,
        "f_min_raw": f_min_raw, "f_max_raw": f_max_raw,
        "f_min_valido": f_min_valido, "f_max_valido": f_max_valido,
        "f_min_archivo": f_min_archivo, "f_max_archivo": f_max_archivo,
        "ventana_restringida": ventana_restringida, "ventana_nota": ventana_nota,
        "dias_excluidos_antes": dias_excluidos_antes, "dias_excluidos_despues": dias_excluidos_despues,
        "ventana_nocturna": ventana_nocturna, "valles_nocturnos": valles_nocturnos,
        "es_tandeo": es_tandeo, "hay_falla_operacional": hay_falla_operacional,
        "hay_cierre_valvula": hay_cierre_valvula, "hay_conversion_psi": hay_conversion_psi,
        "p1_fue_psi": p1_fue_psi, "p2_fue_psi": p2_fue_psi,
        "eventos_p1": eventos_p1, "eventos_valvula": eventos_valvula,
        "dias_totales": dias_totales, "q_pico_apertura": q_pico_apertura,
        "q": q,
    }


def kpi(col, t, v, clase_extra=""):
    col.markdown(f'<div class="kpi-box {clase_extra}"><div class="kpi-title">{t}</div><div class="kpi-value">{v}</div></div>', unsafe_allow_html=True)


def graficar_serie(r, titulo=""):
    """Construye la gráfica de caudal de un periodo (misma lógica visual que mostrar_dashboard, mode reusable: también la usa el PDF)."""
    fig = go.Figure()
    q = r["q"]

    if not q.empty:
        fig.add_trace(go.Scatter(x=q["FechaHora"], y=q["Valor"], mode="lines", name="Q", line=dict(width=2, color="blue")))
        fig.add_trace(go.Scatter(x=[q["FechaHora"].min(), q["FechaHora"].max()], y=[r["q_prom"], r["q_prom"]], mode="lines", name="Q prom", line=dict(width=1.5, color="red", dash="dot")))

        if r["nmf"] is not None:
            fig.add_trace(go.Scatter(x=[q["FechaHora"].min(), q["FechaHora"].max()], y=[r["nmf"], r["nmf"]], mode="lines", name="MNF", line=dict(width=2, color="green", dash="dash")))

        if r["es_tandeo"] and r["q_pico_apertura"] is not None:
            fig.add_trace(go.Scatter(x=[q["FechaHora"].min(), q["FechaHora"].max()], y=[r["q_pico_apertura"], r["q_pico_apertura"]], mode="lines", name="Pico de Apertura", line=dict(width=1.5, color="purple", dash="longdashdot")))

        if not r["eventos_p1"].empty:
            color_evento = "rgba(0,68,204,0.15)" if r["es_tandeo"] else "rgba(204,0,0,0.15)"
            nombre_evento = "Tandeo (cerrado)" if r["es_tandeo"] else "Falla operacional"
            for i, (_, ev) in enumerate(r["eventos_p1"].iterrows()):
                fig.add_vrect(
                    x0=ev["inicio"], x1=ev["fin"],
                    fillcolor=color_evento, opacity=0.5, line_width=0,
                    annotation_text=nombre_evento if i == 0 else None,
                    annotation_position="top left"
                )

        if not r["eventos_valvula"].empty:
            for i, (_, ev) in enumerate(r["eventos_valvula"].iterrows()):
                fig.add_vrect(
                    x0=ev["inicio"], x1=ev["fin"],
                    fillcolor="rgba(255,153,0,0.20)", opacity=0.6, line_width=0,
                    annotation_text="Cierre de válvula" if i == 0 else None,
                    annotation_position="bottom left"
                )

    fig.update_layout(
        title=titulo,
        height=460,
        margin=dict(t=40 if titulo else 10, b=10, l=10, r=10),
        hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center")
    )
    return fig


def graficar_n1(n1_info):
    if n1_info is None or n1_info.get("metodo") != "regresion":
        return None
    datos = n1_info["datos"]
    fig = go.Figure()
    colores = {"Previo": "#2A78D6", "Posterior": "#EB6834"}
    for periodo, color in colores.items():
        sub = datos[datos["Periodo"] == periodo]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(x=np.log(sub["P2_valle"]), y=np.log(sub["Q_valle"]), mode="markers",
                                  name=periodo, marker=dict(color=color, size=9)))
    x_vals = np.log(datos["P2_valle"])
    x_line = np.linspace(x_vals.min(), x_vals.max(), 20)
    y_line = n1_info["n1"] * x_line + n1_info["intercepto"]
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode="lines", name="Ajuste N1", line=dict(color="#475569", dash="dash")))
    fig.update_layout(
        title=f"N1 ≈ {n1_info['n1']:.2f}  (R²={n1_info['r2']:.2f}, {n1_info['n_puntos']} noches)" if n1_info["r2"] else f"N1 ≈ {n1_info['n1']:.2f}",
        xaxis_title="ln(P aguas abajo)", yaxis_title="ln(Q)", height=380,
        margin=dict(t=40, b=10, l=10, r=10),
        legend=dict(orientation="h", y=1.18, x=0.5, xanchor="center"),
    )
    return fig


def mostrar_dashboard(r, key_prefix=""):
    """Renderiza alertas + KPIs + tabla resumen + gráfico para un resultado de procesar_archivo()."""
    st.markdown("### Indicadores del Sector")

    if r.get("ventana_restringida") and r.get("ventana_nota"):
        st.markdown(f'<div class="alerta-ventana">{r["ventana_nota"]}</div>', unsafe_allow_html=True)

    if r["es_tandeo"]:
        frac_dias = r["eventos_p1"]["fecha"].nunique() / r["dias_totales"]
        hora_prom = r["eventos_p1"]["hora_inicio"].mean()
        st.markdown(
            f'<div class="alerta-tandeo">🔄 Suministro Intermitente (Tandeo detectado — patrón recurrente en '
            f'{frac_dias * 100:.0f}% de los días, cierre habitual ~{hora_prom:.0f}:00 h)</div>',
            unsafe_allow_html=True
        )
    elif r["hay_falla_operacional"]:
        st.markdown(
            f'<div class="alerta-suministro">⚠️ Fallas operacionales esporádicas detectadas '
            f'({len(r["eventos_p1"])} evento(s) sin patrón definido) — excluidas del cálculo de indicadores</div>',
            unsafe_allow_html=True
        )

    if r["hay_cierre_valvula"]:
        st.markdown(
            f'<div class="alerta-valvula">🔧 Cierre(s) de válvula por condición de trabajo fuera de rango '
            f'({len(r["eventos_valvula"])} evento(s), Q≈0 con P1 normal) — excluidos del cálculo de Q prom y MNF</div>',
            unsafe_allow_html=True
        )

    if r["hay_conversion_psi"]:
        sensores_psi = " y ".join([n for n, f in [("P1", r["p1_fue_psi"]), ("P2", r["p2_fue_psi"])] if f])
        st.markdown(
            f'<div class="alerta-info">🔁 Presión de {sensores_psi} detectada en psi — convertida automáticamente a bar</div>',
            unsafe_allow_html=True
        )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    kpi(c1, "P1 (bar)", f"{r['p1_prom']:.2f}")
    kpi(c2, "P2 (bar)", f"{r['p2_prom']:.2f}")
    kpi(c3, "Q prom (lps)", f"{r['q_prom']:.2f}")
    kpi(c4, "Volumen", f"{r['volumen']:.2f} m³")

    if r["es_tandeo"] and r["q_pico_apertura"] is not None:
        kpi(c5, "Q Pico Apertura (lps)", f"{r['q_pico_apertura']:.2f}")
    else:
        kpi(c5, "MNF (lps)", f"{r['nmf']:.2f}" if r["nmf"] is not None else "-")

    titulo_periodo = "Periodo analizado" if r.get("ventana_restringida") else "Periodo"
    c6.markdown(
        f'<div class="kpi-periodo"><div class="kpi-title">{titulo_periodo}</div><div class="kpi-value">{r["f_min"]}<br>–<br>{r["f_max"]}</div></div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)

    # =====================================================
    # CUERPO DEL DASHBOARD (TABLA Y GRÁFICO)
    # =====================================================
    col_tabla, col_grafico = st.columns([1, 2.3])

    with col_tabla:
        st.markdown('<h3 class="section-subtitle">Resumen</h3>', unsafe_allow_html=True)

        indicadores_lista = ["P1", "P2", "Q prom", "Volumen", "MNF"]
        valores_lista = [f"{r['p1_prom']:.2f}", f"{r['p2_prom']:.2f}", f"{r['q_prom']:.2f}", f"{r['volumen']:.2f}", f"{r['nmf']:.2f}" if r["nmf"] is not None else "-"]
        unidades_lista = ["bar", "bar", "lps", "m³", "lps"]

        if r["es_tandeo"] and r["q_pico_apertura"] is not None:
            indicadores_lista.append("Q Pico Apertura")
            valores_lista.append(f"{r['q_pico_apertura']:.2f}")
            unidades_lista.append("lps")

        resumen = pd.DataFrame({
            "Indicador": indicadores_lista,
            "Valor": valores_lista,
            "Unidad": unidades_lista
        })
        st.markdown(resumen.to_html(index=False, escape=False), unsafe_allow_html=True)

        st.markdown(
            f'<p style="font-size:12px; color:#64748B; margin-top:8px;">'
            f'Horario considerado como "nocturno" para el MNF: '
            f'{(r["ventana_nocturna"]["inicio"] + " – " + r["ventana_nocturna"]["fin"] + " h") if r.get("ventana_nocturna") else "no se pudo determinar"}.'
            f'</p>',
            unsafe_allow_html=True
        )

    with col_grafico:
        fig = graficar_serie(r)
        st.plotly_chart(fig, width="stretch", key=f"grafico_{key_prefix}")


def _fecha_hora(ts):
    if ts is None:
        return "—"
    return ts.strftime("%d/%m/%Y %H:%M")


def generar_pdf_reporte(resultado_previo, resultado_posterior, ili=None, out_path=None):
    """
    Genera el reporte en PDF con: periodo de datos previo/posterior (crudo y válido), horario
    considerado como gestión nocturna, caudal nocturno promedio antes/después, conversión a
    volumen, proyección a un año, el exponente N1, y (si se da un ILI) el contexto CARL/UARL.
    Devuelve la ruta del PDF generado.
    """
    NAVY = colors.HexColor("#1E293B")
    BLUE = colors.HexColor("#2A5B8C")
    LIGHT = colors.HexColor("#F1F5F9")
    GREY = colors.HexColor("#64748B")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TituloReporte", fontSize=18, leading=22, textColor=NAVY, spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Subtitulo", fontSize=10, leading=13, textColor=GREY, spaceAfter=14, fontName="Helvetica-Oblique"))
    styles.add(ParagraphStyle(name="H2", fontSize=13, leading=16, textColor=BLUE, spaceBefore=16, spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Cuerpo", fontSize=9.5, leading=13, textColor=colors.HexColor("#0B0B0B")))
    styles.add(ParagraphStyle(name="Nota", fontSize=8.3, leading=11, textColor=GREY))

    def _num(v, dec=2, suf=""):
        if v is None:
            return "—"
        return f"{v:,.{dec}f}{suf}"

    def _tabla_kv(filas, col_widths=(7.5 * cm, 9.5 * cm)):
        data = [[Paragraph(f"<b>{k}</b>", styles["Cuerpo"]), Paragraph(str(v), styles["Cuerpo"])] for k, v in filas]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ]))
        return t

    def _fig_a_imagen(fig, ancho=16 * cm, alto=7.5 * cm):
        if fig is None:
            return None
        png_bytes = fig.to_image(format="png", width=1000, height=460, scale=2)
        buf = io.BytesIO(png_bytes)
        return Image(buf, width=ancho, height=alto)

    if out_path is None:
        out_path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name

    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    )
    story = []

    story.append(Paragraph("Reporte de Gestión de Presiones en un DMA", styles["TituloReporte"]))
    story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Subtitulo"]))

    story.append(Paragraph("Periodos analizados", styles["H2"]))
    filas_periodos = [
        ("Periodo de datos — previo a la gestión (archivo completo)",
         f"{_fecha_hora(resultado_previo.get('f_min_archivo'))} &nbsp;–&nbsp; {_fecha_hora(resultado_previo.get('f_max_archivo'))}"),
        ("Periodo de datos — posterior a la gestión (archivo completo)",
         f"{_fecha_hora(resultado_posterior.get('f_min_archivo'))} &nbsp;–&nbsp; {_fecha_hora(resultado_posterior.get('f_max_archivo'))}"),
    ]
    if resultado_previo.get("ventana_restringida"):
        filas_periodos.append((
            "Ventana de análisis — previo (seleccionada automáticamente, excluye tramo inestable)",
            f"{_fecha_hora(resultado_previo['f_min_raw'])} &nbsp;–&nbsp; {_fecha_hora(resultado_previo['f_max_raw'])}",
        ))
    if resultado_posterior.get("ventana_restringida"):
        filas_periodos.append((
            "Ventana de análisis — posterior (seleccionada automáticamente, excluye tramo inestable)",
            f"{_fecha_hora(resultado_posterior['f_min_raw'])} &nbsp;–&nbsp; {_fecha_hora(resultado_posterior['f_max_raw'])}",
        ))
    filas_periodos += [
        ("Periodo de fechas VÁLIDO — previo a la gestión (excluye tramos cerrados/tandeo/falla)",
         f"{_fecha_hora(resultado_previo['f_min_valido'])} &nbsp;–&nbsp; {_fecha_hora(resultado_previo['f_max_valido'])}"),
        ("Periodo de fechas VÁLIDO — posterior a la gestión (excluye tramos cerrados/tandeo/falla)",
         f"{_fecha_hora(resultado_posterior['f_min_valido'])} &nbsp;–&nbsp; {_fecha_hora(resultado_posterior['f_max_valido'])}"),
    ]
    story.append(_tabla_kv(filas_periodos))
    if resultado_previo.get("ventana_restringida") or resultado_posterior.get("ventana_restringida"):
        story.append(Paragraph(
            "Cuando el archivo tiene un tramo largo con tandeos, fallas operacionales o cierres de "
            "válvula frecuentes, la plataforma selecciona automáticamente el tramo continuo más largo "
            "sin esos problemas y restringe todo el análisis (indicadores, MNF, N1, gráficas) a esa "
            "ventana, en vez de mezclarlo con el periodo inestable.",
            styles["Nota"]
        ))

    story.append(Paragraph("Horario considerado como gestión nocturna", styles["H2"]))
    story.append(Paragraph(
        "El horario nocturno no es una ventana de reloj fija: cada noche se delimita de forma "
        "dinámica dentro de ciclos de mediodía a mediodía. La tabla siguiente muestra el horario "
        "típico que resultó de ese cálculo en cada periodo.",
        styles["Cuerpo"]
    ))

    def _vn_txt(vn):
        if vn is None:
            return "No se pudo determinar (datos insuficientes)"
        return f"{vn['inicio']} – {vn['fin']} h &nbsp;(duración promedio {vn['duracion_h']:.1f} h, {vn['n_noches']} noches)"

    story.append(_tabla_kv([
        ("Horario nocturno típico — previo a la gestión", _vn_txt(resultado_previo.get("ventana_nocturna"))),
        ("Horario nocturno típico — posterior a la gestión", _vn_txt(resultado_posterior.get("ventana_nocturna"))),
    ]))

    story.append(Paragraph("Caudal nocturno, volumen y proyección", styles["H2"]))
    q_prom_previo = resultado_previo["q_prom"]
    q_prom_post = resultado_posterior["q_prom"]
    delta_q = q_prom_previo - q_prom_post
    vol_dia = delta_q * FACTOR_DIARIO_LPS_A_M3
    vol_anual = delta_q * FACTOR_ANUAL_LPS_A_M3
    story.append(_tabla_kv([
        ("Caudal promedio en horario nocturno — antes (lps)", _num(resultado_previo["nmf"])),
        ("Caudal promedio en horario nocturno — después (lps)", _num(resultado_posterior["nmf"])),
        ("Conversión a volumen — diferencia de caudal medio de 24h (m<super>3</super>/día)", _num(vol_dia, 1)),
        ("Proyección a un año (m<super>3</super>/año)", _num(vol_anual, 0)),
    ]))
    story.append(Paragraph(
        "La conversión a volumen y la proyección anual se calculan con la diferencia del caudal "
        "promedio de 24 horas entre ambos periodos (Q prom antes − Q prom después), no con el MNF "
        "nocturno extrapolado de forma plana, porque el porcentaje de ahorro nocturno no siempre "
        "coincide con el del resto del día.",
        styles["Nota"]
    ))

    n1_info = estimar_n1(resultado_previo["valles_nocturnos"], resultado_posterior["valles_nocturnos"])
    story.append(Paragraph("Exponente presión–caudal (N1)", styles["H2"]))
    if n1_info is not None:
        etiqueta_metodo = "regresión log-log" if n1_info["metodo"] == "regresion" else n1_info["metodo"]
        filas_n1 = [
            ("N1 estimado", f"{n1_info['n1']:.3f}"),
            ("Método", f"{etiqueta_metodo} ({n1_info['n_puntos']} noches)"),
        ]
        if n1_info["r2"] is not None:
            filas_n1.append(("R<super>2</super> de la regresión", f"{n1_info['r2']:.3f}"))
        story.append(_tabla_kv(filas_n1))
    else:
        story.append(Paragraph("No hay suficientes noches con presión y caudal válidos en ambos periodos para estimarlo.", styles["Cuerpo"]))

    story.append(Paragraph("Índice de Fugas de Infraestructura (ILI)", styles["H2"]))
    carl_uarl = estimar_carl_uarl(resultado_previo["nmf"], ili) if ili else None
    if carl_uarl is not None:
        story.append(Paragraph(
            "ILI = CARL / UARL (Lambert et al., metodología IWA de pérdidas de agua). CARL son las "
            "pérdidas reales anuales actuales y UARL el piso técnico de pérdidas inevitables de un "
            "sistema de ese tamaño, bien mantenido. Aquí, el CARL se aproxima con el MNF del periodo "
            "previo extrapolado de forma plana a un año (ver limitación más abajo); con el ILI "
            "ingresado por el usuario se despeja el UARL implícito.",
            styles["Cuerpo"]
        ))
        pct_margen = (vol_anual / carl_uarl["margen_teorico"] * 100) if carl_uarl["margen_teorico"] > 0 else None
        story.append(_tabla_kv([
            ("Índice de Fugas (ILI) ingresado por el usuario", f"{carl_uarl['ili']:.2f}"),
            ("CARL aproximado — pérdidas reales anuales actuales (m<super>3</super>/año)", _num(carl_uarl["carl_aprox"], 0)),
            ("UARL estimado — pérdidas reales anuales inevitables (m<super>3</super>/año)", _num(carl_uarl["uarl"], 0)),
            ("Margen teórico de reducción (CARL − UARL) (m<super>3</super>/año)", _num(carl_uarl["margen_teorico"], 0)),
            ("Volumen ya recuperado vs. margen teórico",
             f"{_num(vol_anual, 0)} m<super>3</super>/año ({pct_margen:.0f}% del margen)" if pct_margen is not None else "—"),
        ]))
    else:
        story.append(Paragraph(
            "No se ingresó un Índice de Fugas (ILI), así que esta sección se omite. Si lo ingresas en "
            "la aplicación, aquí se muestra el CARL aproximado, el UARL implícito y qué porcentaje del "
            "margen teórico de reducción ya se alcanzó con la gestión de presiones.",
            styles["Cuerpo"]
        ))

    story.append(PageBreak())

    story.append(Paragraph("Series de caudal", styles["H2"]))
    img_previo = _fig_a_imagen(graficar_serie(resultado_previo, "Previo a la gestión de presiones"))
    if img_previo is not None:
        story.append(img_previo)
    story.append(Spacer(1, 10))
    img_post = _fig_a_imagen(graficar_serie(resultado_posterior, "Posterior a la gestión de presiones"))
    if img_post is not None:
        story.append(img_post)

    img_n1 = _fig_a_imagen(graficar_n1(n1_info), ancho=14 * cm, alto=7 * cm)
    if img_n1 is not None:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Regresión N1 (presión–caudal)", styles["H2"]))
        story.append(img_n1)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#D9D9D9")))
    story.append(Paragraph("Limitaciones", styles["H2"]))
    story.append(Paragraph(
        "El MNF reportado es el caudal total mínimo de entrada al sector (consumo legítimo nocturno "
        "+ fuga, sin separar): no se cuenta con catastro de fugas por sector ni estudios de consumo "
        "nocturno por tipo de usuario que permitan aislar el componente de fuga con confianza. Por lo "
        "mismo, el CARL de esta sección es una aproximación, probablemente sobreestimada.",
        styles["Nota"]
    ))

    doc.build(story)
    return out_path


def mostrar_dashboard_comparativo(previo, posterior, ili=None):
    """Dashboard comparativo Previo/Posterior a gestión de presiones."""
    st.markdown("### Ahorro Estimado por Gestión de Presiones")

    delta_q = previo["q_prom"] - posterior["q_prom"]
    volumen_ahorrado_anual = delta_q * FACTOR_ANUAL_LPS_A_M3
    volumen_ahorrado_dia = delta_q * FACTOR_DIARIO_LPS_A_M3

    ca, cb, cc, cd = st.columns(4)

    kpi(ca, "MNF Previo (lps)", f"{previo['nmf']:.2f}" if previo["nmf"] is not None else "-")
    kpi(cb, "MNF Posterior (lps)", f"{posterior['nmf']:.2f}" if posterior["nmf"] is not None else "-")
    kpi(cc, "Volumen Ahorrado / día", f"{volumen_ahorrado_dia:,.1f} m³")
    kpi(cd, "Volumen Ahorrado Proyectado / año", f"{volumen_ahorrado_anual:,.0f} m³", clase_extra="kpi-ahorro")

    st.markdown(
        '<p style="font-size:12px; color:#64748B; margin-top:4px;">'
        'El volumen se calcula con la diferencia del caudal promedio de 24 horas entre ambos periodos '
        '(Q prom antes − Q prom después), no con la diferencia de MNF extrapolada de forma plana, '
        'porque el porcentaje de ahorro nocturno no siempre coincide con el del resto del día.</p>',
        unsafe_allow_html=True
    )

    n1_info = estimar_n1(previo["valles_nocturnos"], posterior["valles_nocturnos"])
    if n1_info is not None:
        etiqueta_metodo = "regresión log-log" if n1_info["metodo"] == "regresion" else n1_info["metodo"]
        texto_n1 = f"**Exponente N1 (presión–caudal) estimado:** {n1_info['n1']:.3f} ({etiqueta_metodo}, {n1_info['n_puntos']} noches)"
        if n1_info["r2"] is not None:
            texto_n1 += f" — R² = {n1_info['r2']:.3f}"
        st.markdown(texto_n1)
        fig_n1 = graficar_n1(n1_info)
        if fig_n1 is not None:
            st.plotly_chart(fig_n1, width="stretch", key="grafico_n1")

    if ili is not None and ili > 0:
        cu = estimar_carl_uarl(previo["nmf"], ili)
        if cu is not None:
            pct = (volumen_ahorrado_anual / cu["margen_teorico"] * 100) if cu["margen_teorico"] > 0 else None
            texto_ili = (
                f"**Índice de Fugas (ILI = {cu['ili']:.2f})** — CARL aproximado {cu['carl_aprox']:,.0f} m³/año, "
                f"UARL {cu['uarl']:,.0f} m³/año, margen teórico de reducción {cu['margen_teorico']:,.0f} m³/año"
            )
            if pct is not None:
                texto_ili += f" → ya se ha recuperado **{pct:.0f}%** de ese margen teórico."
            st.markdown(texto_ili)
            st.caption(
                "El CARL se aproxima con el MNF del periodo previo extrapolado de forma plana a un año; "
                "probablemente está sobreestimado porque no se separa el consumo legítimo nocturno de la "
                "fuga (ver Limitaciones en el PDF)."
            )

    pdf_path = generar_pdf_reporte(previo, posterior, ili=(ili if ili and ili > 0 else None))
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Descargar reporte PDF", data=f.read(),
            file_name="reporte_gestion_presiones.pdf", mime="application/pdf",
        )

    st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)

    st.markdown("### 📅 Previo a la gestión de presiones")
    mostrar_dashboard(previo, key_prefix="previo")

    st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)

    st.markdown("### 📅 Posterior a la gestión de presiones")
    mostrar_dashboard(posterior, key_prefix="posterior")


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.image("logo.png", width=160)
    st.markdown("""
Calcula automáticamente desde la hoja de excel de cualquier ConDor de SkyPlatform:
- **Presión aguas arriba** (bar)
- **Presión aguas abajo** (bar)
- **Caudal promedio** (lps)
- **Volumen total** ($m^3$)
- **MNF** (Minimum Night Flow)

Sube un solo archivo para ver sus indicadores, o sube **ambos** (previo y posterior a una gestión de presiones) para ver el ahorro proyectado.
    """)
    st.write("---")
    archivo_previo = st.file_uploader("Archivo Previo a la gestión de presiones", type=["xlsx"], key="archivo_previo")
    archivo_posterior = st.file_uploader("Archivo Posterior a la gestión de presiones", type=["xlsx"], key="archivo_posterior")
    ili_input = st.number_input(
        "Índice de Fugas (ILI) — opcional",
        min_value=0.0, value=0.0, step=0.1,
        help="Si ya conoces el ILI de este sector, escríbelo aquí: se usa para el contexto "
             "CARL/UARL del reporte PDF. No se calcula a partir de catastro de red.",
    )
    ejecutar_calculo = st.button("▶ Ejecutar cálculo")

# =====================================================
# INTERFAZ PRINCIPAL
# =====================================================

st.title("Dashboard de Indicadores en un DMA")

if archivo_previo is None and archivo_posterior is None:
    st.info("Carga uno o dos archivos desde el panel izquierdo y presiona 'Ejecutar cálculo'.")

if (archivo_previo is not None or archivo_posterior is not None) and ejecutar_calculo:
    if archivo_previo is not None and archivo_posterior is not None:
        resultado_previo = procesar_archivo(archivo_previo)
        resultado_posterior = procesar_archivo(archivo_posterior)
        mostrar_dashboard_comparativo(resultado_previo, resultado_posterior, ili=ili_input)
    else:
        archivo_unico = archivo_previo if archivo_previo is not None else archivo_posterior
        resultado = procesar_archivo(archivo_unico)
        mostrar_dashboard(resultado)

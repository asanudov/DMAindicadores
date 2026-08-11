import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import unicodedata
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
UMBRAL_P1 = 0.15          # bar. Por debajo de esto se considera "P1 en cero" (sector cerrado / sin presión)
FRAC_DIAS_TANDEO = 0.6     # fracción mínima de días del periodo que deben mostrar el evento para considerarlo recurrente
TOL_HORA_TANDEO = 2.0      # horas. Tolerancia de dispersión en la hora de inicio del evento para considerarlo "misma hora todos los días"
CV_DURACION_TANDEO = 0.5   # coeficiente de variación máximo de la duración de los eventos para considerarlos "misma duración"
MIN_DIAS_ANALISIS = 2      # con menos días no se puede evaluar recurrencia/periodicidad de forma confiable
VENTANA_PICO_MIN = 60      # minutos tras el cierre en que se busca el pico de apertura (tandeo)
UMBRAL_Q_CIERRE = 0.05     # lps. Caudal prácticamente exacto en 0 (más estricto que el umbral de tandeo/falla)
MIN_DURACION_CIERRE_MIN = 30  # minutos. Duración mínima para no confundir un cierre real con ruido de una sola lectura
PSI_A_BAR = 0.0689476      # factor de conversión 1 psi = 0.0689476 bar
UMBRAL_PSI_DETECCION = 25  # bar. Si el promedio de una serie de presión supera esto, se asume que viene en psi y se convierte
FACTOR_ANUAL_LPS_A_M3 = 3600 * 24 * 365 / 1000  # convierte una diferencia de caudal sostenida (lps) a m³/año
FACTOR_DIARIO_LPS_A_M3 = 3600 * 24 / 1000       # convierte una diferencia de caudal sostenida (lps) a m³/día
MIN_NOCHES_REGRESION_N1 = 4  # mínimo de noches (con Q y P2 válidos, combinando ambos periodos) para ajustar N1 por regresión
# =====================================================
# FUNCIONES DE APOYO
# =====================================================
def normalizar(texto):
    if pd.isna(texto): return ""
    texto = str(texto).strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto
def clasificar_variable(var):
    v = normalizar(var)
    if "p1" in v or "presion 1" in v or "aguas arriba" in v: return "P1"
    if "p2" in v or "presion 2" in v or "aguas abajo" in v: return "P2"
    if "q" in v or "caudal" in v: return "Q"
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
    r = min(np.sqrt(sin_m**2 + cos_m**2), 0.9999)
    if r <= 0:
        return np.inf
    return np.sqrt(-2 * np.log(r)) / (2 * np.pi) * 24
def clasificar_patron(eventos, dias_totales):
    """
    Devuelve: "sin_eventos", "tandeo" o "falla_operacional".
    Tandeo    -> P1 cae a 0 de forma recurrente y a horas similares todos los días (patrón/periodicidad).
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
    Detecta el valle nocturno de caudal en cada ciclo mediodía-a-mediodía (mismo criterio que el MNF:
    se ubica el mínimo del caudal suavizado y se expande mientras se mantenga por debajo del promedio
    del ciclo). Devuelve un DataFrame con una fila por noche válida:
      - fecha_ciclo: fecha del ciclo noche-mañana
      - Q_valle: caudal mínimo real (sin suavizar) dentro del tramo detectado (= el valor que usa el MNF)
      - P2_valle: presión aguas abajo promedio durante ESE MISMO tramo horario (si se pasa p2_abierto)
    P2_valle permite, junto con Q_valle, estimar el exponente presión-caudal N1 (q = c·P^N1) cuando se
    comparan dos periodos (antes/después de gestión de presiones), en vez de solo comparar caudales.
    """
    if q_abierto.empty:
        return pd.DataFrame(columns=["fecha_ciclo", "Q_valle", "P2_valle"])
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
        p2_valle = np.nan
        if p2_abierto is not None and not p2_abierto.empty:
            t_ini, t_fin = grupo.loc[ini, "FechaHora"], grupo.loc[fin, "FechaHora"]
            ventana_p2 = p2_abierto[(p2_abierto["FechaHora"] >= t_ini) & (p2_abierto["FechaHora"] <= t_fin)]
            if not ventana_p2.empty:
                p2_valle = float(ventana_p2["Valor"].mean())
        filas.append({"fecha_ciclo": fecha_ciclo, "Q_valle": float(valle.min()), "P2_valle": p2_valle})
    return pd.DataFrame(filas)
def calcular_mnf(q_abierto):
    """
    MNF = media aritmética del caudal mínimo de cada 'valle nocturno' (ver calcular_valles_nocturnos).
    Se mantiene como función independiente por compatibilidad; el detalle noche a noche (con su
    presión asociada) vive en calcular_valles_nocturnos, que es lo que usa la comparación antes/después.
    """
    valles = calcular_valles_nocturnos(q_abierto)
    if valles.empty:
        return None
    return float(valles["Q_valle"].mean())
def estimar_n1(valles_previo, valles_posterior, min_puntos=MIN_NOCHES_REGRESION_N1):
    """
    Estima el exponente presión-caudal N1 (q = c·P^N1) a partir de los pares (Q_valle, P2_valle) de
    cada noche, en ambos periodos.
      - Con >= min_puntos noches válidas (Q y P2 disponibles) combinando los dos periodos, se ajusta
        una regresión log-log: ln(Q) = N1·ln(P) + b (método más robusto, se reporta R²).
      - Con menos noches pero al menos una válida en cada periodo, se calcula un N1 "de 2 puntos"
        usando el promedio de cada periodo (sin R², marcado como aproximado).
      - Si no hay suficiente información (p.ej. no se pudo emparejar presión con los valles), devuelve None.
    """
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
    # Detección de eventos de P1≈0 y clasificación de patrón (tandeo vs falla operacional)
    dias_totales = df_raw["FechaHora"].dt.date.nunique()
    eventos_p1 = construir_eventos_cero(p1, UMBRAL_P1)
    patron = clasificar_patron(eventos_p1, dias_totales)
    es_tandeo = patron == "tandeo"
    hay_falla_operacional = patron == "falla_operacional"
    # Cierres de válvula por condición de trabajo fuera de rango: Q≈0 sostenido con P1 normal.
    # Distinto de tandeo/falla (esos son P1≈0). Solo afecta a Q, no a P1/P2 (esas presiones siguen siendo válidas).
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
        f_min = q["FechaHora"].min().strftime('%d/%m/%Y')
        f_max = q["FechaHora"].max().strftime('%d/%m/%Y')
    else:
        volumen = 0.0
        f_min = f_max = "-/-/-"
    # Valles nocturnos: caudal mínimo (MNF) + presión aguas abajo asociada a cada noche, sobre los
    # tramos "abiertos". Es la base tanto del MNF (como antes) como de la estimación de N1 cuando se
    # comparan dos periodos (ver estimar_n1 / mostrar_dashboard_comparativo).
    valles_nocturnos = calcular_valles_nocturnos(q_abierto, p2_abierto)
    nmf = float(valles_nocturnos["Q_valle"].mean()) if not valles_nocturnos.empty else None
    return {
        "p1_prom": p1_prom, "p2_prom": p2_prom, "q_prom": q_prom, "volumen": volumen,
        "nmf": nmf, "f_min": f_min, "f_max": f_max,
        "es_tandeo": es_tandeo, "hay_falla_operacional": hay_falla_operacional,
        "hay_cierre_valvula": hay_cierre_valvula, "hay_conversion_psi": hay_conversion_psi,
        "p1_fue_psi": p1_fue_psi, "p2_fue_psi": p2_fue_psi,
        "eventos_p1": eventos_p1, "eventos_valvula": eventos_valvula,
        "dias_totales": dias_totales, "q_pico_apertura": q_pico_apertura,
        "q": q, "valles_nocturnos": valles_nocturnos,
    }
def kpi(col, t, v, clase_extra=""):
    col.markdown(f'<div class="kpi-box {clase_extra}"><div class="kpi-title">{t}</div><div class="kpi-value">{v}</div></div>', unsafe_allow_html=True)
def mostrar_dashboard(r, key_prefix=""):
    """Renderiza alertas + KPIs + tabla resumen + gráfico para un resultado de procesar_archivo()."""
    st.markdown("### Indicadores del Sector")
    if r["es_tandeo"]:
        frac_dias = r["eventos_p1"]["fecha"].nunique() / r["dias_totales"]
        hora_prom = r["eventos_p1"]["hora_inicio"].mean()
        st.markdown(
            f'<div class="alerta-tandeo">🔄 Suministro Intermitente (Tandeo detectado — patrón recurrente en '
            f'{frac_dias*100:.0f}% de los días, cierre habitual ~{hora_prom:.0f}:00 h)</div>',
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
    # Cambiamos dinámicamente el título del KPI si hay tandeo para alertar sobre el pico
    if r["es_tandeo"] and r["q_pico_apertura"] is not None:
        kpi(c5, "Q Pico Apertura (lps)", f"{r['q_pico_apertura']:.2f}")
    else:
        kpi(c5, "MNF (lps)", f"{r['nmf']:.2f}" if r["nmf"] is not None else "-")
    c6.markdown(
        f'<div class="kpi-periodo"><div class="kpi-title">Periodo</div><div class="kpi-value">{r["f_min"]}<br>–<br>{r["f_max"]}</div></div>',
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
    with col_grafico:
        fig = go.Figure()
        q = r["q"]
        if not q.empty:
            fig.add_trace(go.Scatter(x=q["FechaHora"], y=q["Valor"], mode="lines", name="Q", line=dict(width=2, color="blue")))
            fig.add_trace(go.Scatter(x=[q["FechaHora"].min(), q["FechaHora"].max()], y=[r["q_prom"], r["q_prom"]], mode="lines", name="Q prom", line=dict(width=1.5, color="red", dash="dot")))
            if r["nmf"] is not None:
                fig.add_trace(go.Scatter(x=[q["FechaHora"].min(), q["FechaHora"].max()], y=[r["nmf"], r["nmf"]], mode="lines", name="MNF", line=dict(width=2, color="green", dash="dash")))
            if r["es_tandeo"] and r["q_pico_apertura"] is not None:
                fig.add_trace(go.Scatter(x=[q["FechaHora"].min(), q["FechaHora"].max()], y=[r["q_pico_apertura"], r["q_pico_apertura"]], mode="lines", name="Pico de Apertura", line=dict(width=1.5, color="purple", dash="longdashdot")))
            # Sombreado de los tramos "cerrados" (P1≈0) excluidos del cálculo, para validar visualmente la clasificación
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
            # Sombreado de cierres de válvula (Q≈0 con P1 normal) excluidos de Q prom / MNF
            if not r["eventos_valvula"].empty:
                for i, (_, ev) in enumerate(r["eventos_valvula"].iterrows()):
                    fig.add_vrect(
                        x0=ev["inicio"], x1=ev["fin"],
                        fillcolor="rgba(255,153,0,0.20)", opacity=0.6, line_width=0,
                        annotation_text="Cierre de válvula" if i == 0 else None,
                        annotation_position="bottom left"
                    )
        fig.update_layout(
            height=460,
            margin=dict(t=10, b=10, l=10, r=10),
            hovermode="x unified",
            xaxis=dict(rangeslider=dict(visible=True), type="date"),
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True, key=f"grafico_{key_prefix}")
def mostrar_dashboard_comparativo(previo, posterior):
    """
    Dashboard comparativo Previo/Posterior a gestión de presiones.

    Metodología (actualizada):
    - El volumen recuperado se estima con la diferencia del CAUDAL PROMEDIO de 24h medido en cada
      periodo (Q prom, ya calculado por procesar_archivo), no con la diferencia de MNF extrapolada
      de forma plana. Extrapolar el MNF asume que el % de ahorro nocturno se sostiene igual las 24h,
      lo cual no siempre es cierto (p.ej. si en el periodo "previo" la presión diurna ya caía sola por
      fricción/consumo, el margen de ahorro de día es distinto al de noche). Comparar directamente el
      caudal de entrada medido evita esa suposición.
    - El MNF se conserva como indicador de diagnóstico de pérdidas reales nocturnas (más "limpio" que
      el caudal de 24h porque el consumo legítimo nocturno es mínimo y estable), pero ya no se usa
      para proyectar el volumen anual.
    - Se estima el exponente presión-caudal N1 (q = c·P^N1) con los pares caudal/presión de cada valle
      nocturno de ambos periodos, como verificación cruzada: la reducción de caudal nocturno medida
      debería ser consistente con la que predice N1 a partir de la reducción de presión aplicada.
    """
    st.markdown("### Ahorro Estimado por Gestión de Presiones")

    q_prom_previo = previo.get("q_prom")
    q_prom_post = posterior.get("q_prom")
    if q_prom_previo is not None and q_prom_post is not None:
        delta_q = q_prom_previo - q_prom_post
        volumen_diario = delta_q * FACTOR_DIARIO_LPS_A_M3
        volumen_anual = delta_q * FACTOR_ANUAL_LPS_A_M3
    else:
        delta_q = volumen_diario = volumen_anual = None

    delta_mnf = None
    if previo["nmf"] is not None and posterior["nmf"] is not None:
        delta_mnf = previo["nmf"] - posterior["nmf"]

    n1_info = estimar_n1(previo.get("valles_nocturnos"), posterior.get("valles_nocturnos"))

    ca, cb, cc, cd = st.columns(4)
    kpi(ca, "Q prom Previo (lps)", f"{q_prom_previo:.2f}" if q_prom_previo is not None else "-")
    kpi(cb, "Q prom Posterior (lps)", f"{q_prom_post:.2f}" if q_prom_post is not None else "-")
    kpi(cc, "ΔQ prom (lps)", f"{delta_q:.2f}" if delta_q is not None else "-")
    kpi(cd, "Volumen Ahorrado Proyectado / año", f"{volumen_anual:,.0f} m³" if volumen_anual is not None else "-", clase_extra="kpi-ahorro")

    if volumen_diario is not None:
        nota_vol = (
            'Estimado con la diferencia del caudal promedio de 24h medido en ambos periodos '
            f'(≈{volumen_diario:,.1f} m³/día extrapolado a un año). Se usa el caudal medio y no solo el MNF '
            'porque la reducción porcentual nocturna no siempre es igual a la del resto del día — comparar '
            'directamente el caudal de entrada medido es más robusto cuando se cuenta con registro continuo '
            'de 24h en ambos periodos.'
        )
    else:
        nota_vol = 'No fue posible calcular el caudal promedio en alguno de los dos periodos.'
    st.markdown(f'<p style="font-size:12px; color:#64748B; margin-top:4px;">{nota_vol}</p>', unsafe_allow_html=True)

    ce, cf, cg, ch = st.columns(4)
    kpi(ce, "MNF Previo (lps)", f"{previo['nmf']:.2f}" if previo["nmf"] is not None else "-")
    kpi(cf, "MNF Posterior (lps)", f"{posterior['nmf']:.2f}" if posterior["nmf"] is not None else "-")
    kpi(cg, "ΔMNF (lps)", f"{delta_mnf:.2f}" if delta_mnf is not None else "-")
    if n1_info is not None:
        etiqueta_n1 = f"N1 ≈ {n1_info['n1']:.2f}"
        if n1_info["r2"] is not None:
            etiqueta_n1 += f" (R²={n1_info['r2']:.2f}, {n1_info['n_puntos']} noches)"
        else:
            etiqueta_n1 += f" ({n1_info['metodo']})"
        kpi(ch, "Exponente N1 (presión–caudal)", etiqueta_n1)
    else:
        kpi(ch, "Exponente N1 (presión–caudal)", "-")

    st.markdown(
        '<p style="font-size:12px; color:#64748B; margin-top:4px;">'
        'MNF = diagnóstico de pérdidas reales nocturnas (ya no se usa para proyectar el volumen anual). '
        'N1 = exponente de la relación caudal-presión (q = c·P^N1), estimado con los pares caudal/presión '
        'de cada valle nocturno de ambos periodos; sirve para verificar que la reducción de caudal medida '
        'es consistente con la reducción de presión aplicada.'
        '</p>', unsafe_allow_html=True
    )

    # Verificación cruzada: reducción nocturna medida vs. la que predice N1 a partir del cambio de presión
    if n1_info is not None and previo["nmf"] and posterior["nmf"]:
        datos_n1 = n1_info["datos"]
        p_prev_avg = datos_n1.loc[datos_n1["Periodo"] == "Previo", "P2_valle"].mean()
        p_post_avg = datos_n1.loc[datos_n1["Periodo"] == "Posterior", "P2_valle"].mean()
        if pd.notna(p_prev_avg) and pd.notna(p_post_avg) and p_prev_avg > 0:
            reduccion_medida = 1 - (posterior["nmf"] / previo["nmf"])
            reduccion_teorica = 1 - (p_post_avg / p_prev_avg) ** n1_info["n1"]
            st.markdown(
                f'<p style="font-size:12px; color:#64748B;">Verificación: reducción nocturna medida '
                f'{reduccion_medida*100:.1f}% vs. teórica según N1 {reduccion_teorica*100:.1f}% '
                f'(deberían ser cercanas; si difieren mucho, revisar la calidad del dato de presión o si '
                f'los periodos comparados son realmente representativos).</p>',
                unsafe_allow_html=True
            )

    # Gráfico de la regresión N1 (solo si se pudo ajustar por regresión, no en el caso "2 puntos")
    if n1_info is not None and n1_info["metodo"] == "regresion":
        datos_n1 = n1_info["datos"]
        fig_n1 = go.Figure()
        colores = {"Previo": "#2A78D6", "Posterior": "#EB6834"}
        for periodo, color in colores.items():
            sub = datos_n1[datos_n1["Periodo"] == periodo]
            if sub.empty:
                continue
            fig_n1.add_trace(go.Scatter(
                x=np.log(sub["P2_valle"]), y=np.log(sub["Q_valle"]),
                mode="markers", name=periodo, marker=dict(color=color, size=8)
            ))
        x_vals = np.log(datos_n1["P2_valle"])
        x_line = np.linspace(x_vals.min(), x_vals.max(), 20)
        y_line = n1_info["n1"] * x_line + n1_info["intercepto"]
        fig_n1.add_trace(go.Scatter(x=x_line, y=y_line, mode="lines", name="Ajuste N1", line=dict(color="#475569", dash="dash")))
        fig_n1.update_layout(
            height=280, margin=dict(t=30, b=10, l=10, r=10),
            title="N1 — ln(Q valle nocturno) vs ln(P aguas abajo valle nocturno)",
            xaxis_title="ln(P aguas abajo)", yaxis_title="ln(Q)",
            legend=dict(orientation="h", y=1.25, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig_n1, use_container_width=True, key="grafico_n1")

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
    Sube un solo archivo para ver sus indicadores, o sube **ambos** (previo y posterior a una gestión de presiones) para ver el ahorro proyectado, calculado con la diferencia de caudal promedio de 24h y verificado con el exponente presión-caudal N1.
    """)
    st.write("---")
    archivo_previo = st.file_uploader("Archivo Previo a la gestión de presiones", type=["xlsx"], key="archivo_previo")
    archivo_posterior = st.file_uploader("Archivo Posterior a la gestión de presiones", type=["xlsx"], key="archivo_posterior")
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
        mostrar_dashboard_comparativo(resultado_previo, resultado_posterior)
    else:
        archivo_unico = archivo_previo if archivo_previo is not None else archivo_posterior
        resultado = procesar_archivo(archivo_unico)
        mostrar_dashboard(resultado)

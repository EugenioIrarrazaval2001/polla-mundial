import os
import re
import json
import sys
import unicodedata
from openpyxl import Workbook, load_workbook
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA = BASE_DIR

OUTPUT_DIR = os.path.join(BASE_DIR, "site")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CALENDARIO_PATH = os.path.join(BASE_DIR, "Calendario_Mundial.xlsx")

CELDA_INICIAL_RESULTADO = "B4"   # donde parte el partido 1
COL_MODO = "D"                   # en eliminatorias, el "cómo pasa" está en C4, C8, C12...
SALTO_FILAS = 4                  # cada partido está 4 filas más abajo

# Etapas:
# - tipo "GRUPOS": 1 celda por partido (resultado)
# - tipo "ELIM": 2 celdas por partido (pasa + modo)
ETAPAS = {
    "E01": {"tipo": "GRUPOS", "n_partidos": 25, "ppp": 1},
    "E02": {"tipo": "ELIM",   "n_partidos": 16, "ppp": 1},
    "E03": {"tipo": "ELIM",   "n_partidos": 8,  "ppp": 1},
    "E04": {"tipo": "ELIM",   "n_partidos": 4,  "ppp": 2},
    "E05": {"tipo": "ELIM",   "n_partidos": 2,  "ppp": 2},
    "E06": {"tipo": "ELIM",   "n_partidos": 1,  "ppp": 3},
}
ETIQUETAS_ETAPAS = {
    "E01": "Grupos",
    "E02": "16avos",
    "E03": "Octavos",
    "E04": "Cuartos",
    "E05": "Semis",
    "E06": "Final",
}
CALENDARIO_HOJAS = [
    ("E01", "E01_Grupos"),
    ("E02", "E02_16avos"),
    ("E03", "E03_Octavos"),
    ("E04", "E04_Cuartos"),
    ("E05", "E05_Semis"),
    ("E06", "E06_Final"),
]
CALENDARIO_HEADERS = [
    "numero_partido",
    "equipo_a",
    "equipo_b",
    "fecha_chile",
    "hora_chile",
    "datetime_chile_iso",
    "sede",
    "notas",
]
CALENDARIO_E01_INICIAL = [
    (1, "México", "Sudáfrica", "2026-06-11", "15:00", "2026-06-11T15:00:00-04:00"),
    (2, "Estados Unidos", "Paraguay", "2026-06-12", "21:00", "2026-06-12T21:00:00-04:00"),
    (3, "Brasil", "Marruecos", "2026-06-13", "18:00", "2026-06-13T18:00:00-04:00"),
    (4, "Australia", "Turquía", "2026-06-14", "00:00", "2026-06-14T00:00:00-04:00"),
    (5, "Holanda", "Japón", "2026-06-14", "16:00", "2026-06-14T16:00:00-04:00"),
    (6, "Bélgica", "Egipto", "2026-06-15", "15:00", "2026-06-15T15:00:00-04:00"),
    (7, "Francia", "Senegal", "2026-06-16", "15:00", "2026-06-16T15:00:00-04:00"),
    (8, "Argentina", "Argelia", "2026-06-16", "21:00", "2026-06-16T21:00:00-04:00"),
    (9, "Inglaterra", "Croacia", "2026-06-17", "16:00", "2026-06-17T16:00:00-04:00"),
    (10, "México", "Corea", "2026-06-18", "21:00", "2026-06-18T21:00:00-04:00"),
    (11, "Estados Unidos", "Australia", "2026-06-19", "15:00", "2026-06-19T15:00:00-04:00"),
    (12, "Holanda", "Suecia", "2026-06-20", "13:00", "2026-06-20T13:00:00-04:00"),
    (13, "Bélgica", "Irán", "2026-06-21", "15:00", "2026-06-21T15:00:00-04:00"),
    (14, "Argentina", "Austria", "2026-06-22", "13:00", "2026-06-22T13:00:00-04:00"),
    (15, "Noruega", "Senegal", "2026-06-22", "20:00", "2026-06-22T20:00:00-04:00"),
    (16, "Suiza", "Canadá", "2026-06-24", "15:00", "2026-06-24T15:00:00-04:00"),
    (17, "Ecuador", "Alemania", "2026-06-25", "16:00", "2026-06-25T16:00:00-04:00"),
    (18, "Japón", "Suecia", "2026-06-25", "19:00", "2026-06-25T19:00:00-04:00"),
    (19, "Turquía", "Estados Unidos", "2026-06-25", "22:00", "2026-06-25T22:00:00-04:00"),
    (20, "Paraguay", "Australia", "2026-06-25", "22:00", "2026-06-25T22:00:00-04:00"),
    (21, "Uruguay", "España", "2026-06-26", "20:00", "2026-06-26T20:00:00-04:00"),
    (22, "Noruega", "Francia", "2026-06-26", "15:00", "2026-06-26T15:00:00-04:00"),
    (23, "Egipto", "Irán", "2026-06-26", "23:00", "2026-06-26T23:00:00-04:00"),
    (24, "Argelia", "Austria", "2026-06-27", "22:00", "2026-06-27T22:00:00-04:00"),
    (25, "Colombia", "Portugal", "2026-06-27", "19:30", "2026-06-27T19:30:00-04:00"),
]
DIAS_DISPLAY = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_DISPLAY = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}

def clave_orden_etapa(etapa):
    m = re.match(r"^E(\d{2})$", str(etapa).upper())
    return int(m.group(1)) if m else 9999


def etiqueta_etapa_larga(etapa):
    nombre = ETIQUETAS_ETAPAS.get(etapa, etapa)
    if str(etapa).upper() == "E01":
        nombre = "Fase de grupos"
    return nombre


def texto_celda(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def hoja_calendario_vacia(ws):
    for row in ws.iter_rows():
        for cell in row:
            if texto_celda(cell.value):
                return False
    return True


def calendario_tiene_filas_datos(ws):
    for row in ws.iter_rows(min_row=2, values_only=True):
        if any(texto_celda(valor) for valor in row):
            return True
    return False


def asegurar_headers_calendario(ws):
    if hoja_calendario_vacia(ws):
        ws.append(CALENDARIO_HEADERS)
        return True
    return False


def agregar_e01_inicial_si_corresponde(ws):
    if calendario_tiene_filas_datos(ws):
        return False

    for numero, equipo_a, equipo_b, fecha, hora, iso in CALENDARIO_E01_INICIAL:
        ws.append([numero, equipo_a, equipo_b, fecha, hora, iso, "", ""])
    return True


def normalizar_numero_partido(valor):
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        numero = int(valor)
        return numero if numero == valor or float(numero) == float(valor) else None

    texto = texto_celda(valor)
    if not texto:
        return None
    m = re.search(r"\d+", texto)
    return int(m.group(0)) if m else None


def normalizar_fecha_calendario(valor):
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, date):
        return valor.strftime("%Y-%m-%d")

    texto = texto_celda(valor)
    if not texto:
        return ""

    formatos = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y")
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return texto


def normalizar_hora_calendario(valor):
    if isinstance(valor, datetime):
        return valor.strftime("%H:%M")
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 0 <= valor < 1:
            minutos = int(round(valor * 24 * 60))
            horas = (minutos // 60) % 24
            mins = minutos % 60
            return f"{horas:02d}:{mins:02d}"
        if 0 <= valor < 24:
            horas = int(valor)
            mins = int(round((valor - horas) * 60))
            return f"{horas:02d}:{mins:02d}"

    texto = texto_celda(valor)
    if not texto:
        return ""
    m = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", texto)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return texto


def parse_datetime_iso_calendario(valor):
    if isinstance(valor, datetime):
        dt = valor
    else:
        texto = texto_celda(valor)
        if not texto:
            return None
        try:
            dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("America/Santiago"))
    return dt


def normalizar_iso_calendario(valor):
    dt = parse_datetime_iso_calendario(valor)
    if dt:
        return dt.isoformat(timespec="seconds")
    return texto_celda(valor)


def construir_iso_calendario(fecha_chile, hora_chile):
    if not fecha_chile or not hora_chile:
        return ""
    try:
        dt = datetime.strptime(f"{fecha_chile} {hora_chile}", "%Y-%m-%d %H:%M")
    except ValueError:
        return ""
    dt = dt.replace(tzinfo=ZoneInfo("America/Santiago"))
    return dt.isoformat(timespec="seconds")


def datetime_calendario_para_display(fecha_chile, hora_chile, datetime_chile_iso):
    dt = parse_datetime_iso_calendario(datetime_chile_iso)
    if dt:
        return dt
    if fecha_chile and hora_chile:
        try:
            return datetime.strptime(f"{fecha_chile} {hora_chile}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    return None


def formatear_fecha_hora_display(fecha_chile, hora_chile, datetime_chile_iso):
    dt = datetime_calendario_para_display(fecha_chile, hora_chile, datetime_chile_iso)
    if not dt:
        return "Horario por confirmar"

    hora_display = hora_chile or dt.strftime("%H:%M")
    mes_display = MESES_DISPLAY.get(dt.month, "")
    return f"{DIAS_DISPLAY[dt.weekday()]} {dt.day} {mes_display} · {hora_display}"


def preparar_y_cargar_calendario():
    if os.path.exists(CALENDARIO_PATH):
        wb = load_workbook(CALENDARIO_PATH)
        cambiado = False
    else:
        wb = Workbook()
        wb.active.title = CALENDARIO_HOJAS[0][1]
        cambiado = True

    for idx, (etapa, nombre_hoja) in enumerate(CALENDARIO_HOJAS):
        if nombre_hoja in wb.sheetnames:
            ws = wb[nombre_hoja]
        else:
            ws = wb.create_sheet(title=nombre_hoja, index=idx)
            cambiado = True

        if asegurar_headers_calendario(ws):
            cambiado = True
        if etapa == "E01" and agregar_e01_inicial_si_corresponde(ws):
            cambiado = True

    if cambiado:
        wb.save(CALENDARIO_PATH)

    calendario = {etapa: {} for etapa, _ in CALENDARIO_HOJAS}
    hoja_por_etapa = dict(CALENDARIO_HOJAS)

    for etapa, nombre_hoja in hoja_por_etapa.items():
        if nombre_hoja not in wb.sheetnames:
            continue

        ws = wb[nombre_hoja]
        headers = {
            texto_celda(cell.value).lower(): idx
            for idx, cell in enumerate(ws[1])
            if texto_celda(cell.value)
        }
        if "numero_partido" not in headers:
            continue

        def valor_columna(row, nombre):
            idx = headers.get(nombre)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(texto_celda(valor) for valor in row):
                continue

            numero = normalizar_numero_partido(valor_columna(row, "numero_partido"))
            if numero is None:
                continue

            fecha_chile = normalizar_fecha_calendario(valor_columna(row, "fecha_chile"))
            hora_chile = normalizar_hora_calendario(valor_columna(row, "hora_chile"))
            datetime_chile_iso = normalizar_iso_calendario(valor_columna(row, "datetime_chile_iso"))
            if not datetime_chile_iso and fecha_chile and hora_chile:
                datetime_chile_iso = construir_iso_calendario(fecha_chile, hora_chile)

            calendario[etapa][numero] = {
                "equipo_a": texto_celda(valor_columna(row, "equipo_a")),
                "equipo_b": texto_celda(valor_columna(row, "equipo_b")),
                "fecha_chile": fecha_chile,
                "hora_chile": hora_chile,
                "datetime_chile_iso": datetime_chile_iso,
                "fecha_hora_display": formatear_fecha_hora_display(
                    fecha_chile,
                    hora_chile,
                    datetime_chile_iso,
                ),
                "sort_key": datetime_chile_iso,
                "sede": texto_celda(valor_columna(row, "sede")),
                "notas": texto_celda(valor_columna(row, "notas")),
            }

    return calendario

# ============================================================
# BONUS CAMPEÓN
# - Cada participante escribe en B4 de su archivo E01 su campeón.
# - El campeón real OFICIAL se lee desde B4 del archivo de pauta E01.
# - CAMPEON_REAL_MANUAL queda solo como fallback opcional.
# ============================================================
BONUS_PTS = 5
NOMBRE_COLUMNA_BONUS = "Bono Campeón"
CAMPEON_REAL_MANUAL = None


# ============================================================
# DETECCIÓN DE ETAPA / PARTICIPANTE
# ============================================================
def extraer_etapa_desde_texto(texto):
    limpio = str(texto).strip()

    # E01 / E1 / e01
    m = re.search(r"(?i)\bE\s*0*(\d{1,2})\b", limpio)
    if m:
        etapa = f"E{int(m.group(1)):02d}"
        return etapa if etapa in ETAPAS else None

    # etapa 01 / etapa_1 / Etapa-02
    m = re.search(r"(?i)\bETAPA\D*0*(\d{1,2})\b", limpio)
    if m:
        etapa = f"E{int(m.group(1)):02d}"
        return etapa if etapa in ETAPAS else None

    # Solo número: 01 / 1
    m = re.fullmatch(r"0*(\d{1,2})", limpio)
    if m:
        etapa = f"E{int(m.group(1)):02d}"
        return etapa if etapa in ETAPAS else None

    return None


def extraer_etapa_desde_nombre(fn):
    base = os.path.splitext(os.path.basename(fn))[0]
    # En pauta permitimos prefijos tipo E01Pauta.xlsx (sin separador).
    m = re.match(r"(?i)^E\s*0*(\d{1,2})", base)
    if m:
        etapa = f"E{int(m.group(1)):02d}"
        return etapa if etapa in ETAPAS else None
    return extraer_etapa_desde_texto(base)


def extraer_etapa_desde_ruta_participante(ruta_excel, carpeta_participantes):
    carpeta_archivo = os.path.dirname(os.path.abspath(ruta_excel))
    rel = os.path.relpath(carpeta_archivo, os.path.abspath(carpeta_participantes))
    if rel in (".", ""):
        return None

    partes = rel.split(os.sep)
    for parte in reversed(partes):
        etapa = extraer_etapa_desde_texto(parte)
        if etapa:
            return etapa
    return None


def nombre_participante_desde_archivo(ruta_excel):
    base = os.path.splitext(os.path.basename(ruta_excel))[0]
    # Acepta nombres simples con guiones/guiones bajos.
    nombre = re.sub(r"[_-]+", " ", base)
    nombre = re.sub(r"\s+", " ", nombre).strip()
    return nombre


def id_participante(nombre):
    # ID estable derivada del nombre de archivo (sin convención antigua).
    return normalizar_texto(nombre)


def resolver_carpeta_por_nombre(carpeta_base, nombre_objetivo):
    objetivo = str(nombre_objetivo).strip().lower()
    for nombre in os.listdir(carpeta_base):
        ruta = os.path.join(carpeta_base, nombre)
        if os.path.isdir(ruta) and nombre.lower() == objetivo:
            return ruta
    raise FileNotFoundError(
        f"No encontré la carpeta '{nombre_objetivo}' dentro de: {carpeta_base}"
    )


def resolver_carpeta_pauta(carpeta_base):
    # Busca "pauta" sin depender de mayúsculas/minúsculas.
    return resolver_carpeta_por_nombre(carpeta_base, "Pauta")


def cargar_pautas_desde_excel(carpeta_pauta):
    archivos_excel = sorted(
        fn for fn in os.listdir(carpeta_pauta)
        if fn.lower().endswith(".xlsx") and not fn.startswith("~$")
    )
    if not archivos_excel:
        raise FileNotFoundError(
            f"La carpeta de pauta está vacía o no tiene .xlsx: {carpeta_pauta}"
        )

    pautas = {}
    fuentes = {}
    ignorados = []
    enfrentamientos = {}
    enfrentamientos_detalle = {}
    campeon_real_pauta = None

    for fn in archivos_excel:
        etapa = extraer_etapa_desde_nombre(fn)
        if etapa is None:
            ignorados.append(fn)
            continue
        if etapa not in ETAPAS:
            ignorados.append(fn)
            continue
        if etapa in pautas:
            raise ValueError(
                f"Hay más de una pauta para {etapa}: '{fuentes[etapa]}' y '{fn}'. "
                "Deja solo un archivo por etapa en la carpeta pauta."
            )

        ruta_excel = os.path.join(carpeta_pauta, fn)
        cfg = ETAPAS[etapa]
        wb = load_workbook(ruta_excel, data_only=True)
        ws = wb.active

        if etapa == "E01":
            campeon_real_pauta = ws["B4"].value

        if cfg["tipo"] == "GRUPOS":
            pauta_etapa = leer_celdas_resultado(ws, cfg["n_partidos"])
        elif cfg["tipo"] == "ELIM":
            pauta_etapa = leer_celdas_eliminatoria(ws, cfg["n_partidos"])
        else:
            raise ValueError(f"Tipo de etapa desconocido: {cfg['tipo']}")
        enfrentamientos_detalle_etapa = leer_enfrentamientos_etapa_detalle(ws, cfg)
        enfrentamientos_etapa = [p["nombre"] for p in enfrentamientos_detalle_etapa]

        if len(pauta_etapa) != cfg["n_partidos"]:
            raise ValueError(
                f"La pauta {fn} ({etapa}) no tiene {cfg['n_partidos']} partidos."
            )

        pautas[etapa] = pauta_etapa
        fuentes[etapa] = fn
        enfrentamientos[etapa] = enfrentamientos_etapa
        enfrentamientos_detalle[etapa] = enfrentamientos_detalle_etapa

    if not pautas:
        raise ValueError(
            f"No pude cargar pautas válidas desde: {carpeta_pauta}. "
            "Asegúrate de usar archivos cuyo nombre comience por etapa (ej: E01...)."
        )

    faltantes = [e for e in sorted(ETAPAS.keys()) if e not in pautas]
    return pautas, fuentes, faltantes, ignorados, enfrentamientos, campeon_real_pauta, enfrentamientos_detalle


def cargar_archivos_pronostico(carpeta_participantes):
    registros = []
    avisos = []
    etapas_con_carpeta = set()
    conteo_por_etapa = {}

    for raiz, dirs, files in os.walk(carpeta_participantes):
        dirs.sort()
        files = sorted(files)

        etapa_en_raiz = extraer_etapa_desde_texto(os.path.basename(raiz))
        if etapa_en_raiz in ETAPAS:
            etapas_con_carpeta.add(etapa_en_raiz)

        for fn in files:
            if fn.startswith("~$") or not fn.lower().endswith(".xlsx"):
                continue

            ruta = os.path.join(raiz, fn)
            etapa = extraer_etapa_desde_ruta_participante(ruta, carpeta_participantes)
            if etapa is None:
                avisos.append(
                    f"Archivo ignorado (no pude inferir etapa por carpeta): {ruta}"
                )
                continue
            if etapa not in ETAPAS:
                avisos.append(
                    f"Archivo ignorado (etapa fuera de configuración): {ruta}"
                )
                continue

            nombre = nombre_participante_desde_archivo(ruta)
            if not nombre:
                avisos.append(
                    f"Archivo ignorado (nombre de participante vacío): {ruta}"
                )
                continue

            registros.append({
                "ruta": ruta,
                "archivo": fn,
                "etapa": etapa,
                "nombre": nombre,
                "pid": id_participante(nombre),
            })
            conteo_por_etapa[etapa] = conteo_por_etapa.get(etapa, 0) + 1

    etapas_vacias = [
        e for e in sorted(etapas_con_carpeta, key=clave_orden_etapa)
        if conteo_por_etapa.get(e, 0) == 0
    ]

    registros.sort(key=lambda r: (clave_orden_etapa(r["etapa"]), r["nombre"], r["archivo"]))
    return registros, avisos, etapas_vacias


# ============================================================
# LECTURA CELDAS
# ============================================================
def leer_celdas_resultado(ws, n_partidos, celda_inicial=CELDA_INICIAL_RESULTADO, salto_filas=SALTO_FILAS):
    col = celda_inicial[0]
    fila = int(celda_inicial[1:]) + 4  # (mantengo EXACTO tu offset)
    out = []
    for _ in range(n_partidos):
        out.append(ws[f"{col}{fila}"].value)
        fila += salto_filas
    return out


def leer_celdas_eliminatoria(ws, n_partidos, celda_inicial=CELDA_INICIAL_RESULTADO, col_modo=COL_MODO, salto_filas=SALTO_FILAS):
    col_pasa = celda_inicial[0]
    fila = int(celda_inicial[1:])
    out = []
    for _ in range(n_partidos):
        pasa = ws[f"{col_pasa}{fila}"].value
        modo = ws[f"{col_modo}{fila}"].value
        out.append((pasa, modo))
        fila += salto_filas
    return out


def leer_campeon_predicho_desde_e01(ruta_excel):
    """
    En E01, el campeón pronosticado está en B4.
    """
    wb = load_workbook(ruta_excel, data_only=True)
    ws = wb.active
    return ws["B4"].value


# ============================================================
# PUNTAJE
# ============================================================
def normalizar_texto(x):
    if x is None:
        return ""
    return " ".join(str(x).strip().split()).upper()


def texto_ganador_sin_prefijo(x):
    txt = "" if x is None else str(x).strip()
    if not txt:
        return ""
    return re.sub(r"(?i)^\s*(?:pasa|gana|clasifica|avanza)\b[\s:.-]*", "", txt, count=1).strip()


def texto_pasa_eliminatoria(x):
    return texto_ganador_sin_prefijo(x)


def normalizar_pasa_eliminatoria(x):
    return normalizar_texto(texto_pasa_eliminatoria(x))


def puntaje_grupos(apuestas, pauta):
    pts = 0
    for a, r in zip(apuestas, pauta):
        if normalizar_texto(a) == normalizar_texto(r):
            pts += 1
    return pts


def puntaje_eliminatoria(apuestas, pauta, ppp):
    """
    Regla:
    - Si falla "pasa": 0
    - Si acierta "pasa": suma ppp
    - Si además acierta "modo": suma +1 (tal como lo tienes ahora)
    """
    pts = 0

    for (pasa, modo), (pasa_real, modo_real) in zip(apuestas, pauta):
        if normalizar_pasa_eliminatoria(pasa) != normalizar_pasa_eliminatoria(pasa_real):
            continue
        pts += ppp
        if normalizar_texto(modo) == normalizar_texto(modo_real):
            pts += 1

    return pts


def valor_visible(x):
    if x is None:
        return "-"
    txt = str(x).strip()
    return txt if txt else "-"


def valor_payload(x):
    if x is None:
        return ""
    return str(x).strip()


def pauta_partido_tiene_resultado(partido):
    if isinstance(partido, (list, tuple)):
        return any(normalizar_texto(valor) != "" for valor in partido)
    return normalizar_texto(partido) != ""


def etapa_comenzada(pautas_por_etapa, etapa):
    pauta = pautas_por_etapa.get(etapa)
    if not pauta:
        return False
    return any(pauta_partido_tiene_resultado(partido) for partido in pauta)


def pauta_partido_finalizado(etapa, partido):
    cfg = ETAPAS[etapa]
    if cfg["tipo"] == "GRUPOS":
        return normalizar_texto(partido) != ""

    if cfg["tipo"] == "ELIM":
        if isinstance(partido, (list, tuple)):
            pasa_real = partido[0] if len(partido) > 0 else None
            modo_real = partido[1] if len(partido) > 1 else None
        else:
            pasa_real = partido
            modo_real = None
        return normalizar_pasa_eliminatoria(pasa_real) != "" and normalizar_texto(modo_real) != ""

    return False


def etapa_finalizada(pautas_por_etapa, etapa):
    pauta = pautas_por_etapa.get(etapa)
    if not pauta:
        return False

    cfg = ETAPAS[etapa]
    if len(pauta) < cfg["n_partidos"]:
        return False

    return all(
        pauta_partido_finalizado(etapa, partido)
        for partido in pauta[:cfg["n_partidos"]]
    )


def normalizar_comparacion(x):
    txt = normalizar_texto(x)
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    txt = re.sub(r"[^A-Z0-9]+", " ", txt)
    return " ".join(txt.split())


def es_empate_pauta(x):
    return normalizar_comparacion(x) in {
        "EMPATE",
        "EMPATADO",
        "E",
        "DRAW",
        "TIE",
        "X",
        "IGUALDAD",
    }


def etiqueta_modo_eliminatoria(modo):
    txt = valor_payload(modo)
    if not txt:
        return ""

    norm = normalizar_comparacion(txt)
    if norm in {"90", "90 MIN", "90 MINUTOS", "TIEMPO REGULAR", "REGULAR", "EN LOS 90", "EN 90", "LOS 90"}:
        return "90'"
    if norm in {"ALARGUE", "ALARGUE EXTRA", "TIEMPO EXTRA", "EN TIEMPO EXTRA", "SUPLEMENTARIO", "PRORROGA"}:
        return "Alargue"
    if norm in {"PENALES", "EN PENALES", "PENAL", "PENALTIS", "PENALTIES", "PK", "PEN"}:
        return "Penales"
    return txt


def formatear_prediccion_elim(pasa, modo):
    vp = valor_visible(texto_pasa_eliminatoria(pasa))
    vm = valor_visible(modo)
    if vp == "-" and vm == "-":
        return "-"
    if vm == "-":
        return vp
    return f"{vp} | {vm}"


def formatear_enfrentamiento(equipo_a, equipo_b, numero_partido):
    a = valor_visible(equipo_a)
    b = valor_visible(equipo_b)
    if a != "-" and b != "-":
        return f"{a} vs {b}"
    if a != "-":
        return a
    if b != "-":
        return b
    return f"Partido {numero_partido}"


def leer_enfrentamientos_etapa_detalle(ws, cfg, celda_inicial=CELDA_INICIAL_RESULTADO, salto_filas=SALTO_FILAS):
    col_equipo_a = celda_inicial[0]
    col_equipo_b = "D"
    fila_base = int(celda_inicial[1:])
    if cfg["tipo"] == "GRUPOS":
        fila_prediccion = fila_base + 4  # mismo offset usado en leer_celdas_resultado
    elif cfg["tipo"] == "ELIM":
        fila_prediccion = fila_base
    else:
        raise ValueError(f"Tipo de etapa desconocido: {cfg['tipo']}")

    out = []
    for i in range(cfg["n_partidos"]):
        numero_partido = i + 1
        fila_enfrentamiento = (fila_prediccion - 1) + (i * salto_filas)
        equipo_a = ws[f"{col_equipo_a}{fila_enfrentamiento}"].value
        equipo_b = ws[f"{col_equipo_b}{fila_enfrentamiento}"].value
        out.append({
            "numero": numero_partido,
            "nombre": formatear_enfrentamiento(equipo_a, equipo_b, numero_partido),
            "equipo_a": valor_payload(equipo_a),
            "equipo_b": valor_payload(equipo_b),
        })
    return out


def leer_enfrentamientos_etapa(ws, cfg, celda_inicial=CELDA_INICIAL_RESULTADO, salto_filas=SALTO_FILAS):
    return [
        partido["nombre"]
        for partido in leer_enfrentamientos_etapa_detalle(ws, cfg, celda_inicial, salto_filas)
    ]


def interpretar_resultado_grupos(pauta, equipo_a, equipo_b):
    resultado = valor_payload(pauta)
    if not resultado:
        return {
            "resultado": "Pendiente",
            "ganador": "",
            "winner_side": "",
            "modo": "",
            "estado": "pendiente",
            "outcome": "pending",
        }

    ganador_sin_prefijo = texto_ganador_sin_prefijo(resultado)
    norm_resultado = normalizar_comparacion(ganador_sin_prefijo)
    norm_a = normalizar_comparacion(equipo_a)
    norm_b = normalizar_comparacion(equipo_b)

    if norm_a and norm_resultado == norm_a:
        return {
            "resultado": f"Gana {valor_payload(equipo_a)}",
            "ganador": valor_payload(equipo_a),
            "winner_side": "A",
            "modo": "",
            "estado": "jugado",
            "outcome": "winner",
        }
    if norm_b and norm_resultado == norm_b:
        return {
            "resultado": f"Gana {valor_payload(equipo_b)}",
            "ganador": valor_payload(equipo_b),
            "winner_side": "B",
            "modo": "",
            "estado": "jugado",
            "outcome": "winner",
        }
    if es_empate_pauta(resultado):
        return {
            "resultado": "Empate",
            "ganador": "",
            "winner_side": "",
            "modo": "",
            "estado": "jugado",
            "outcome": "draw",
        }

    return {
        "resultado": resultado,
        "ganador": "",
        "winner_side": "",
        "modo": "",
        "estado": "jugado",
        "outcome": "text",
    }


def interpretar_resultado_eliminatoria(pauta, equipo_a, equipo_b):
    if isinstance(pauta, (list, tuple)):
        pasa = pauta[0] if len(pauta) > 0 else None
        modo = pauta[1] if len(pauta) > 1 else None
    else:
        pasa = pauta
        modo = None

    ganador = texto_pasa_eliminatoria(pasa)
    modo_txt = etiqueta_modo_eliminatoria(modo)
    if not ganador:
        return {
            "resultado": "Pendiente",
            "ganador": "",
            "winner_side": "",
            "modo": modo_txt,
            "estado": "pendiente",
            "outcome": "pending",
        }

    norm_ganador = normalizar_comparacion(ganador)
    norm_a = normalizar_comparacion(equipo_a)
    norm_b = normalizar_comparacion(equipo_b)
    winner_side = ""
    if norm_a and norm_ganador == norm_a:
        winner_side = "A"
    elif norm_b and norm_ganador == norm_b:
        winner_side = "B"

    resultado = f"Pasa {ganador}"
    if modo_txt:
        resultado = f"{resultado} - {modo_txt}"

    return {
        "resultado": resultado,
        "ganador": ganador,
        "winner_side": winner_side,
        "modo": modo_txt,
        "estado": "jugado",
        "outcome": "winner",
    }


def construir_resultados_payload(etapas_ordenadas, pautas_por_etapa, enfrentamientos_detalle_por_etapa, calendario_por_etapa=None):
    stages = []
    matches = {}
    calendario_por_etapa = calendario_por_etapa or {}

    for etapa in etapas_ordenadas:
        cfg = ETAPAS[etapa]
        stages.append({
            "id": etapa,
            "label": etiqueta_etapa_larga(etapa),
            "type": cfg["tipo"],
        })

        pauta_etapa = pautas_por_etapa.get(etapa)
        enfrentamientos = enfrentamientos_detalle_por_etapa.get(etapa, [])
        calendario_etapa = calendario_por_etapa.get(etapa, {})
        partidos = []

        if pauta_etapa is None:
            matches[etapa] = partidos
            continue

        for i in range(cfg["n_partidos"]):
            numero_partido = i + 1
            enfrentamiento = (
                enfrentamientos[i]
                if i < len(enfrentamientos)
                else {
                    "numero": numero_partido,
                    "nombre": f"Partido {numero_partido}",
                    "equipo_a": "",
                    "equipo_b": "",
                }
            )
            equipo_a = enfrentamiento.get("equipo_a", "")
            equipo_b = enfrentamiento.get("equipo_b", "")
            pauta = pauta_etapa[i] if i < len(pauta_etapa) else None
            datos_calendario = calendario_etapa.get(numero_partido, {})
            if not equipo_a:
                equipo_a = datos_calendario.get("equipo_a", "")
            if not equipo_b:
                equipo_b = datos_calendario.get("equipo_b", "")
            nombre_enfrentamiento = enfrentamiento.get("nombre") or f"Partido {numero_partido}"
            if equipo_a or equipo_b:
                nombre_enfrentamiento = formatear_enfrentamiento(equipo_a, equipo_b, numero_partido)

            if cfg["tipo"] == "GRUPOS":
                info_resultado = interpretar_resultado_grupos(pauta, equipo_a, equipo_b)
                pauta_visible = valor_visible(pauta)
            elif cfg["tipo"] == "ELIM":
                info_resultado = interpretar_resultado_eliminatoria(pauta, equipo_a, equipo_b)
                if isinstance(pauta, (list, tuple)):
                    pasa = pauta[0] if len(pauta) > 0 else None
                    modo = pauta[1] if len(pauta) > 1 else None
                    pauta_visible = formatear_prediccion_elim(pasa, modo)
                else:
                    pauta_visible = valor_visible(pauta)
            else:
                info_resultado = {
                    "resultado": "Pendiente",
                    "ganador": "",
                    "winner_side": "",
                    "modo": "",
                    "estado": "pendiente",
                    "outcome": "pending",
                }
                pauta_visible = valor_visible(pauta)

            partidos.append({
                "numero": numero_partido,
                "nombre_enfrentamiento": nombre_enfrentamiento,
                "equipo_a": equipo_a,
                "equipo_b": equipo_b,
                "fecha_chile": datos_calendario.get("fecha_chile", ""),
                "hora_chile": datos_calendario.get("hora_chile", ""),
                "datetime_chile_iso": datos_calendario.get("datetime_chile_iso", ""),
                "fecha_hora_display": datos_calendario.get("fecha_hora_display", "Horario por confirmar"),
                "sort_key": datos_calendario.get("sort_key", ""),
                "sede": datos_calendario.get("sede", ""),
                "notas": datos_calendario.get("notas", ""),
                "pauta": pauta_visible,
                "resultado": info_resultado["resultado"],
                "ganador": info_resultado["ganador"],
                "winner_side": info_resultado["winner_side"],
                "modo": info_resultado["modo"],
                "estado": info_resultado["estado"],
                "outcome": info_resultado["outcome"],
            })

        matches[etapa] = partidos

    return {
        "stages": stages,
        "matches": matches,
    }


def calcular_detalle_etapa(ruta_excel, etapa, pautas_por_etapa):
    cfg = ETAPAS[etapa]
    pauta = pautas_por_etapa.get(etapa)
    if pauta is None:
        raise ValueError(
            f"No existe pauta cargada para la etapa {etapa}. "
            "Revisa la carpeta pauta."
        )

    wb = load_workbook(ruta_excel, data_only=True)
    ws = wb.active

    if cfg["tipo"] == "GRUPOS":
        apuestas = leer_celdas_resultado(ws, cfg["n_partidos"])
        if len(pauta) != cfg["n_partidos"]:
            raise ValueError(
                f"La pauta de {etapa} debe tener {cfg['n_partidos']} resultados "
                f"(tiene {len(pauta)})."
            )
        partidos = []
        total_etapa = 0
        for i, (a, r) in enumerate(zip(apuestas, pauta), start=1):
            pauta_llena = normalizar_texto(r) != ""
            puntos_exactitud = 1 if (pauta_llena and normalizar_texto(a) == normalizar_texto(r)) else 0
            puntos_signo = 0
            bonus = 0
            total_partido = puntos_exactitud
            total_etapa += total_partido
            desglose = "Acierta resultado (+1)." if total_partido else "No acierta resultado (0)."
            partidos.append({
                "partido": i,
                "pronostico": valor_visible(a),
                "pauta": valor_visible(r),
                "puntos_exactitud": puntos_exactitud,
                "puntos_signo": puntos_signo,
                "bonus": bonus,
                "total": total_partido,
                "desglose": desglose,
            })
        return {
            "etapa": etapa,
            "tipo": cfg["tipo"],
            "total_etapa": total_etapa,
            "partidos": partidos,
        }

    if cfg["tipo"] == "ELIM":
        apuestas = leer_celdas_eliminatoria(ws, cfg["n_partidos"])
        if len(pauta) != cfg["n_partidos"]:
            raise ValueError(
                f"La pauta de {etapa} debe tener {cfg['n_partidos']} tuplas "
                f"(tiene {len(pauta)})."
            )
        partidos = []
        total_etapa = 0
        for i, ((pasa, modo), (pasa_real, modo_real)) in enumerate(zip(apuestas, pauta), start=1):

            pauta_pasa_llena = normalizar_pasa_eliminatoria(pasa_real) != ""
            pauta_modo_llena = normalizar_texto(modo_real) != ""     
            acierta_pasa = pauta_pasa_llena and (normalizar_pasa_eliminatoria(pasa) == normalizar_pasa_eliminatoria(pasa_real))
            puntos_exactitud = cfg["ppp"] if acierta_pasa else 0
            puntos_signo = 0
            bonus = 1 if (acierta_pasa and pauta_modo_llena and normalizar_texto(modo) == normalizar_texto(modo_real)) else 0
            
            total_partido = puntos_exactitud + bonus
            total_etapa += total_partido
            if not acierta_pasa:
                desglose = "No acierta quién pasa (0)."
            elif bonus:
                desglose = f"Acierta quién pasa (+{cfg['ppp']}) y modo (+1)."
            else:
                desglose = f"Acierta quién pasa (+{cfg['ppp']}), pero falla modo (+0)."

            partidos.append({
                "partido": i,
                "pronostico": formatear_prediccion_elim(pasa, modo),
                "pauta": formatear_prediccion_elim(pasa_real, modo_real),
                "puntos_exactitud": puntos_exactitud,
                "puntos_signo": puntos_signo,
                "bonus": bonus,
                "total": total_partido,
                "desglose": desglose,
            })
        return {
            "etapa": etapa,
            "tipo": cfg["tipo"],
            "total_etapa": total_etapa,
            "partidos": partidos,
        }

    raise ValueError(f"Tipo de etapa desconocido: {cfg['tipo']}")


def calcular_puntaje_etapa(ruta_excel, etapa, pautas_por_etapa):
    return calcular_detalle_etapa(ruta_excel, etapa, pautas_por_etapa)["total_etapa"]

def html_escape(x):
    if x is None:
        return ""
    return (str(x)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

def calcular_posiciones_con_empate(participantes):
    posiciones = []
    pos_anterior = None
    total_anterior = None

    for idx, participante in enumerate(participantes, start=1):
        total = participante[4]
        if total != total_anterior:
            pos_actual = idx
        else:
            pos_actual = pos_anterior

        posiciones.append(pos_actual)
        total_anterior = total
        pos_anterior = pos_actual

    return posiciones


def calcular_puntos_repartidos(pautas_por_etapa, campeon_real_oficial, max_por_etapa, max_bonus):
    puntos_repartidos = 0

    for etapa, cfg in ETAPAS.items():
        pauta = pautas_por_etapa.get(etapa)
        if not pauta:
            continue

        puntos_etapa = 0
        if cfg["tipo"] == "GRUPOS":
            for resultado_real in pauta[:cfg["n_partidos"]]:
                if normalizar_texto(resultado_real) != "":
                    puntos_etapa += cfg["ppp"]
        elif cfg["tipo"] == "ELIM":
            for item in pauta[:cfg["n_partidos"]]:
                if isinstance(item, (list, tuple)):
                    pasa_real = item[0] if len(item) > 0 else None
                    modo_real = item[1] if len(item) > 1 else None
                else:
                    pasa_real = item
                    modo_real = None

                if normalizar_pasa_eliminatoria(pasa_real) == "":
                    continue

                puntos_etapa += cfg["ppp"]
                if normalizar_texto(modo_real) != "":
                    puntos_etapa += 1

        puntos_repartidos += min(puntos_etapa, max_por_etapa.get(etapa, puntos_etapa))

    if normalizar_texto(campeon_real_oficial) != "":
        puntos_repartidos += max_bonus

    return puntos_repartidos


def formatear_porcentaje_avance(porcentaje):
    porcentaje_redondeado = round(float(porcentaje), 1)
    if porcentaje_redondeado.is_integer():
        return f"{int(porcentaje_redondeado)}%"
    return f"{porcentaje_redondeado:.1f}%".replace(".", ",")


def calcular_podios_por_etapa(participantes, etapas_ordenadas, etapas_finalizadas):
    medallas = {
        1: {"medal": "🥇", "class": "stage-gold"},
        2: {"medal": "🥈", "class": "stage-silver"},
        3: {"medal": "🥉", "class": "stage-bronze"},
    }
    podios_por_etapa = {}

    for etapa in etapas_ordenadas:
        if not etapas_finalizadas.get(etapa):
            continue

        puntajes = []
        for pid, nombre, scores, bono, total, errores in participantes:
            puntaje = scores.get(etapa, 0)
            if puntaje > 0:
                puntajes.append((pid, puntaje))

        if not puntajes:
            continue

        puntajes_distintos = sorted({puntaje for pid, puntaje in puntajes}, reverse=True)
        rank_por_puntaje = {
            puntaje: rank
            for rank, puntaje in enumerate(puntajes_distintos[:3], start=1)
        }

        for pid, puntaje in puntajes:
            rank_actual = rank_por_puntaje.get(puntaje)
            if rank_actual not in medallas:
                continue

            info_medalla = medallas[rank_actual]
            podios_por_etapa.setdefault(pid, {})[etapa] = {
                "rank": rank_actual,
                "medal": info_medalla["medal"],
                "class": info_medalla["class"],
                "title": f"{rank_actual}° lugar en {ETIQUETAS_ETAPAS.get(etapa, etapa)}",
            }

    return podios_por_etapa


def render_tabla_html(nombre_competencia, participantes, etapas_ordenadas,
                      max_por_etapa, max_bonus, max_total, out_path,
                      detalle_payload, resultados_payload=None,
                      puntos_repartidos=0, porcentaje_avance=0,
                      podios_por_etapa=None):

    now = datetime.now(ZoneInfo("America/Santiago")).strftime("%Y-%m-%d %H:%M:%S")
    titulo_competencia = html_escape(nombre_competencia)
    detalle_json = json.dumps(detalle_payload, ensure_ascii=False).replace("</", "<\\/")
    resultados_payload = resultados_payload or {"stages": [], "matches": {}}
    resultados_json = json.dumps(resultados_payload, ensure_ascii=False).replace("</", "<\\/")
    porcentaje_display = formatear_porcentaje_avance(porcentaje_avance)
    progreso_width = max(0, min(100, float(porcentaje_avance or 0)))
    podios_por_etapa = podios_por_etapa or {}

    headers = ["Pos", "Nombre", "Total"] \
              + [ETIQUETAS_ETAPAS[e] for e in etapas_ordenadas] \
              + [NOMBRE_COLUMNA_BONUS]

    max_row = ["", "", f"Max={max_total}"] \
              + [f"Max={max_por_etapa[e]}" for e in etapas_ordenadas] \
              + [f"Max={max_bonus}"]

    body_rows = []
    for pid, pos, nombre, scores, bono, total in participantes:
        body_rows.append({
            "pid": pid,
            "pos": pos,
            "nombre": nombre,
            "scores": scores,
            "bono": bono,
            "total": total,
        })

    colgroup_html = (
        "<colgroup>"
        "<col class='col-pos'>"
        "<col class='col-nombre'>"
        "<col class='col-total'>"
        + "".join("<col class='col-puntaje'>" for _ in headers[3:])
        + "</colgroup>"
    )

    def render_header_cell(text, idx):
        clase = " class='total'" if idx == 2 else ""
        return f"<th{clase}>{text}</th>"

    def clase_podio_tabla(pos):
        return {
            1: "podio-oro",
            2: "podio-plata",
            3: "podio-bronce",
        }.get(pos, "")

    def render_stage_score(pid, etapa, puntaje):
        podio = podios_por_etapa.get(pid, {}).get(etapa)
        if not podio:
            return html_escape(puntaje)

        clase = podio["class"]
        title = html_escape(podio["title"])
        medal = podio["medal"]
        return (
            f"<span class='stage-score {clase}' title='{title}'>"
            f"<span class='stage-score-value'>{html_escape(puntaje)}</span>"
            f"<span class='stage-medal' aria-hidden='true'>{medal}</span>"
            "</span>"
        )

    def render_body_row(row):
        clase = clase_podio_tabla(row["pos"])
        row_open = f"<tr class='{clase}'>" if clase else "<tr>"
        cells = [
            f"<td>{html_escape(row['pos'])}</td>",
            f"<td class='nombre'>{html_escape(row['nombre'])}</td>",
            f"<td class='total'>{html_escape(row['total'])}</td>",
        ]
        for etapa in etapas_ordenadas:
            cells.append(
                f"<td>{render_stage_score(row['pid'], etapa, row['scores'].get(etapa, 0))}</td>"
            )
        cells.append(f"<td>{html_escape(row['bono'])}</td>")
        return row_open + "".join(cells) + "</tr>"

    detalle_script = """
<script id="resultados-data" type="application/json">__RESULTADOS_JSON__</script>
<script id="detalle-data" type="application/json">__DETALLE_JSON__</script>
<script>
(function () {
    var dataNode = document.getElementById("resultados-data");
    var stageSelect = document.getElementById("resultados-etapa");
    var stageLabel = document.getElementById("resultados-stage-label");
    var stageCount = document.getElementById("resultados-stage-count");
    var tableWrap = document.getElementById("resultados-table-wrap");
    var tableBody = document.getElementById("resultados-body");
    var emptyBox = document.getElementById("resultados-empty");
    var noteBox = document.getElementById("resultados-note");

    if (!dataNode || !stageSelect || !tableWrap || !tableBody || !emptyBox) return;

    var payload = {};
    try {
        payload = JSON.parse(dataNode.textContent || "{}");
    } catch (e) {
        console.error("No pude parsear resultados-data", e);
        return;
    }

    var stages = payload.stages || [];
    var matchesByStage = payload.matches || {};
    var FLAG_BY_NAME = {
        "ALEMANIA": "🇩🇪",
        "ARGENTINA": "🇦🇷",
        "ARABIA SAUDITA": "🇸🇦",
        "ARGELIA": "🇩🇿",
        "AUSTRIA": "🇦🇹",
        "AUSTRALIA": "🇦🇺",
        "BELGICA": "🇧🇪",
        "BOLIVIA": "🇧🇴",
        "BOSNIA": "🇧🇦",
        "BOSNIA AND HERZEGOVINA": "🇧🇦",
        "BOSNIA HERZAGOBINA": "🇧🇦",
        "BOSNIA HERZEGOVINA": "🇧🇦",
        "BOSNIA Y HERZAGOBINA": "🇧🇦",
        "BOSNIA Y HERZEGOVINA": "🇧🇦",
        "BRASIL": "🇧🇷",
        "CABO VERDE": "🇨🇻",
        "CAMERUN": "🇨🇲",
        "CANADA": "🇨🇦",
        "CHILE": "🇨🇱",
        "CHINA": "🇨🇳",
        "COLOMBIA": "🇨🇴",
        "CONGO": "🇨🇬",
        "COREA": "🇰🇷",
        "COREA DEL SUR": "🇰🇷",
        "COSTA DE MARFIL": "🇨🇮",
        "COSTA RICA": "🇨🇷",
        "CROACIA": "🇭🇷",
        "DINAMARCA": "🇩🇰",
        "ECUADOR": "🇪🇨",
        "EGIPTO": "🇪🇬",
        "EE UU": "🇺🇸",
        "EEUU": "🇺🇸",
        "ESCOCIA": "🏴",
        "ESPANA": "🇪🇸",
        "ESTADOS UNIDOS": "🇺🇸",
        "ESTADOS UNIDOS DE AMERICA": "🇺🇸",
        "FRANCIA": "🇫🇷",
        "GALES": "🏴",
        "GHANA": "🇬🇭",
        "HOLANDA": "🇳🇱",
        "INGLATERRA": "🏴",
        "IRAN": "🇮🇷",
        "ITALIA": "🇮🇹",
        "JAPON": "🇯🇵",
        "MARRUECOS": "🇲🇦",
        "MEXICO": "🇲🇽",
        "NIGERIA": "🇳🇬",
        "NORUEGA": "🇳🇴",
        "PAISES BAJOS": "🇳🇱",
        "PANAMA": "🇵🇦",
        "PARAGUAY": "🇵🇾",
        "PERU": "🇵🇪",
        "POLONIA": "🇵🇱",
        "PORTUGAL": "🇵🇹",
        "QATAR": "🇶🇦",
        "CONGO DEMOCRATICO": "🇨🇩",
        "CONGO KINSHASA": "🇨🇩",
        "DR CONGO": "🇨🇩",
        "R D CONGO": "🇨🇩",
        "RD CONGO": "🇨🇩",
        "REP DEMOCRATICA DEL CONGO": "🇨🇩",
        "REPUBLICA DEMOCRATICA DEL CONGO": "🇨🇩",
        "SENEGAL": "🇸🇳",
        "SERBIA": "🇷🇸",
        "SUDAFRICA": "🇿🇦",
        "SUECIA": "🇸🇪",
        "SUIZA": "🇨🇭",
        "TUNEZ": "🇹🇳",
        "TURQUIA": "🇹🇷",
        "URUGUAY": "🇺🇾",
        "USA": "🇺🇸",
        "VENEZUELA": "🇻🇪"
    };
    var COUNTRY_CODE_BY_NAME = {
        "ALEMANIA": "de",
        "ARGENTINA": "ar",
        "ARABIA SAUDITA": "sa",
        "ARGELIA": "dz",
        "AUSTRIA": "at",
        "AUSTRALIA": "au",
        "BELGICA": "be",
        "BOLIVIA": "bo",
        "BOSNIA": "ba",
        "BOSNIA AND HERZEGOVINA": "ba",
        "BOSNIA HERZAGOBINA": "ba",
        "BOSNIA HERZEGOVINA": "ba",
        "BOSNIA Y HERZAGOBINA": "ba",
        "BOSNIA Y HERZEGOVINA": "ba",
        "BRASIL": "br",
        "CABO VERDE": "cv",
        "CAMERUN": "cm",
        "CANADA": "ca",
        "CHILE": "cl",
        "CHINA": "cn",
        "COLOMBIA": "co",
        "CONGO": "cg",
        "COREA": "kr",
        "COREA DEL SUR": "kr",
        "COSTA DE MARFIL": "ci",
        "COSTA RICA": "cr",
        "CROACIA": "hr",
        "DINAMARCA": "dk",
        "ECUADOR": "ec",
        "EGIPTO": "eg",
        "EE UU": "us",
        "EEUU": "us",
        "ESCOCIA": "gb-sct",
        "ESPANA": "es",
        "ESTADOS UNIDOS": "us",
        "ESTADOS UNIDOS DE AMERICA": "us",
        "FRANCIA": "fr",
        "GALES": "gb-wls",
        "GHANA": "gh",
        "HOLANDA": "nl",
        "INGLATERRA": "gb-eng",
        "IRAN": "ir",
        "ITALIA": "it",
        "JAPON": "jp",
        "MARRUECOS": "ma",
        "MEXICO": "mx",
        "NIGERIA": "ng",
        "NORUEGA": "no",
        "PAISES BAJOS": "nl",
        "PANAMA": "pa",
        "PARAGUAY": "py",
        "PERU": "pe",
        "POLONIA": "pl",
        "PORTUGAL": "pt",
        "QATAR": "qa",
        "CONGO DEMOCRATICO": "cd",
        "CONGO KINSHASA": "cd",
        "DR CONGO": "cd",
        "R D CONGO": "cd",
        "RD CONGO": "cd",
        "REP DEMOCRATICA DEL CONGO": "cd",
        "REPUBLICA DEMOCRATICA DEL CONGO": "cd",
        "SENEGAL": "sn",
        "SERBIA": "rs",
        "SUDAFRICA": "za",
        "SUECIA": "se",
        "SUIZA": "ch",
        "TUNEZ": "tn",
        "TURQUIA": "tr",
        "URUGUAY": "uy",
        "USA": "us",
        "VENEZUELA": "ve"
    };

    function normalizarPais(valor) {
        var texto = String(valor || "").trim().toUpperCase();
        if (texto.normalize) {
            texto = texto.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");
        }
        return texto.replace(/[^A-Z0-9]+/g, " ").replace(/\\s+/g, " ").trim();
    }

    function flagPais(nombre) {
        return FLAG_BY_NAME[normalizarPais(nombre)] || "";
    }

    function codigoPais(nombre) {
        return COUNTRY_CODE_BY_NAME[normalizarPais(nombre)] || "";
    }

    function crearBandera(nombre) {
        var code = codigoPais(nombre);
        var emoji = flagPais(nombre);
        if (code) {
            var img = document.createElement("img");
            img.className = "resultados-flag-img";
            img.src = "https://flagcdn.com/24x18/" + code + ".png";
            img.srcset = "https://flagcdn.com/48x36/" + code + ".png 2x";
            img.alt = emoji || code.toUpperCase();
            img.loading = "lazy";
            img.decoding = "async";
            img.onerror = function () {
                var fallback = document.createElement("span");
                fallback.className = "resultados-flag";
                fallback.textContent = emoji || code.toUpperCase();
                img.replaceWith(fallback);
            };
            return img;
        }
        if (emoji) {
            var flagNode = document.createElement("span");
            flagNode.className = "resultados-flag";
            flagNode.textContent = emoji;
            return flagNode;
        }
        return null;
    }

    function crearPais(nombre, ganador, fallback) {
        var limpio = String(nombre || "").trim();
        var texto = limpio || fallback || "Por definir";
        var span = document.createElement("span");
        span.className = "resultados-team" + (ganador ? " resultados-team-win" : "") + (!limpio ? " resultados-team-pending" : "");

        var flagNode = crearBandera(limpio);
        if (flagNode) {
            span.appendChild(flagNode);
        }

        var nameNode = document.createElement("span");
        nameNode.textContent = texto;
        span.appendChild(nameNode);
        return span;
    }

    function appendCell(tr, className) {
        var td = document.createElement("td");
        if (className) td.className = className;
        tr.appendChild(td);
        return td;
    }

    function buscarEtapaResultado(etapaId) {
        return stages.find(function (stage) { return stage.id === etapaId; }) || null;
    }

    function renderResultadoCell(td, match, stage) {
        var estado = match.estado || "pendiente";
        var outcome = match.outcome || "pending";
        var badge = document.createElement("span");
        badge.className = "resultados-badge resultados-badge-" + (estado === "pendiente" ? "pending" : outcome);
        badge.textContent = estado === "pendiente" ? "Pendiente" : (outcome === "draw" ? "Empate" : "Jugado");
        td.appendChild(badge);

        var line = document.createElement("div");
        line.className = "resultados-result-line";
        if (estado === "pendiente") {
            line.textContent = "Pendiente";
        } else if (outcome === "draw") {
            line.textContent = "Empate";
        } else if (outcome === "winner" && match.ganador) {
            var prefix = document.createElement("span");
            prefix.textContent = stage && stage.type === "ELIM" ? "Pasa " : "Gana ";
            line.appendChild(prefix);
            line.appendChild(crearPais(match.ganador, true, match.ganador));
            if (match.modo) {
                var modo = document.createElement("span");
                modo.className = "resultados-mode";
                modo.textContent = " " + match.modo;
                line.appendChild(modo);
            }
        } else {
            line.textContent = match.resultado || "Resultado";
        }
        td.appendChild(line);
    }

    function renderResultados() {
        var etapaId = stageSelect.value;
        var stage = buscarEtapaResultado(etapaId);
        var partidos = matchesByStage[etapaId] || [];
        tableBody.innerHTML = "";

        if (stageLabel) stageLabel.textContent = stage ? stage.label : "Etapa";
        if (stageCount) {
            stageCount.textContent = partidos.length === 1 ? "1 partido" : String(partidos.length) + " partidos";
        }

        if (!partidos.length) {
            tableWrap.hidden = true;
            if (noteBox) noteBox.hidden = true;
            emptyBox.hidden = false;
            emptyBox.textContent = "Todavía no hay resultados cargados para esta etapa.";
            return;
        }

        var hayJugados = partidos.some(function (match) { return match.estado === "jugado"; });
        emptyBox.hidden = true;
        if (noteBox) {
            noteBox.hidden = hayJugados;
            noteBox.textContent = "Todavía no hay resultados cargados para esta etapa.";
        }

        var partidosOrdenados = partidos.slice().sort(function (a, b) {
            var aTime = Date.parse(String(a.sort_key || "").trim());
            var bTime = Date.parse(String(b.sort_key || "").trim());
            var aTieneHorario = !isNaN(aTime);
            var bTieneHorario = !isNaN(bTime);
            var aNumero = Number(a.numero || 0);
            var bNumero = Number(b.numero || 0);

            if (aTieneHorario && bTieneHorario) {
                if (aTime !== bTime) return aTime - bTime;
                return aNumero - bNumero;
            }
            if (aTieneHorario) return -1;
            if (bTieneHorario) return 1;
            return aNumero - bNumero;
        });

        partidosOrdenados.forEach(function (match) {
            var tr = document.createElement("tr");
            tr.className = "resultados-row resultados-" + (match.estado || "pendiente");

            var partidoCell = appendCell(tr, "resultados-match-cell");
            var numero = document.createElement("strong");
            numero.textContent = "Partido " + String(match.numero || "");
            partidoCell.appendChild(numero);
            var horario = document.createElement("span");
            horario.className = "resultados-schedule-line";
            horario.textContent = match.fecha_hora_display || "Horario por confirmar";
            partidoCell.appendChild(horario);
            var sede = String(match.sede || "").trim();
            if (sede) {
                var sedeNode = document.createElement("span");
                sedeNode.className = "resultados-venue-line";
                sedeNode.textContent = sede;
                partidoCell.appendChild(sedeNode);
            }

            appendCell(tr, "").appendChild(crearPais(match.equipo_a, match.winner_side === "A", "Por definir"));
            appendCell(tr, "").appendChild(crearPais(match.equipo_b, match.winner_side === "B", "Por definir"));
            renderResultadoCell(appendCell(tr, "resultados-result-cell"), match, stage);

            tableBody.appendChild(tr);
        });

        tableWrap.hidden = false;
    }

    function llenarSelectorResultados() {
        stageSelect.innerHTML = "";
        if (!stages.length) {
            var emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = "Sin etapas disponibles";
            stageSelect.appendChild(emptyOption);
            stageSelect.disabled = true;
            renderResultados();
            return;
        }

        stages.forEach(function (stage) {
            var option = document.createElement("option");
            option.value = stage.id;
            option.textContent = stage.label;
            stageSelect.appendChild(option);
        });
        stageSelect.disabled = false;
        var etapaConHorario = stages.slice().reverse().find(function (stage) {
            return (matchesByStage[stage.id] || []).some(function (match) {
                var sortKey = String(match.sort_key || "").trim();
                var fecha = String(match.fecha_chile || "").trim();
                var hora = String(match.hora_chile || "").trim();
                return !!sortKey || (!!fecha && !!hora);
            });
        });
        stageSelect.value = (etapaConHorario || stages[0]).id;
        renderResultados();
    }

    stageSelect.addEventListener("change", renderResultados);
    llenarSelectorResultados();
})();

(function () {
    var dataNode = document.getElementById("detalle-data");
    if (!dataNode) return;

    var payload = {};
    try {
        payload = JSON.parse(dataNode.textContent || "{}");
    } catch (e) {
        console.error("No pude parsear detalle-data", e);
        return;
    }

    var participantes = payload.participants || [];
    var etapas = payload.stages || [];
    var detalles = payload.details || {};
    var etiquetasPartidos = payload.match_labels || {};
    var MENSAJE_RONDA_NO_COMIENZA = "Ronda aún no comienza.";

    var participanteSel = document.getElementById("detalle-participante");
    var etapaSel = document.getElementById("detalle-etapa");
    var content = document.getElementById("detalle-content");
    var resumenParticipante = document.getElementById("detalle-resumen-participante");
    var resumenEtapa = document.getElementById("detalle-resumen-etapa");
    var resumenTotal = document.getElementById("detalle-resumen-total");
    var detalleHead = document.getElementById("detalle-head-row");
    var detalleBody = document.getElementById("detalle-body");

    var detalle2EtapaSel = document.getElementById("detalle2-etapa");
    var detalle2PartidoSel = document.getElementById("detalle2-partido");
    var detalle2Content = document.getElementById("detalle2-content");
    var detalle2ResumenEtapa = document.getElementById("detalle2-resumen-etapa");
    var detalle2ResumenPartido = document.getElementById("detalle2-resumen-partido");
    var detalle2ResumenResultado = document.getElementById("detalle2-resumen-resultado");
    var detalle2Head = document.getElementById("detalle2-head-row");
    var detalle2Body = document.getElementById("detalle2-body");

    function appendCell(tr, value, className) {
        var td = document.createElement("td");
        if (className) td.className = className;
        td.textContent = value;
        tr.appendChild(td);
    }

    function clasePuntos(value) {
        return "num " + (Number(value || 0) > 0 ? "pts-pos" : "pts-zero");
    }

    function resetSelect(selectNode, placeholder) {
        if (!selectNode) return;
        selectNode.innerHTML = "";
        var option = document.createElement("option");
        option.value = "";
        option.textContent = placeholder;
        selectNode.appendChild(option);
    }

    function renderHeaderDetalle(mostrarBonus) {
        detalleHead.innerHTML = "";
        var headers = [
            { text: "Partido", cls: "" },
            { text: "Pronóstico participante", cls: "" },
            { text: "Resultado Real", cls: "" },
            { text: "Puntos por acertar resultado", cls: "num" }
        ];

        if (mostrarBonus) {
            headers.push({ text: "Bonus por acertar modo", cls: "num" });
        }
        headers.push({ text: "Total", cls: "num" });

        headers.forEach(function (h) {
            var th = document.createElement("th");
            if (h.cls) th.className = h.cls;
            th.textContent = h.text;
            detalleHead.appendChild(th);
        });
    }

    function renderHeaderPartido(mostrarBonus) {
        detalle2Head.innerHTML = "";
        var headers = [
            { text: "Participante", cls: "" },
            { text: "Pronóstico participante", cls: "" },
            { text: "Resultado Real", cls: "" },
            { text: "Puntos por acertar resultado", cls: "num" }
        ];

        if (mostrarBonus) {
            headers.push({ text: "Bonus por acertar modo", cls: "num" });
        }
        headers.push({ text: "Total partido", cls: "num" });

        headers.forEach(function (h) {
            var th = document.createElement("th");
            if (h.cls) th.className = h.cls;
            th.textContent = h.text;
            detalle2Head.appendChild(th);
        });
    }

    function renderSinDataDetalle(mostrarBonus, mensaje) {
        detalleBody.innerHTML = "";
        var tr = document.createElement("tr");
        var td = document.createElement("td");
        td.colSpan = mostrarBonus ? 6 : 5;
        td.textContent = mensaje;
        tr.appendChild(td);
        detalleBody.appendChild(tr);
    }

    function renderSinDataPartido(mostrarBonus, mensaje) {
        detalle2Body.innerHTML = "";
        var tr = document.createElement("tr");
        var td = document.createElement("td");
        td.colSpan = mostrarBonus ? 6 : 5;
        td.textContent = mensaje;
        tr.appendChild(td);
        detalle2Body.appendChild(tr);
    }

    function buscarEtapa(etapaId) {
        return etapas.find(function (e) { return e.id === etapaId; }) || null;
    }

    function etapaEstaComenzada(etapa) {
        return !!(etapa && etapa.started);
    }

    function etiquetaPartido(etapaId, numeroPartido) {
        var n = Number(numeroPartido);
        if (isNaN(n) || n <= 0) {
            return "";
        }
        var lista = etiquetasPartidos[etapaId];
        if (Array.isArray(lista) && (n - 1) < lista.length) {
            var etiqueta = String(lista[n - 1] || "").trim();
            if (etiqueta) {
                return etiqueta;
            }
        }
        return "Partido " + String(n);
    }

    function partidosDisponiblesDeEtapa(etapaId) {
        var partidos = {};
        participantes.forEach(function (p) {
            var detalleEtapa = (detalles[p.id] || {})[etapaId];
            if (!detalleEtapa || !Array.isArray(detalleEtapa.partidos)) return;
            detalleEtapa.partidos.forEach(function (partido) {
                var numero = Number(partido.partido);
                if (!isNaN(numero) && numero > 0) {
                    partidos[numero] = true;
                }
            });
        });

        return Object.keys(partidos).map(function (x) { return Number(x); }).sort(function (a, b) { return a - b; });
    }

    function actualizarSelectorPartido() {
        var etapaId = detalle2EtapaSel.value;
        var etapa = buscarEtapa(etapaId);
        resetSelect(detalle2PartidoSel, "Selecciona un partido");

        if (!etapaId) {
            detalle2PartidoSel.disabled = true;
            return;
        }

        if (!etapaEstaComenzada(etapa)) {
            var pendiente = document.createElement("option");
            pendiente.value = "";
            pendiente.textContent = MENSAJE_RONDA_NO_COMIENZA;
            detalle2PartidoSel.appendChild(pendiente);
            detalle2PartidoSel.disabled = true;
            return;
        }

        var partidos = partidosDisponiblesDeEtapa(etapaId);
        if (!partidos.length) {
            var vacio = document.createElement("option");
            vacio.value = "";
            vacio.textContent = "Sin partidos disponibles";
            detalle2PartidoSel.appendChild(vacio);
            detalle2PartidoSel.disabled = true;
            return;
        }

        partidos.forEach(function (numero) {
            var option = document.createElement("option");
            option.value = String(numero);
            option.textContent = etiquetaPartido(etapaId, numero);
            detalle2PartidoSel.appendChild(option);
        });
        detalle2PartidoSel.disabled = false;
    }

    function llenarSelectores() {
        participantes.forEach(function (p) {
            var optionParticipante = document.createElement("option");
            optionParticipante.value = p.id;
            optionParticipante.textContent = p.name;
            participanteSel.appendChild(optionParticipante);
        });

        etapas.forEach(function (e) {
            var optionEtapaDetalle = document.createElement("option");
            optionEtapaDetalle.value = e.id;
            optionEtapaDetalle.textContent = e.label;
            etapaSel.appendChild(optionEtapaDetalle);

            var optionEtapaPartido = document.createElement("option");
            optionEtapaPartido.value = e.id;
            optionEtapaPartido.textContent = e.label;
            detalle2EtapaSel.appendChild(optionEtapaPartido);
        });
    }

    function renderVacioDetalle() {
        content.hidden = true;
    }

    function renderVacioPartido() {
        detalle2Content.hidden = true;
    }

    function renderDetalleParticipante() {
        var participanteId = participanteSel.value;
        var etapaId = etapaSel.value;
        detalleBody.innerHTML = "";

        if (!participanteId || !etapaId) {
            renderVacioDetalle();
            return;
        }

        var participante = participantes.find(function (p) { return p.id === participanteId; });
        var etapa = buscarEtapa(etapaId);
        var detalle = (detalles[participanteId] || {})[etapaId] || null;
        var mostrarBonus = !!(etapa && etapa.show_bonus);
        renderHeaderDetalle(mostrarBonus);

        resumenParticipante.textContent = participante ? participante.name : "-";
        resumenEtapa.textContent = etapa ? etapa.label : etapaId;

        if (!etapaEstaComenzada(etapa)) {
            resumenTotal.textContent = "-";
            renderSinDataDetalle(mostrarBonus, MENSAJE_RONDA_NO_COMIENZA);
            content.hidden = false;
            return;
        }

        if (!detalle) {
            resumenTotal.textContent = "0 puntos";
            renderSinDataDetalle(mostrarBonus, "Sin pronóstico disponible para este participante en esta etapa.");
            content.hidden = false;
            return;
        }

        resumenTotal.textContent = String(detalle.total) + " puntos";
        (detalle.partidos || []).forEach(function (partido) {
            var tr = document.createElement("tr");
            appendCell(tr, etiquetaPartido(etapaId, partido.partido), "partido-cell");
            appendCell(tr, partido.pronostico || "-", "");
            appendCell(tr, partido.pauta || "-", "");
            appendCell(tr, String(partido.puntos_exactitud || 0), clasePuntos(partido.puntos_exactitud || 0));
            if (mostrarBonus) {
                appendCell(tr, String(partido.bonus || 0), clasePuntos(partido.bonus || 0));
            }
            appendCell(tr, String(partido.total || 0), clasePuntos(partido.total || 0));
            detalleBody.appendChild(tr);
        });

        content.hidden = false;
    }

    function renderDetallePartido() {
        var etapaId = detalle2EtapaSel.value;
        var etapa = buscarEtapa(etapaId);
        var mostrarBonus = !!(etapa && etapa.show_bonus);
        detalle2Body.innerHTML = "";

        if (!etapaId) {
            renderVacioPartido();
            return;
        }

        renderHeaderPartido(mostrarBonus);
        detalle2ResumenEtapa.textContent = etapa ? etapa.label : etapaId;

        if (!etapaEstaComenzada(etapa)) {
            detalle2ResumenPartido.textContent = "-";
            detalle2ResumenResultado.textContent = "-";
            renderSinDataPartido(mostrarBonus, MENSAJE_RONDA_NO_COMIENZA);
            detalle2Content.hidden = false;
            return;
        }

        if (!detalle2PartidoSel.value) {
            renderVacioPartido();
            return;
        }

        var partidoNumero = Number(detalle2PartidoSel.value);

        var filas = participantes.map(function (p) {
            var detalleEtapa = (detalles[p.id] || {})[etapaId] || null;
            var partido = null;

            if (detalleEtapa && Array.isArray(detalleEtapa.partidos)) {
                partido = detalleEtapa.partidos.find(function (x) {
                    return Number(x.partido) === partidoNumero;
                }) || null;
            }

            return {
                participante: p.name,
                pronostico: partido ? (partido.pronostico || "-") : "Sin pronóstico",
                pauta: partido ? (partido.pauta || "-") : "-",
                puntosExactitud: partido ? Number(partido.puntos_exactitud || 0) : 0,
                bonus: partido ? Number(partido.bonus || 0) : 0,
                total: partido ? Number(partido.total || 0) : 0,
            };
        });

        filas.sort(function (a, b) {
            if (b.total !== a.total) return b.total - a.total;
            return a.participante.localeCompare(b.participante, "es", { sensitivity: "base" });
        });

        var resultadoReal = filas.find(function (f) {
            return f.pauta && f.pauta !== "-" && f.pauta !== "Sin pauta";
        });

        detalle2ResumenPartido.textContent = etiquetaPartido(etapaId, partidoNumero);
        detalle2ResumenResultado.textContent = resultadoReal ? resultadoReal.pauta : "-";

        if (!filas.length) {
            renderSinDataPartido(mostrarBonus, "No hay datos disponibles para este partido.");
            detalle2Content.hidden = false;
            return;
        }

        filas.forEach(function (fila) {
            var tr = document.createElement("tr");
            appendCell(tr, fila.participante, "");
            appendCell(tr, fila.pronostico, "");
            appendCell(tr, fila.pauta, "");
            appendCell(tr, String(fila.puntosExactitud), clasePuntos(fila.puntosExactitud));
            if (mostrarBonus) {
                appendCell(tr, String(fila.bonus), clasePuntos(fila.bonus));
            }
            appendCell(tr, String(fila.total), clasePuntos(fila.total));
            detalle2Body.appendChild(tr);
        });

        detalle2Content.hidden = false;
    }

    llenarSelectores();
    participanteSel.addEventListener("change", renderDetalleParticipante);
    etapaSel.addEventListener("change", renderDetalleParticipante);
    detalle2EtapaSel.addEventListener("change", function () {
        actualizarSelectorPartido();
        renderDetallePartido();
    });
    detalle2PartidoSel.addEventListener("change", renderDetallePartido);
    renderVacioDetalle();
    renderVacioPartido();
})();
</script>
""".replace("__DETALLE_JSON__", detalle_json).replace("__RESULTADOS_JSON__", resultados_json)

    html = f"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Tabla de posiciones - {titulo_competencia}</title>

<style>
:root {{
    --bg-0: #070b17;
    --bg-1: #0b1020;
    --text: #ecf2ff;
    --muted: rgba(236, 242, 255, 0.72);
    --gold-1: #f3b000;
    --gold-2: #ffdf57;
    --silver-1: #9ea8ba;
    --silver-2: #e3e9f5;
    --bronze-1: #8a4c1f;
    --bronze-2: #d08a4f;
}}

body {{
    font-family: "Trebuchet MS", "Segoe UI", "Gill Sans", sans-serif;
    background:
        radial-gradient(circle at 20% 15%, rgba(70, 122, 255, 0.20), transparent 32%),
        radial-gradient(circle at 80% 0%, rgba(255, 201, 78, 0.16), transparent 28%),
        linear-gradient(165deg, var(--bg-0), var(--bg-1), #0f1730);
    color: var(--text);
    margin: 0;
    padding: 24px;
    min-height: 100vh;
}}

.wrap {{
    max-width: 1200px;
    margin: 0 auto;
}}

.main-title {{
    margin: 0 0 8px 0;
    text-align: center;
    letter-spacing: 0.6px;
    font-size: clamp(28px, 4vw, 48px);
    color: #ffffff;
    text-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
}}

.hero {{
    margin-bottom: 14px;
}}

.sub {{
    text-align: center;
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 18px;
}}

.tabla-title {{
    margin: 0 0 10px 0;
    text-align: center;
    font-size: 22px;
    letter-spacing: 0.3px;
}}

.tabla-topbar {{
    display: flex;
    justify-content: flex-end;
    margin: 0 0 12px 0;
}}

.avance-card {{
    width: min(280px, 100%);
    padding: 14px 16px;
    border-radius: 14px;
    background: rgba(12, 22, 49, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.22);
}}

.avance-label {{
    margin-bottom: 4px;
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}}

.avance-percent {{
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
    line-height: 1;
}}

.avance-progress {{
    height: 9px;
    margin-top: 12px;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.34);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}}

.avance-progress-fill {{
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #50d991, #ffdf57);
}}

table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    background: #121a33;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.30);
}}

th, td {{
    padding: 12px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    word-wrap: break-word;
}}

tbody tr:not(:last-child) td {{
    border-bottom: 1px solid rgba(0, 0, 0, 0.28);
}}

thead tr:first-child {{
    background: #1c2753;
    font-weight: bold;
}}

thead tr:nth-child(2) {{
    background: #141c3a;
    font-size: 13px;
    opacity: 0.85;
}}

tbody tr:hover {{
    background: rgba(255,255,255,0.05);
}}

.tabla-posiciones th.total,
.tabla-posiciones td.total {{
    border: 2px solid #05070d;
}}

td.nombre {{
    text-align: center;
}}

.stage-score {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    white-space: nowrap;
    border-radius: 999px;
    padding: 1px 5px;
    background: rgba(255, 255, 255, 0.06);
}}

.stage-medal {{
    font-size: 14px;
    line-height: 1;
}}

.stage-gold {{
    color: #ffdf57;
    font-weight: 800;
}}

.stage-silver {{
    color: #dfe7f5;
    font-weight: 800;
}}

.stage-bronze {{
    color: #e6a15a;
    font-weight: 800;
}}

tbody tr.podio-oro .stage-score,
tbody tr.podio-plata .stage-score,
tbody tr.podio-bronce .stage-score {{
    color: #111827;
    background: rgba(0, 0, 0, 0.10);
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.12);
}}

.tabla-posiciones col.col-pos {{
    width: 5%;
}}

.tabla-posiciones col.col-nombre {{
    width: 22%;
}}

.tabla-posiciones col.col-total {{
    width: 9%;
}}

.tabla-posiciones col.col-puntaje {{
    width: auto;
}}

.tabla-posiciones th,
.tabla-posiciones td {{
    overflow-wrap: normal;
    word-wrap: normal;
}}

.tabla-posiciones th:nth-child(2),
.tabla-posiciones td.nombre {{
    white-space: normal;
    word-break: keep-all;
    overflow-wrap: normal;
    word-wrap: normal;
    hyphens: none;
    line-height: 1.25;
}}

.tabla-posiciones thead tr:nth-child(2) th,
.tabla-posiciones tbody td:not(.nombre) {{
    white-space: nowrap;
    word-break: normal;
    overflow-wrap: normal;
    word-wrap: normal;
}}

/* Estilo podio dentro de la tabla existente */
tbody tr.podio-oro {{
    background: linear-gradient(90deg, #ffd700, #ffea00, #ffd700);
    color: #1a1a1a;
    font-weight: 700;
}}

tbody tr.podio-plata {{
    background: linear-gradient(90deg, #cfcfcf, #f5f5f5, #cfcfcf);
    color: #1a1a1a;
    font-weight: 700;
}}

tbody tr.podio-bronce {{
    background: linear-gradient(90deg, #cd7f32, #e6a15a, #cd7f32);
    color: #1a1a1a;
    font-weight: 700;
}}

tbody tr.podio-oro:hover,
tbody tr.podio-plata:hover,
tbody tr.podio-bronce:hover {{
    filter: brightness(1.05);
}}

.resultados-wrap {{
    margin-top: 34px;
    padding: 22px;
    border-radius: 16px;
    background: rgba(12, 22, 49, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.25);
}}

.resultados-sub {{
    margin: -8px 0 18px 0;
    color: var(--muted);
    font-size: 14px;
}}

.resultados-layout {{
    display: grid;
    grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
    gap: 18px;
    align-items: start;
}}

.resultados-panel-title {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: baseline;
    margin-bottom: 10px;
}}

.resultados-panel-title strong {{
    font-size: 16px;
}}

.resultados-count {{
    color: var(--muted);
    font-size: 13px;
    white-space: nowrap;
}}

.resultados-note,
.resultados-empty {{
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 12px;
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.06);
    color: var(--muted);
    font-size: 14px;
}}

.resultados-note {{
    margin-bottom: 10px;
}}

.resultados-table th,
.resultados-table td {{
    vertical-align: middle;
}}

.resultados-match-cell strong,
.resultados-match-cell span {{
    display: block;
}}

.resultados-match-cell span {{
    margin-top: 3px;
    color: var(--muted);
    font-size: 12px;
}}

.resultados-match-cell .resultados-schedule-line {{
    margin-top: 4px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.25;
}}

.resultados-match-cell .resultados-venue-line {{
    margin-top: 2px;
    color: rgba(236, 242, 255, 0.50);
    font-size: 11px;
    line-height: 1.25;
}}

.resultados-team {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    line-height: 1.25;
    font-weight: 600;
}}

.resultados-flag {{
    min-width: 1.45em;
    font-size: 18px;
    text-align: center;
}}

.resultados-flag-img {{
    width: 24px;
    height: 18px;
    flex: 0 0 24px;
    border-radius: 3px;
    object-fit: cover;
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18);
}}

.resultados-team-win {{
    color: #91f5a8;
    font-weight: 800;
}}

.resultados-team-pending {{
    color: rgba(236, 242, 255, 0.55);
    font-weight: 500;
}}

.resultados-result-cell {{
    min-width: 170px;
}}

.resultados-badge {{
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 4px 9px;
    margin-bottom: 6px;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.2px;
}}

.resultados-badge-winner {{
    background: rgba(126, 242, 158, 0.14);
    color: #91f5a8;
    border: 1px solid rgba(126, 242, 158, 0.26);
}}

.resultados-badge-draw,
.resultados-badge-text {{
    background: rgba(255, 223, 87, 0.13);
    color: #ffdf57;
    border: 1px solid rgba(255, 223, 87, 0.25);
}}

.resultados-badge-pending {{
    background: rgba(215, 222, 239, 0.10);
    color: rgba(236, 242, 255, 0.62);
    border: 1px solid rgba(215, 222, 239, 0.14);
}}

.resultados-result-line {{
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
}}

.resultados-mode {{
    color: var(--muted);
}}

.resultados-pendiente {{
    opacity: 0.76;
}}

.detalle-wrap {{
    margin-top: 34px;
    padding: 22px;
    border-radius: 16px;
    background: rgba(12, 22, 49, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.25);
}}

.detalle-wrap-sec {{
    margin-top: 18px;
}}

.detalle-title {{
    margin: 0 0 16px 0;
    text-align: left;
    font-size: clamp(20px, 2.4vw, 28px);
}}

.detalle-controls {{
    display: grid;
    grid-template-columns: repeat(2, minmax(220px, 1fr));
    gap: 14px;
}}

.detalle-field {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}

.detalle-field label {{
    font-size: 13px;
    color: var(--muted);
}}

.detalle-select {{
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 10px;
    padding: 10px 12px;
    background: #0e1a3a;
    color: var(--text);
    font-size: 15px;
}}

.detalle-select:disabled {{
    opacity: 0.66;
    cursor: not-allowed;
}}

.detalle-summary {{
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(3, minmax(170px, 1fr));
    gap: 10px;
}}

.detalle-card {{
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 12px 14px;
}}

.detalle-label {{
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 4px;
}}

.detalle-value {{
    font-size: 17px;
    font-weight: 700;
}}

.detalle-total {{
    color: #ffdf57;
}}

.detalle-table-wrap {{
    margin-top: 14px;
    overflow-x: auto;
}}

.detalle-table {{
    width: 100%;
    border-collapse: collapse;
    background: #101a39;
    border-radius: 12px;
    overflow: hidden;
}}

.detalle-table th,
.detalle-table td {{
    padding: 10px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    text-align: left;
    font-size: 14px;
    vertical-align: top;
}}

.detalle-table th {{
    background: #1a2654;
    color: #f6f8ff;
    font-weight: 700;
}}

.detalle-table td.num {{
    text-align: center;
    white-space: nowrap;
}}

.detalle-table td.partido-cell {{
    min-width: 180px;
    color: #dfe7f5;
    font-weight: 700;
}}

.detalle-table th.num {{
    text-align: center;
    white-space: normal;
    line-height: 1.2;
    word-break: break-word;
}}

.pts-pos {{
    color: #7ef29e;
    font-weight: 700;
}}

.pts-zero {{
    color: #d7deef;
}}

@media (max-width: 900px) {{
    table {{
        font-size: 13px;
    }}

    th, td {{
        padding: 10px 8px;
    }}

    .detalle-controls {{
        grid-template-columns: 1fr;
    }}

    .resultados-layout {{
        grid-template-columns: 1fr;
    }}

    .resultados-panel-title {{
        align-items: flex-start;
        flex-direction: column;
    }}

    .detalle-summary {{
        grid-template-columns: 1fr;
    }}

    .detalle-table th,
    .detalle-table td {{
        font-size: 13px;
    }}

    .tabla-topbar {{
        justify-content: center;
    }}
}}

@media (max-width: 600px) {{
    .tabla-topbar {{
        justify-content: stretch;
    }}

    .avance-card {{
        width: 100%;
        box-sizing: border-box;
    }}

    .tabla-posiciones {{
        font-size: 12px;
    }}

    .tabla-posiciones col.col-nombre {{
        width: 23%;
    }}

    .tabla-posiciones col.col-total {{
        width: 10%;
    }}

    .tabla-posiciones th,
    .tabla-posiciones td {{
        padding: 8px 4px;
    }}

    .tabla-posiciones th:first-child,
    .tabla-posiciones td:first-child,
    .tabla-posiciones th:nth-child(n+3),
    .tabla-posiciones td:nth-child(n+3) {{
        padding-left: 3px;
        padding-right: 3px;
    }}

    .tabla-posiciones th:nth-child(2),
    .tabla-posiciones td.nombre {{
        font-size: 11px;
        padding-left: 5px;
        padding-right: 5px;
    }}

    .stage-score {{
        gap: 2px;
        padding-left: 3px;
        padding-right: 3px;
    }}

    .stage-medal {{
        font-size: 12px;
    }}
}}

</style>
</head>

<body>
<div class="wrap">
<div class="hero">
<h1 class="main-title">{titulo_competencia}</h1>
<div class="sub">Generado: {now}</div>
</div>

<div class="tabla-topbar">
    <div class="avance-card" aria-label="Avance del Mundial">
        <div class="avance-label">Avance del Mundial (% de puntos repartidos)</div>
        <div class="avance-percent">{porcentaje_display}</div>
        <div class="avance-progress" aria-hidden="true">
            <div class="avance-progress-fill" style="width: {progreso_width:.1f}%;"></div>
        </div>
    </div>
</div>

<table class="tabla-posiciones">
{colgroup_html}
<thead>
<tr>
{''.join(render_header_cell(h, i) for i, h in enumerate(headers))}
</tr>
<tr>
{''.join(render_header_cell(v, i) for i, v in enumerate(max_row))}
</tr>
</thead>

<tbody>
{''.join(render_body_row(row) for row in body_rows)}
</tbody>

</table>

<section class="resultados-wrap" id="resultados-section">
<h2 class="detalle-title">Resultados actualizados del Mundial</h2>
<p class="resultados-sub">Resultados oficiales con última actualización en {now}</p>

<div class="resultados-layout">
    <div class="detalle-field">
        <label for="resultados-etapa">Etapa</label>
        <select id="resultados-etapa" class="detalle-select">
            <option value="">Selecciona una etapa</option>
        </select>
    </div>

    <div class="resultados-board">
        <div class="resultados-panel-title">
            <strong id="resultados-stage-label">Etapa</strong>
            <span class="resultados-count" id="resultados-stage-count">0 partidos</span>
        </div>
        <div id="resultados-note" class="resultados-note" hidden></div>
        <div id="resultados-empty" class="resultados-empty" hidden></div>
        <div class="detalle-table-wrap" id="resultados-table-wrap" hidden>
            <table class="detalle-table resultados-table">
                <thead>
                    <tr>
                        <th>Partido / horario</th>
                        <th>Equipo A</th>
                        <th>Equipo B</th>
                        <th>Resultado oficial</th>
                    </tr>
                </thead>
                <tbody id="resultados-body"></tbody>
            </table>
        </div>
    </div>
</div>
</section>

<section class="detalle-wrap" id="detalle-section">
<h2 class="detalle-title">Detalle por participante y etapa</h2>

<div class="detalle-controls">
    <div class="detalle-field">
        <label for="detalle-participante">Participante</label>
        <select id="detalle-participante" class="detalle-select">
            <option value="">Selecciona un participante</option>
        </select>
    </div>
    <div class="detalle-field">
        <label for="detalle-etapa">Etapa</label>
        <select id="detalle-etapa" class="detalle-select">
            <option value="">Selecciona una etapa</option>
        </select>
    </div>
</div>

<div id="detalle-content" hidden>
    <div class="detalle-summary">
        <div class="detalle-card">
            <div class="detalle-label">Participante</div>
            <div class="detalle-value" id="detalle-resumen-participante">-</div>
        </div>
        <div class="detalle-card">
            <div class="detalle-label">Etapa</div>
            <div class="detalle-value" id="detalle-resumen-etapa">-</div>
        </div>
        <div class="detalle-card">
            <div class="detalle-label">Total etapa</div>
            <div class="detalle-value detalle-total" id="detalle-resumen-total">0 puntos</div>
        </div>
    </div>

    <div class="detalle-table-wrap">
        <table class="detalle-table">
            <thead>
                <tr id="detalle-head-row"></tr>
            </thead>
            <tbody id="detalle-body"></tbody>
        </table>
    </div>
</div>
</section>

<section class="detalle-wrap detalle-wrap-sec" id="detalle2-section">
<h2 class="detalle-title">Detalle por etapa y partido</h2>

<div class="detalle-controls">
    <div class="detalle-field">
        <label for="detalle2-etapa">Etapa</label>
        <select id="detalle2-etapa" class="detalle-select">
            <option value="">Selecciona una etapa</option>
        </select>
    </div>
    <div class="detalle-field">
        <label for="detalle2-partido">Partido</label>
        <select id="detalle2-partido" class="detalle-select" disabled>
            <option value="">Selecciona un partido</option>
        </select>
    </div>
</div>

<div id="detalle2-content" hidden>
    <div class="detalle-summary">
        <div class="detalle-card">
            <div class="detalle-label">Etapa</div>
            <div class="detalle-value" id="detalle2-resumen-etapa">-</div>
        </div>
        <div class="detalle-card">
            <div class="detalle-label">Partido</div>
            <div class="detalle-value" id="detalle2-resumen-partido">-</div>
        </div>
        <div class="detalle-card">
            <div class="detalle-label">Resultado Real</div>
            <div class="detalle-value" id="detalle2-resumen-resultado">-</div>
        </div>
    </div>

    <div class="detalle-table-wrap">
        <table class="detalle-table">
            <thead>
                <tr id="detalle2-head-row"></tr>
            </thead>
            <tbody id="detalle2-body"></tbody>
        </table>
    </div>
</div>
</section>

{detalle_script}
</div>
</body>
</html>
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

def render_portada_html(out_path):
    html = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Pollas Mundialeras</title>
<style>
body {
    font-family: "Trebuchet MS", "Segoe UI", sans-serif;
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0a1124, #172a59);
    color: #eef3ff;
}
.wrap {
    width: min(560px, calc(100% - 40px));
    background: rgba(8, 16, 37, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 26px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.35);
}
h1 {
    margin: 0 0 8px;
    text-align: center;
}
p {
    margin: 0 0 18px;
    text-align: center;
    color: rgba(238, 243, 255, 0.78);
}
.links {
    display: grid;
    gap: 10px;
}
a {
    display: block;
    text-decoration: none;
    text-align: center;
    padding: 12px;
    border-radius: 10px;
    background: #243f86;
    color: #ffffff;
    font-weight: 700;
}
a:hover {
    background: #2f50a6;
}
</style>
</head>
<body>
<main class="wrap">
<h1>Pollas Mundialeras</h1>
<p>Selecciona una competencia para ver la tabla.</p>
<div class="links">
<a href="./familia/index.html">Ver polla familia</a>
<a href="./curso/index.html">Ver polla curso</a>
</div>
</main>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def generar_competencia(nombre_competencia, nombre_carpeta_participantes, subcarpeta_salida, calendario_por_etapa=None):
    nombre_competencia = str(nombre_competencia).strip()
    titulo_competencia = (
        nombre_competencia
        if nombre_competencia.lower().startswith("polla ")
        else f"Polla {nombre_competencia}"
    )

    print(f"\nGenerando competencia: {nombre_competencia}")
    datos = {}

    # 1) Cargar pautas oficiales desde carpeta Pauta (compartida)
    try:
        carpeta_pauta = resolver_carpeta_pauta(CARPETA)
        (
            pautas_por_etapa,
            fuentes_pauta,
            etapas_faltantes,
            archivos_ignorados,
            enfrentamientos_por_etapa,
            campeon_real_pauta,
            enfrentamientos_detalle_por_etapa,
        ) = cargar_pautas_desde_excel(carpeta_pauta)
    except Exception as e:
        print(f"[{nombre_competencia}] ERROR cargando pauta compartida: {e}")
        return False

    print(f"[{nombre_competencia}] Pautas cargadas desde: {carpeta_pauta}")
    for etapa in sorted(fuentes_pauta.keys(), key=clave_orden_etapa):
        print(f"  - {etapa}: {fuentes_pauta[etapa]}")

    if archivos_ignorados:
        print(f"\n[{nombre_competencia}] Aviso: se ignoraron archivos en pauta:")
        for fn in archivos_ignorados:
            print(f"  - {fn}")

    if etapas_faltantes:
        print(f"\n[{nombre_competencia}] Aviso: faltan pautas para estas etapas:")
        print("  " + ", ".join(etapas_faltantes))
        print("  Se asignará 0 en esas etapas y quedará registrado como error por participante.")

    # 2) Cargar pronósticos de la carpeta específica de la competencia
    try:
        carpeta_participantes = resolver_carpeta_por_nombre(
            CARPETA, nombre_carpeta_participantes
        )
    except Exception as e:
        print(f"[{nombre_competencia}] ERROR cargando carpeta de participantes: {e}")
        return False

    registros, avisos_pronostico, etapas_vacias = cargar_archivos_pronostico(carpeta_participantes)

    if avisos_pronostico:
        print(f"\n[{nombre_competencia}] Aviso: se ignoraron archivos de pronóstico:")
        for aviso in avisos_pronostico:
            print(f"  - {aviso}")

    if etapas_vacias:
        print(f"\n[{nombre_competencia}] Aviso: hay carpetas de etapa sin archivos de pronóstico:")
        print("  " + ", ".join(etapas_vacias))

    if not registros:
        print(
            f"[{nombre_competencia}] ERROR: no encontré pronósticos válidos en "
            f"'{nombre_carpeta_participantes}'. Usa carpetas por etapa (ej: E01 o etapa 01) "
            "y archivos como Nombre.xlsx."
        )
        return False

    procesados = set()

    for reg in registros:
        etapa = reg["etapa"]
        nombre = reg["nombre"]
        pid = reg["pid"]
        ruta = reg["ruta"]
        fn = reg["archivo"]

        datos.setdefault(pid, {
            "nombre": nombre,
            "scores": {e: 0 for e in ETAPAS.keys()},
            "detalle_etapas": {},
            "campeon_pred": None,
            "errores": []
        })

        datos[pid]["nombre"] = nombre

        clave_archivo = (pid, etapa)
        if clave_archivo in procesados:
            datos[pid]["errores"].append(
                f"{fn}: archivo duplicado para {nombre} en etapa {etapa} (se ignoró)."
            )
            continue
        procesados.add(clave_archivo)

        try:
            detalle_etapa = calcular_detalle_etapa(ruta, etapa, pautas_por_etapa)
            pts_etapa = detalle_etapa["total_etapa"]
            datos[pid]["detalle_etapas"][etapa] = detalle_etapa
        except Exception as e:
            pts_etapa = 0
            datos[pid]["errores"].append(f"{fn}: {e}")

        datos[pid]["scores"][etapa] = pts_etapa

        # Guardar campeón pronosticado SOLO desde E01 (B4)
        if etapa == "E01":
            try:
                datos[pid]["campeon_pred"] = leer_campeon_predicho_desde_e01(ruta)
            except Exception as e:
                datos[pid]["campeon_pred"] = None
                datos[pid]["errores"].append(f"{fn}: error leyendo campeón en B4: {e}")

    # 3) Orden de etapas (ya existe para toda la impresión)
    etapas_ordenadas = sorted(ETAPAS.keys(), key=clave_orden_etapa)

    # 4) Parámetros de impresión "tipo Excel"
    W_POS = 4
    W_NOMBRE = 12
    W_ETAPA = 12
    W_BONUS = 15
    W_TOTAL = 10

    max_por_etapa = {}
    for e, cfg in ETAPAS.items():
        if cfg["tipo"] == "GRUPOS":
            max_por_etapa[e] = cfg["n_partidos"] * cfg["ppp"]
        else:
            max_por_etapa[e] = cfg["n_partidos"] * (cfg["ppp"] + 1)

    max_bonus = BONUS_PTS
    max_total = sum(max_por_etapa.values()) + max_bonus

    def c(text, w):
        return f"{str(text):^{w}}"

    def l(text, w):
        return f"{str(text):<{w}}"

    ancho_tabla = (
        W_POS + 1 + W_NOMBRE + 1 +
        len(etapas_ordenadas) * (W_ETAPA + 1) +
        (W_BONUS + 1) + W_TOTAL
    )

    # Normalización simple para comparar campeones
    def norm(x):
        if x is None:
            return ""
        return str(x).strip().upper()

    campeon_real_oficial = campeon_real_pauta
    if not norm(campeon_real_oficial):
        campeon_real_oficial = CAMPEON_REAL_MANUAL
    campeon_real_norm = norm(campeon_real_oficial)

    if norm(campeon_real_pauta):
        print(f"\n[{nombre_competencia}] Campeón oficial desde pauta E01 (B4): {campeon_real_pauta}")
    elif norm(CAMPEON_REAL_MANUAL):
        print(f"\n[{nombre_competencia}] Aviso: B4 de E01Pauta está vacío. Usando CAMPEON_REAL_MANUAL como fallback.")
    else:
        print(f"\n[{nombre_competencia}] Aviso: no hay campeón oficial en E01Pauta (B4 vacío). No se asignará Bono Campeón.")

    puntos_repartidos = calcular_puntos_repartidos(
        pautas_por_etapa=pautas_por_etapa,
        campeon_real_oficial=campeon_real_oficial,
        max_por_etapa=max_por_etapa,
        max_bonus=max_bonus,
    )
    porcentaje_avance = (puntos_repartidos / max_total * 100) if max_total else 0

    # 5) Ranking general (sin grupos)
    participantes = []

    for pid, info in datos.items():
        bono = 0
        if campeon_real_norm and norm(info.get("campeon_pred")) == campeon_real_norm:
            bono = BONUS_PTS

        total = sum(info["scores"].values()) + bono
        participantes.append((pid, info["nombre"], info["scores"], bono, total, info["errores"]))

    participantes.sort(key=lambda x: (-x[4], x[1].upper()))  # total desc, nombre asc

    print("\n" + "=" * ancho_tabla)
    print(f"Tabla de posiciones - {titulo_competencia}")
    print("=" * ancho_tabla)

    # Header fila 1
    header1 = l("Pos", W_POS) + " " + l("Nombre", W_NOMBRE) + " " + c("Total", W_TOTAL) + " "
    for e in etapas_ordenadas:
        header1 += c(ETIQUETAS_ETAPAS[e], W_ETAPA) + " "
    header1 += c(NOMBRE_COLUMNA_BONUS, W_BONUS)
    print(header1)

    # Header fila 2 (máximos)
    header2 = (" " * W_POS) + " " + (" " * W_NOMBRE) + " " + c(f"Max={max_total}", W_TOTAL) + " "
    for e in etapas_ordenadas:
        header2 += c(f"Max={max_por_etapa[e]}", W_ETAPA) + " "
    header2 += c(f"Max={max_bonus}", W_BONUS)
    print(header2)

    print("-" * len(header1))

    posiciones_participantes = calcular_posiciones_con_empate(participantes)

    # Filas
    for pos, (pid, nombre, scores, bono, total, errores) in zip(posiciones_participantes, participantes):
        row = l(pos, W_POS) + " " + l(nombre, W_NOMBRE) + " " + c(total, W_TOTAL) + " "
        for e in etapas_ordenadas:
            row += c(scores[e], W_ETAPA) + " "
        row += c(bono, W_BONUS)
        print(row)

        for err in errores:
            print(f"  -> ERROR: {err}")

    participantes_html = []
    for pos, (pid, nombre, scores, bono, total, errores) in zip(posiciones_participantes, participantes):
        participantes_html.append((pid, pos, nombre, scores, bono, total))

    participantes_select = [
        {"id": pid, "name": info["nombre"]}
        for pid, info in sorted(datos.items(), key=lambda x: x[1]["nombre"].upper())
    ]
    etapas_comenzadas = {
        e: etapa_comenzada(pautas_por_etapa, e)
        for e in etapas_ordenadas
    }
    etapas_finalizadas = {
        e: etapa_finalizada(pautas_por_etapa, e)
        for e in etapas_ordenadas
    }
    podios_por_etapa = calcular_podios_por_etapa(
        participantes=participantes,
        etapas_ordenadas=etapas_ordenadas,
        etapas_finalizadas=etapas_finalizadas,
    )
    etapas_select = [
        {
            "id": e,
            "label": etiqueta_etapa_larga(e),
            "show_bonus": ETAPAS[e]["tipo"] != "GRUPOS",
            "started": etapas_comenzadas[e],
        }
        for e in etapas_ordenadas
    ]
    detalles_ui = {}
    for pid, info in datos.items():
        detalles_ui[pid] = {}
        for etapa in etapas_ordenadas:
            if not etapas_comenzadas[etapa]:
                continue
            detalle = info.get("detalle_etapas", {}).get(etapa)
            if not detalle:
                continue
            detalles_ui[pid][etapa] = {
                "total": detalle["total_etapa"],
                "partidos": detalle["partidos"],
            }

    payload_detalle = {
        "participants": participantes_select,
        "stages": etapas_select,
        "details": detalles_ui,
        "match_labels": {
            e: enfrentamientos_por_etapa.get(e, [])
            for e in etapas_ordenadas
        },
    }
    payload_resultados = construir_resultados_payload(
        etapas_ordenadas=etapas_ordenadas,
        pautas_por_etapa=pautas_por_etapa,
        enfrentamientos_detalle_por_etapa=enfrentamientos_detalle_por_etapa,
        calendario_por_etapa=calendario_por_etapa,
    )

    out_dir = os.path.join(OUTPUT_DIR, subcarpeta_salida)
    os.makedirs(out_dir, exist_ok=True)
    out_html = os.path.join(out_dir, "index.html")
    render_tabla_html(
        nombre_competencia=titulo_competencia,
        participantes=participantes_html,
        etapas_ordenadas=etapas_ordenadas,
        max_por_etapa=max_por_etapa,
        max_bonus=max_bonus,
        max_total=max_total,
        out_path=out_html,
        detalle_payload=payload_detalle,
        resultados_payload=payload_resultados,
        puntos_repartidos=puntos_repartidos,
        porcentaje_avance=porcentaje_avance,
        podios_por_etapa=podios_por_etapa,
    )
    print(f"[{nombre_competencia}] HTML generado: {out_html}")
    return True


def main():
    calendario_por_etapa = preparar_y_cargar_calendario()

    resultados = {}
    resultados["familia"] = generar_competencia(
        nombre_competencia="familia",
        nombre_carpeta_participantes="Participantes_Familia",
        subcarpeta_salida="familia",
        calendario_por_etapa=calendario_por_etapa,
    )
    resultados["curso"] = generar_competencia(
        nombre_competencia="Segundos Medios",
        nombre_carpeta_participantes="Participantes_Curso",
        subcarpeta_salida="curso",
        calendario_por_etapa=calendario_por_etapa,
    )

    out_portada = os.path.join(OUTPUT_DIR, "index.html")
    render_portada_html(out_portada)
    print(f"\nPortada generada: {out_portada}")

    if not any(resultados.values()):
        print("\nERROR: no se pudo generar ninguna competencia.")
        sys.exit(1)



if __name__ == "__main__":
    main()

import os
import re
import json
import sys
from openpyxl import load_workbook
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA = BASE_DIR

OUTPUT_DIR = os.path.join(BASE_DIR, "site")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def clave_orden_etapa(etapa):
    m = re.match(r"^E(\d{2})$", str(etapa).upper())
    return int(m.group(1)) if m else 9999


def etiqueta_etapa_larga(etapa):
    nombre = ETIQUETAS_ETAPAS.get(etapa, etapa)
    if str(etapa).upper() == "E01":
        nombre = "Fase de grupos"
    return nombre

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


def resolver_carpeta_participantes(carpeta_base):
    for nombre in os.listdir(carpeta_base):
        ruta = os.path.join(carpeta_base, nombre)
        if os.path.isdir(ruta) and nombre.lower() == "participantes":
            return ruta
    raise FileNotFoundError(
        f"No encontré la carpeta 'Participantes' dentro de: {carpeta_base}"
    )


def resolver_carpeta_pauta(carpeta_base):
    # Busca "pauta" sin depender de mayúsculas/minúsculas.
    for nombre in os.listdir(carpeta_base):
        ruta = os.path.join(carpeta_base, nombre)
        if os.path.isdir(ruta) and nombre.lower() == "pauta":
            return ruta
    raise FileNotFoundError(
        f"No encontré la carpeta 'pauta' dentro de: {carpeta_base}"
    )


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
        enfrentamientos_etapa = leer_enfrentamientos_etapa(ws, cfg)

        if len(pauta_etapa) != cfg["n_partidos"]:
            raise ValueError(
                f"La pauta {fn} ({etapa}) no tiene {cfg['n_partidos']} partidos."
            )

        pautas[etapa] = pauta_etapa
        fuentes[etapa] = fn
        enfrentamientos[etapa] = enfrentamientos_etapa

    if not pautas:
        raise ValueError(
            f"No pude cargar pautas válidas desde: {carpeta_pauta}. "
            "Asegúrate de usar archivos cuyo nombre comience por etapa (ej: E01...)."
        )

    faltantes = [e for e in sorted(ETAPAS.keys()) if e not in pautas]
    return pautas, fuentes, faltantes, ignorados, enfrentamientos, campeon_real_pauta


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
        if normalizar_texto(pasa) != normalizar_texto(pasa_real):
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


def formatear_prediccion_elim(pasa, modo):
    vp = valor_visible(pasa)
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


def leer_enfrentamientos_etapa(ws, cfg, celda_inicial=CELDA_INICIAL_RESULTADO, salto_filas=SALTO_FILAS):
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
        fila_enfrentamiento = (fila_prediccion - 1) + (i * salto_filas)
        equipo_a = ws[f"{col_equipo_a}{fila_enfrentamiento}"].value
        equipo_b = ws[f"{col_equipo_b}{fila_enfrentamiento}"].value
        out.append(formatear_enfrentamiento(equipo_a, equipo_b, i + 1))
    return out


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

            pauta_pasa_llena = normalizar_texto(pasa_real) != ""
            pauta_modo_llena = normalizar_texto(modo_real) != ""     
            acierta_pasa = pauta_pasa_llena and (normalizar_texto(pasa) == normalizar_texto(pasa_real))
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

def render_tabla_html(nombre_competencia, participantes, etapas_ordenadas,
                      max_por_etapa, max_bonus, max_total, out_path,
                      detalle_payload):

    now = datetime.now(ZoneInfo("America/Santiago")).strftime("%Y-%m-%d %H:%M:%S")
    titulo_competencia = html_escape(nombre_competencia)
    detalle_json = json.dumps(detalle_payload, ensure_ascii=False).replace("</", "<\\/")

    headers = ["Pos", "Nombre"] \
              + [ETIQUETAS_ETAPAS[e] for e in etapas_ordenadas] \
              + [NOMBRE_COLUMNA_BONUS, "Total"]

    max_row = ["", ""] \
              + [f"Max={max_por_etapa[e]}" for e in etapas_ordenadas] \
              + [f"Max={max_bonus}", f"Max={max_total}"]

    body_rows = []
    for pos, nombre, scores, bono, total in participantes:
        row = [pos, nombre] \
              + [scores[e] for e in etapas_ordenadas] \
              + [bono, total]
        body_rows.append(row)

    def top_podio(posicion, nombre_default, puntos_default):
        if len(participantes) >= posicion:
            _, nombre, _, _, total = participantes[posicion - 1]
            return {
                "pos": posicion,
                "nombre": html_escape(nombre),
                "puntos": total
            }
        return {
            "pos": posicion,
            "nombre": html_escape(nombre_default),
            "puntos": puntos_default
        }

    podio_1 = top_podio(1, "Nombre 1", 120)
    podio_2 = top_podio(2, "Nombre 2", 110)
    podio_3 = top_podio(3, "Nombre 3", 95)

    detalle_script = """
<script id="detalle-data" type="application/json">__DETALLE_JSON__</script>
<script>
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
        td.colSpan = mostrarBonus ? 5 : 4;
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
        resetSelect(detalle2PartidoSel, "Selecciona un partido");

        if (!etapaId) {
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

        if (!detalle) {
            resumenTotal.textContent = "0 puntos";
            renderSinDataDetalle(mostrarBonus, "Sin pronóstico disponible para este participante en esta etapa.");
            content.hidden = false;
            return;
        }

        resumenTotal.textContent = String(detalle.total) + " puntos";
        (detalle.partidos || []).forEach(function (partido) {
            var tr = document.createElement("tr");
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
        var partidoNumero = Number(detalle2PartidoSel.value);
        detalle2Body.innerHTML = "";

        if (!etapaId || !detalle2PartidoSel.value) {
            renderVacioPartido();
            return;
        }

        var etapa = buscarEtapa(etapaId);
        var mostrarBonus = !!(etapa && etapa.show_bonus);
        renderHeaderPartido(mostrarBonus);

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

        detalle2ResumenEtapa.textContent = etapa ? etapa.label : etapaId;
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
""".replace("__DETALLE_JSON__", detalle_json)

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

.podio-wrap {{
    margin: 18px auto 30px;
}}

.podio-title {{
    margin: 0 0 14px 0;
    text-align: center;
    font-size: 20px;
    letter-spacing: 0.4px;
}}

.podio-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(170px, 1fr));
    gap: 16px;
    align-items: end;
    max-width: 900px;
    margin: 0 auto;
}}

.podio-step {{
    border-radius: 18px 18px 10px 10px;
    padding: 16px 12px 14px;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 14px 35px rgba(0, 0, 0, 0.35);
}}

.podio-num {{
    font-size: clamp(42px, 6vw, 74px);
    font-weight: 800;
    line-height: 0.9;
    margin-top: 6px;
}}

.podio-name {{
    margin-top: 12px;
    font-size: clamp(16px, 2vw, 22px);
    font-weight: 700;
    word-break: break-word;
}}

.podio-points {{
    margin-top: 6px;
    font-size: clamp(14px, 1.8vw, 18px);
    font-weight: 600;
    opacity: 0.95;
}}

.podio-first {{
    min-height: 300px;
    background: linear-gradient(180deg, var(--gold-2), var(--gold-1));
    color: #2f2300;
}}

.podio-second {{
    min-height: 235px;
    background: linear-gradient(180deg, var(--silver-2), var(--silver-1));
    color: #152033;
}}

.podio-third {{
    min-height: 205px;
    background: linear-gradient(180deg, var(--bronze-2), var(--bronze-1));
    color: #28160b;
}}

.tabla-title {{
    margin: 0 0 10px 0;
    text-align: center;
    font-size: 22px;
    letter-spacing: 0.3px;
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

td.total {{
    font-weight: bold;
    font-size: 16px;
}}

td.nombre {{
    text-align: center;
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

tbody tr.podio-oro td.total,
tbody tr.podio-plata td.total,
tbody tr.podio-bronce td.total {{
    font-size: 18px;
    font-weight: 800;
}}

tbody tr.podio-oro:hover,
tbody tr.podio-plata:hover,
tbody tr.podio-bronce:hover {{
    filter: brightness(1.05);
}}

tbody tr.podio-oro td:first-child::before {{
    content: "1";
    font-weight: 800;
}}

tbody tr.podio-plata td:first-child::before {{
    content: "2";
    font-weight: 800;
}}

tbody tr.podio-bronce td:first-child::before {{
    content: "3";
    font-weight: 800;
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
    .podio-grid {{
        grid-template-columns: 1fr;
        max-width: 440px;
    }}

    .podio-first {{
        min-height: 220px;
        order: 1;
    }}

    .podio-second {{
        min-height: 180px;
        order: 2;
    }}

    .podio-third {{
        min-height: 165px;
        order: 3;
    }}

    table {{
        font-size: 13px;
    }}

    th, td {{
        padding: 10px 8px;
    }}

    .detalle-controls {{
        grid-template-columns: 1fr;
    }}

    .detalle-summary {{
        grid-template-columns: 1fr;
    }}

    .detalle-table th,
    .detalle-table td {{
        font-size: 13px;
    }}
}}

</style>
</head>

<body>
<div class="wrap">
<div class="hero">
<h1 class="main-title">Polla Familia Riesco Eyzaguirre</h1>
<div class="sub">Generado: {now}</div>
</div>

<section class="podio-wrap" aria-label="Podio actual">
<div class="podio-grid">
<article class="podio-step podio-second">
<div class="podio-num">{podio_2["pos"]}&deg;</div>
<div class="podio-name">{podio_2["nombre"]}</div>
<div class="podio-points">{podio_2["puntos"]} puntos</div>
</article>
<article class="podio-step podio-first">
<div class="podio-num">{podio_1["pos"]}&deg;</div>
<div class="podio-name">{podio_1["nombre"]}</div>
<div class="podio-points">{podio_1["puntos"]} puntos</div>
</article>
<article class="podio-step podio-third">
<div class="podio-num">{podio_3["pos"]}&deg;</div>
<div class="podio-name">{podio_3["nombre"]}</div>
<div class="podio-points">{podio_3["puntos"]} puntos</div>
</article>
</div>
</section>

<table>
<thead>
<tr>
{''.join(f"<th>{h}</th>" for h in headers)}
</tr>
<tr>
{''.join(f"<th>{v}</th>" for v in max_row)}
</tr>
</thead>

<tbody>
{''.join(
    (f"<tr class='podio-oro'>" if idx == 0 else
     f"<tr class='podio-plata'>" if idx == 1 else
     f"<tr class='podio-bronce'>" if idx == 2 else
     "<tr>") +
    "".join(
        f"<td></td>" if (idx in [0,1,2] and i == 0) else
        f"<td class='total'>{html_escape(cell)}</td>" if i == len(row)-1 else
        f"<td class='nombre'>{html_escape(cell)}</td>" if i == 1 else
        f"<td>{html_escape(cell)}</td>"
        for i, cell in enumerate(row)
    ) +
    "</tr>"
    for idx, row in enumerate(body_rows)
)}
</tbody>

</table>

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

def main():
    datos = {}

    # 1) Cargar pautas oficiales desde carpeta pauta
    try:
        carpeta_pauta = resolver_carpeta_pauta(CARPETA)
        (
            pautas_por_etapa,
            fuentes_pauta,
            etapas_faltantes,
            archivos_ignorados,
            enfrentamientos_por_etapa,
            campeon_real_pauta,
        ) = cargar_pautas_desde_excel(carpeta_pauta)
    except Exception as e:
        print(f"ERROR cargando pautas desde carpeta 'pauta': {e}")
        sys.exit(1)

    print(f"Pautas cargadas desde: {carpeta_pauta}")
    for etapa in sorted(fuentes_pauta.keys(), key=clave_orden_etapa):
        print(f"  - {etapa}: {fuentes_pauta[etapa]}")

    if archivos_ignorados:
        print("\nAviso: se ignoraron archivos en pauta (nombre no reconocido o etapa no configurada):")
        for fn in archivos_ignorados:
            print(f"  - {fn}")

    if etapas_faltantes:
        print("\nAviso: faltan pautas para estas etapas:")
        print("  " + ", ".join(etapas_faltantes))
        print("  Se asignará 0 en esas etapas y quedará registrado como error por participante.")

    # 2) Cargar pronósticos desde carpeta Participantes por etapa
    try:
        carpeta_participantes = resolver_carpeta_participantes(CARPETA)
    except Exception as e:
        print(f"ERROR cargando carpeta de participantes: {e}")
        sys.exit(1)

    registros, avisos_pronostico, etapas_vacias = cargar_archivos_pronostico(carpeta_participantes)

    if avisos_pronostico:
        print("\nAviso: se ignoraron archivos de pronóstico:")
        for aviso in avisos_pronostico:
            print(f"  - {aviso}")

    if etapas_vacias:
        print("\nAviso: hay carpetas de etapa sin archivos de pronóstico:")
        print("  " + ", ".join(etapas_vacias))

    if not registros:
        print(
            "No encontré archivos de pronóstico válidos en la carpeta Participantes. "
            "Usa carpetas por etapa (ej: E01 o etapa 01) y archivos como Nombre.xlsx."
        )
        sys.exit(1)

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
        print(f"\nCampeón oficial desde pauta E01 (B4): {campeon_real_pauta}")
    elif norm(CAMPEON_REAL_MANUAL):
        print("\nAviso: B4 de E01Pauta está vacío. Usando CAMPEON_REAL_MANUAL como fallback.")
    else:
        print("\nAviso: no hay campeón oficial en E01Pauta (B4 vacío). No se asignará Bono Campeón.")

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
    print("Tabla de posiciones - General")
    print("=" * ancho_tabla)

    # Header fila 1
    header1 = l("Pos", W_POS) + " " + l("Nombre", W_NOMBRE) + " "
    for e in etapas_ordenadas:
        header1 += c(ETIQUETAS_ETAPAS[e], W_ETAPA) + " "
    header1 += c(NOMBRE_COLUMNA_BONUS, W_BONUS) + " " + c("Total", W_TOTAL)
    print(header1)

    # Header fila 2 (máximos)
    header2 = (" " * W_POS) + " " + (" " * W_NOMBRE) + " "
    for e in etapas_ordenadas:
        header2 += c(f"Max={max_por_etapa[e]}", W_ETAPA) + " "
    header2 += c(f"Max={max_bonus}", W_BONUS) + " " + c(f"Max={max_total}", W_TOTAL)
    print(header2)

    print("-" * len(header1))

    # Filas
    for i, (pid, nombre, scores, bono, total, errores) in enumerate(participantes, start=1):
        row = l(i, W_POS) + " " + l(nombre, W_NOMBRE) + " "
        for e in etapas_ordenadas:
            row += c(scores[e], W_ETAPA) + " "
        row += c(bono, W_BONUS) + " " + c(total, W_TOTAL)
        print(row)

        for err in errores:
            print(f"  -> ERROR: {err}")

    participantes_html = []
    for idx, (pid, nombre, scores, bono, total, errores) in enumerate(participantes, start=1):
        participantes_html.append((idx, nombre, scores, bono, total))

    participantes_select = [
        {"id": pid, "name": info["nombre"]}
        for pid, info in sorted(datos.items(), key=lambda x: x[1]["nombre"].upper())
    ]
    etapas_select = [
        {
            "id": e,
            "label": etiqueta_etapa_larga(e),
            "show_bonus": ETAPAS[e]["tipo"] != "GRUPOS",
        }
        for e in etapas_ordenadas
    ]
    detalles_ui = {}
    for pid, info in datos.items():
        detalles_ui[pid] = {}
        for etapa in etapas_ordenadas:
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

    out_html = os.path.join(OUTPUT_DIR, "index.html")
    render_tabla_html(
        nombre_competencia="General",
        participantes=participantes_html,
        etapas_ordenadas=etapas_ordenadas,
        max_por_etapa=max_por_etapa,
        max_bonus=max_bonus,
        max_total=max_total,
        out_path=out_html,
        detalle_payload=payload_detalle
    )



if __name__ == "__main__":
    main()

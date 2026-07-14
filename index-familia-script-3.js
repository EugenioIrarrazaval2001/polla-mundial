
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
            texto = texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        }
        return texto.replace(/[^A-Z0-9]+/g, " ").replace(/\s+/g, " ").trim();
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
    var bonusCampeon = payload.bonus_champion || {};
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
    var bonusResumenEstado = document.getElementById("bonus-resumen-estado");
    var bonusResumenOficial = document.getElementById("bonus-resumen-oficial");
    var bonusResumenRespuestas = document.getElementById("bonus-resumen-respuestas");
    var bonusBody = document.getElementById("bonus-body");

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

    function renderBonusCampeon() {
        if (!bonusBody) return;

        var started = !!bonusCampeon.started;
        var filas = Array.isArray(bonusCampeon.participants) ? bonusCampeon.participants.slice() : [];
        bonusBody.innerHTML = "";

        if (bonusResumenEstado) {
            bonusResumenEstado.textContent = started ? "Visible" : "Pendiente";
        }
        if (bonusResumenOficial) {
            bonusResumenOficial.textContent = bonusCampeon.official_champion || "-";
        }
        if (bonusResumenRespuestas) {
            bonusResumenRespuestas.textContent = started ? String(filas.length) : "-";
        }

        if (!started) {
            var trPendiente = document.createElement("tr");
            var tdPendiente = document.createElement("td");
            tdPendiente.colSpan = 3;
            tdPendiente.textContent = MENSAJE_RONDA_NO_COMIENZA;
            trPendiente.appendChild(tdPendiente);
            bonusBody.appendChild(trPendiente);
            return;
        }

        if (!filas.length) {
            var trVacio = document.createElement("tr");
            var tdVacio = document.createElement("td");
            tdVacio.colSpan = 3;
            tdVacio.textContent = "Sin pronósticos de campeón disponibles.";
            trVacio.appendChild(tdVacio);
            bonusBody.appendChild(trVacio);
            return;
        }

        filas.sort(function (a, b) {
            return String(a.name || "").localeCompare(String(b.name || ""), "es", { sensitivity: "base" });
        });

        filas.forEach(function (fila) {
            var tr = document.createElement("tr");
            appendCell(tr, fila.name || "-", "");
            appendCell(tr, fila.champion || "Sin dato", "");
            appendCell(tr, String(fila.points || 0), clasePuntos(fila.points || 0));
            bonusBody.appendChild(tr);
        });
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
    renderBonusCampeon();
})();

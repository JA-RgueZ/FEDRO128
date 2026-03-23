import os
import json
import re # Import regex module for validation
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
import gspread
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build # New import for Google Drive API

# --- METADATA DEL PROYECTO ---
VERSION = "1.03.015" # Versión actualizada para asegurar un cambio detectable
app = FastAPI(title="FEDRO API", version=VERSION)

# --- Configuración CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HTML TESTER INCRUSTADO ---
TESTER_HTML = '<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>FEDRO API Tester</title>\n    <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">\n    <style>\n        :root {\n            --bg: #0a0c10; --surface: #111318; --surface2: #181c24;\n            --border: #1e2430; --accent: #00e5a0; --accent2: #0070f3;\n            --accent3: #ff4d6d; --text: #e8e4f0; --muted: #5a6070;\n            --mono: \'Space Mono\', monospace; --sans: \'Syne\', sans-serif;\n        }\n        * { box-sizing: border-box; margin: 0; padding: 0; }\n        body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }\n        body::before {\n            content: \'\'; position: fixed; inset: 0;\n            background-image: linear-gradient(rgba(0,229,160,0.03) 1px, transparent 1px),\n                              linear-gradient(90deg, rgba(0,229,160,0.03) 1px, transparent 1px);\n            background-size: 40px 40px; pointer-events: none; z-index: 0;\n        }\n        .wrapper { position: relative; z-index: 1; max-width: 860px; margin: 0 auto; padding: 48px 24px 80px; }\n        header { margin-bottom: 56px; display: flex; align-items: flex-start; gap: 20px; }\n        .logo-badge {\n            width: 52px; height: 52px; background: var(--accent); border-radius: 12px;\n            display: flex; align-items: center; justify-content: center; flex-shrink: 0;\n            font-family: var(--mono); font-size: 11px; font-weight: 700; color: #000;\n            letter-spacing: -0.5px; line-height: 1.1; text-align: center; padding: 6px;\n        }\n        .header-text h1 { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: var(--text); line-height: 1; margin-bottom: 8px; }\n        .header-text h1 span { color: var(--accent); }\n        .header-text p { font-family: var(--mono); font-size: 12px; color: var(--muted); }\n        .header-text p code { color: var(--accent); background: rgba(0,229,160,0.08); padding: 2px 6px; border-radius: 4px; font-size: 11px; }\n        .status-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 40px; font-family: var(--mono); font-size: 11px; color: var(--muted); }\n        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 2s ease-in-out infinite; }\n        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }\n        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; margin-bottom: 20px; overflow: hidden; transition: border-color 0.2s; }\n        .card:hover { border-color: #2a3040; }\n        .card-header { padding: 20px 24px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }\n        .method-badge { font-family: var(--mono); font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: rgba(0,112,243,0.15); color: var(--accent2); border: 1px solid rgba(0,112,243,0.25); letter-spacing: 1px; }\n        .endpoint-path { font-family: var(--mono); font-size: 14px; color: var(--text); flex: 1; }\n        .endpoint-path .param { color: var(--accent); }\n        .card-body { padding: 20px 24px 24px; }\n        label { display: block; font-family: var(--mono); font-size: 11px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }\n        .input-row { display: flex; gap: 10px; align-items: stretch; }\n        input[type="text"] { flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px; font-family: var(--mono); font-size: 13px; color: var(--text); outline: none; transition: border-color 0.2s, box-shadow 0.2s; }\n        input[type="text"]:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,229,160,0.1); }\n        input[type="text"]::placeholder { color: var(--muted); }\n        button { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 12px 20px; font-family: var(--sans); font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity 0.15s, transform 0.1s; white-space: nowrap; display: flex; align-items: center; gap: 7px; }\n        button:hover { opacity: 0.88; }\n        button:active { transform: scale(0.97); }\n        button.loading { opacity: 0.6; pointer-events: none; }\n        .result-box { margin-top: 16px; border-radius: 10px; overflow: hidden; background: var(--surface2); border: 1px solid var(--border); display: none; }\n        .result-box.visible { display: block; }\n        .result-header { padding: 8px 14px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); }\n        .result-label { font-family: var(--mono); font-size: 10px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }\n        .status-code { font-family: var(--mono); font-size: 11px; padding: 2px 8px; border-radius: 5px; }\n        .status-code.ok { background: rgba(0,229,160,0.12); color: var(--accent); }\n        .status-code.error { background: rgba(255,48,70,0.12); color: var(--accent3); }\n        .result-body { padding: 14px; max-height: 300px; overflow-y: auto; }\n        pre { font-family: var(--mono); font-size: 12px; line-height: 1.7; color: #a8b4c8; white-space: pre-wrap; word-break: break-all; }\n        pre .json-key { color: #7ec8e3; }\n        pre .json-string { color: #a8e6b0; }\n        pre .json-number { color: #ffd580; }\n        pre .json-bool { color: #ff8c69; }\n        pre .json-null { color: var(--muted); }\n        .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.2); border-top-color: #000; border-radius: 50%; animation: spin 0.6s linear infinite; }\n        @keyframes spin { to { transform: rotate(360deg); } }\n        footer { margin-top: 60px; text-align: center; font-family: var(--mono); font-size: 11px; color: var(--muted); }\n        ::-webkit-scrollbar { width: 6px; }\n        ::-webkit-scrollbar-track { background: transparent; }\n        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }\n    </style>\n</head>\n<body>\n<div class="wrapper">\n    <header>\n        <div class="logo-badge">FE<br>DRO</div>\n        <div class="header-text">\n            <h1>FEDRO <span>API</span> Tester</h1>\n            <p>Conectado a: {api_base_url_placeholder}</p>\n            <p>API Version: {api_version_placeholder} &middot; Entorno: {api_environment_placeholder}</p>\n        </div>\n    </header>\n    <div class="status-bar">\n        <div class="status-dot"></div>\n        RAILWAY &middot; PRODUCCI&Oacute;N &middot; REST API\n    </div>\n\n    <!-- Auth Endpoints -->\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/auth/perfil/{telefono}</span>\n        </div>\n        <div class="card-body">\n            <label for="telefonoPerfil">Tel&eacute;fono &mdash; formato internacional</label>\n            <div class="input-row">\n                <input type="text" id="telefonoPerfil" placeholder="912345678">\n                <button onclick="getPerfil(this)"><span>&#8594;</span> Obtener Perfil</button>\n            </div>\n            <div class="result-box" id="boxPerfil">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusPerfil"></span></div>\n                <div class="result-body"><pre id="resultPerfil"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/auth/rut/{telefono}</span>\n        </div>\n        <div class="card-body">\n            <label for="telefonoRut">Tel&eacute;fono &mdash; formato internacional</label>\n            <div class="input-row">\n                <input type="text" id="telefonoRut" placeholder="912345678">\n                <button onclick="getRut(this)"><span>&#8594;</span> Obtener RUT</button>\n            </div>\n            <div class="result-box" id="boxRut">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusRut"></span></div>\n                <div class="result-body"><pre id="resultRut"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/auth/clientall/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutClientall">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutClientall" placeholder="12345678">\n                <button onclick="getClientall(this)"><span>&#8594;</span> Obtener Cliente</button>\n            </div>\n            <div class="result-box" id="boxClientall">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusClientall"></span></div>\n                <div class="result-body"><pre id="resultClientall"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <!-- Financial Endpoints -->\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/membresia_anual/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutMembresia">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutMembresia" placeholder="12345678">\n                <button onclick="getMembresiaAnual(this)"><span>&#8594;</span> Membres&iacute;a Anual</button>\n            </div>\n            <div class="result-box" id="boxMembresia">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusMembresia"></span></div>\n                <div class="result-body"><pre id="resultMembresia"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/deuda_arrastre/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutDeudaArrastre">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutDeudaArrastre" placeholder="12345678">\n                <button onclick="getDeudaArrastre(this)"><span>&#8594;</span> Deuda de Arrastre</button>\n            </div>\n            <div class="result-box" id="boxDeudaArrastre">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusDeudaArrastre"></span></div>\n                <div class="result-body"><pre id="resultDeudaArrastre"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/cuota_anual/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutCuotaAnual">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutCuotaAnual" placeholder="12345678">\n                <button onclick="getCuotaAnual(this)"><span>&#8594;</span> Cuota Anual</button>\n            </div>\n            <div class="result-box" id="boxCuotaAnual">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusCuotaAnual"></span></div>\n                <div class="result-body"><pre id="resultCuotaAnual"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/pagado_a_la_fecha/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutPagadoFecha">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutPagadoFecha" placeholder="12345678">\n                <button onclick="getPagadoALaFecha(this)"><span>&#8594;</span> Pagado a la Fecha</button>\n            </div>\n            <div class="result-box" id="boxPagadoFecha">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusPagadoFecha"></span></div>\n                <div class="result-body"><pre id="resultPagadoFecha"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/deuda/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutDeuda">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutDeuda" placeholder="12345678">\n                <button onclick="getDeuda(this)"><span>&#8594;</span> Obtener Deuda</button>\n            </div>\n            <div class="result-box" id="boxDeuda">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusDeuda"></span></div>\n                <div class="result-body"><pre id="resultDeuda"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/mensaje/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutMensaje">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutMensaje" placeholder="12345678">\n                <button onclick="getMensaje(this)"><span>&#8594;</span> Obtener Mensaje</button>\n            </div>\n            <div class="result-box" id="boxMensaje">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusMensaje"></span></div>\n                <div class="result-body"><pre id="resultMensaje"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <!-- ENDPOINT CONSOLIDADO -->\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/financial/all/{rut_without_dv}</span>\n        </div>\n        <div class="card-body">\n            <label for="rutFinancialAll">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>\n            <div class="input-row">\n                <input type="text" id="rutFinancialAll" placeholder="12345678">\n                <button onclick="getFinancialAll(this)"><span>&#8594;</span> Obtener Todo Financiero</button>\n            </div>\n            <div class="result-box" id="boxFinancialAll">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusFinancialAll"></span></div>\n                <div class="result-body"><pre id="resultFinancialAll"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <!-- NUEVOS ENDPOINTS DE BIBLIOTECA -->\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/library/list_files</span>\n        </div>\n        <div class="card-body">\n            <button onclick="listFiles(this)"><span>&#8594;</span> Listar Todos los Archivos</button>\n            <div class="result-box" id="boxListFiles">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusListFiles"></span></div>\n                <div class="result-body"><pre id="resultListFiles"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/library/get_file_id/{file_name}</span>\n        </div>\n        <div class="card-body">\n            <label for="fileNameGetId">Nombre del Archivo</label>\n            <div class="input-row">\n                <input type="text" id="fileNameGetId" placeholder="Mi Documento Importante">\n                <button onclick="getFileId(this)"><span>&#8594;</span> Obtener ID del Archivo</button>\n            </div>\n            <div class="result-box" id="boxGetFileId">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusGetFileId"></span></div>\n                <div class="result-body"><pre id="resultGetFileId"></pre></div>\n            </div>\n        </div>\n    </div>\n\n    <div class="card">\n        <div class="card-header">\n            <span class="method-badge">GET</span>\n            <span class="endpoint-path">/library/search_files/{search_key}</span>\n        </div>\n        <div class="card-body">\n            <label for="searchKeyFiles">Palabra clave de B&uacute;squeda</label>\n            <div class="input-row">\n                <input type="text" id="searchKeyFiles" placeholder="Reporte">\n                <button onclick="searchFiles(this)"><span>&#8594;</span> Buscar Archivos</button>\n            </div>\n            <div class="result-box" id="boxSearchFiles">\n                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusSearchFiles"></span></div>\n                <div class="result-body"><pre id="resultSearchFiles"></pre></div>\n            </div>\n        </div>\n    </div>\n\n\n    <footer>FEDRO 128 &middot; API TESTER &middot; RAILWAY PRODUCTION</footer>\n</div>\n<script>\n    const BASE = window.location.origin; // sirve local y Railway\n\n    function syntaxHighlight(json) {\n        if (typeof json !== "string") json = JSON.stringify(json, null, 2);\n        json = json.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");\n\n        return json.replace(\n        /("\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\\s*)?:?|\\b(true|false|null)\\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g,\n        function (match) {\n            let cls = "json-number";\n            if (/^".*"$/.test(match)) cls = /:$/.test(match) ? "json-key" : "json-string";\n            else if (/true|false/.test(match)) cls = "json-bool";\n            else if (/null/.test(match)) cls = "json-null";\n            return \'<span class="\' + cls + \'">\' + match + "</span>";\n        }\n        );\n    }\n\n    async function callApi(path, inputId, boxId, preId, statusId, btn, label) {\n        const val = inputId ? document.getElementById(inputId).value.trim() : "";\n        if (inputId && !val) { alert("Ingresa un valor primero."); return; }\n\n        const box = document.getElementById(boxId);\n        const pre = document.getElementById(preId);\n        const statusEl = document.getElementById(statusId);\n\n        btn.classList.add("loading");\n        btn.innerHTML = \'<span class="spinner"></span> Cargando...\';\n\n        box.classList.add("visible");\n        pre.innerHTML = \'<span style="color:var(--muted)">Esperando respuesta...</span>\';\n        statusEl.textContent = "";\n        statusEl.className = "status-code";\n\n        try {\n            const url = BASE + (inputId ? path.replace("{p}", encodeURIComponent(val)) : path);\n            const res = await fetch(url, { cache: "no-store" });\n\n            // Si el backend devuelve HTML por error, esto te lo mostrará en vez de reventar.\n            const ct = res.headers.get("content-type") || "";\n            const data = ct.includes("application/json") ? await res.json() : await res.text();\n\n            statusEl.textContent = res.status;\n            statusEl.classList.add(res.ok ? "ok" : "error");\n\n            pre.innerHTML = typeof data === "string"\n                ? data.replace(/</g, "&lt;")\n                : syntaxHighlight(JSON.stringify(data, null, 2));\n        } catch (err) {\n            statusEl.textContent = "ERROR";\n            statusEl.classList.add("error");\n            pre.innerHTML = \'<span style="color:var(--accent3)">\' + (err?.message || err) + "</span>";\n        } finally {\n            btn.classList.remove("loading");\n            btn.innerHTML = "<span>&#8594;</span> " + label;\n        }\n    }\n\n    function getPerfil(btn)         { callApi("/auth/perfil/{p}",               "telefonoPerfil",   "boxPerfil",       "resultPerfil",       "statusPerfil",       btn, "Obtener Perfil"); }\n    function getRut(btn)            { callApi("/auth/rut/{p}",                  "telefonoRut",      "boxRut",          "resultRut",          "statusRut",          btn, "Obtener RUT"); }\n    function getClientall(btn)      { callApi("/auth/clientall/{p}",            "rutClientall",     "boxClientall",    "resultClientall",    "statusClientall",    btn, "Obtener Cliente"); }\n    function getMembresiaAnual(btn) { callApi("/financial/membresia_anual/{p}", "rutMembresia",     "boxMembresia",    "resultMembresia",    "statusMembresia",    btn, "Membresía Anual"); }\n    function getDeudaArrastre(btn)  { callApi("/financial/deuda_arrastre/{p}",  "rutDeudaArrastre", "boxDeudaArrastre","resultDeudaArrastre","statusDeudaArrastre",btn, "Deuda de Arrastre"); }\n    function getCuotaAnual(btn)     { callApi("/financial/cuota_anual/{p}",     "rutCuotaAnual",    "boxCuotaAnual",   "resultCuotaAnual",   "statusCuotaAnual",   btn, "Cuota Anual"); }\n    function getPagadoALaFecha(btn) { callApi("/financial/pagado_a_la_fecha/{p}","rutPagadoFecha",  "boxPagadoFecha",  "resultPagadoFecha",  "statusPagadoFecha",  btn, "Pagado a la Fecha"); }\n    function getDeuda(btn)          { callApi("/financial/deuda/{p}",           "rutDeuda",         "boxDeuda",        "resultDeuda",        "statusDeuda",        btn, "Obtener Deuda"); }\n    function getMensaje(btn)        { callApi("/financial/mensaje/{p}",         "rutMensaje",       "boxMensaje",      "resultMensaje",      "statusMensaje",      btn, "Obtener Mensaje"); }\n    function getFinancialAll(btn)   { callApi("/financial/all/{p}",             "rutFinancialAll",  "boxFinancialAll", "resultFinancialAll", "statusFinancialAll", btn, "Obtener Todo Financiero"); }\n\n    function listFiles(btn)         { callApi("/library/list_files",            null,               "boxListFiles",    "resultListFiles",    "statusListFiles",    btn, "Listar Todos los Archivos"); }\n    function getFileId(btn)         { callApi("/library/get_file_id/{p}",       "fileNameGetId",    "boxGetFileId",    "resultGetFileId",    "statusGetFileId",    btn, "Obtener ID del Archivo"); }\n    function searchFiles(btn)       { callApi("/library/search_files/{p}",      "searchKeyFiles",   "boxSearchFiles",  "resultSearchFiles",  "statusSearchFiles",  btn, "Buscar Archivos"); }\n</script>\n</body>\n</html>'


# --- CAPA DE CONFIANZA: IDENTIDAD DE DATOS (CUENTA FEDRO) ---
def get_sheets_client():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("Error: GOOGLE_CREDS_JSON no configurada en Railway.")
    info_json = json.loads(creds_json)
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive' # Keep drive scope for sheets client too if needed
    ]
    creds = service_account.Credentials.from_service_account_info(info_json, scopes=scopes)
    return gspread.authorize(creds)

def get_drive_client(): # New function for Drive API
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("Error: GOOGLE_CREDS_JSON no configurada en Railway.")
    info_json = json.loads(creds_json)
    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    creds = service_account.Credentials.from_service_account_info(info_json, scopes=scopes)
    return build("drive", "v3", credentials=creds)

def _validate_phone_number(telefono: str):
    # Basic validation for international phone numbers (e.g., 7 to 15 digits)
    if not re.fullmatch(r'\d{7,15}', telefono):
        raise HTTPException(status_code=400, detail="Formato de número de teléfono incorrecto. Debe contener solo dígitos y tener entre 7 y 15 dígitos.")

# --- Helper function to get a row by RUT from a specific worksheet ---
def _get_row_by_rut_from_sheet(rut_without_dv: str, sheet_name: str):
    # Validate RUT format before proceeding
    cleaned_input_rut = rut_without_dv.replace(".", "").strip()
    # Ensure RUT part before DV contains only digits and is between 1 and 8 digits long
    if not re.fullmatch(r'\d{1,8}', cleaned_input_rut):
        raise HTTPException(status_code=400, detail="Formato de RUT incorrecto. Debe contener solo dígitos y el número (sin dígito verificador) debe tener entre 1 y 8 cifras.")

    try:
        client = get_sheets_client()
        spreadsheet = client.open("FEDRO128")
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"Advertencia: La hoja de cálculo '{sheet_name}' no fue encontrada.")
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al acceder a la fuente de datos '{sheet_name}': {str(e)}")

    if sheet_name == "Tesoreria":
        print(f"Buscando RUT: {rut_without_dv} en la hoja '{sheet_name}'.")

    rut_column_values = sheet.col_values(1)

    found_row_index = -1
    # The cleaned_input_rut is already prepared for comparison from the validation step

    for i, rut_full_with_dv in enumerate(rut_column_values):
        cleaned_rut_in_sheet = rut_full_with_dv.replace(".", "").split('-')[0].strip()

        if sheet_name == "Tesoreria":
            print(f"  Comparando '{cleaned_input_rut}' con '{cleaned_rut_in_sheet}' de la fila {i+1}.")

        if cleaned_rut_in_sheet == cleaned_input_rut:
            found_row_index = i + 1
            break

    if found_row_index == -1:
        if sheet_name == "Tesoreria":
            print(f"RUT '{rut_without_dv}' no encontrado en la hoja '{sheet_name}'.")
        return None

    row_data = sheet.row_values(found_row_index)
    if sheet_name == "Tesoreria":
        print(f"RUT '{rut_without_dv}' encontrado en la fila {found_row_index} de la hoja '{sheet_name}'.")
    return row_data


# --- ENDPOINT DE SALUD (HEALTH CHECK) ---
@app.get("/")
def health_check():
    return {
        "status": "FEDRO Online",
        "version": VERSION,
        "database": "FEDRO128 / Cuadro",
        "ia_brain": "Configurado" if os.environ.get("GEMINI_API_KEY") else "Faltante"
    }


# --- ENDPOINT TESTER HTML ---
@app.get("/fedro-tester", response_class=HTMLResponse)
def get_tester():
    # Determine environment dynamically
    if "RAILWAY_ENVIRONMENT" in os.environ: # This is a common Railway env var
        api_environment = "RAILWAY - Producción"
        api_base_url = "fedro128-production.up.railway.app" # Replace with your actual Railway URL
    else:
        api_environment = "Local - Uvicorn (Colab)"
        api_base_url = "http://localhost:8000" # For local testing in Colab

    return HTMLResponse(
        content=
TESTER_HTML # Corrected variable name
        .replace('{api_version_placeholder}', VERSION)
        .replace('{api_environment_placeholder}', api_environment)
        .replace('{api_base_url_placeholder}', api_base_url)
    )


# --- ENDPOINT: BÚSQUEDA POR TELÉFONO → PERFIL ---
@app.get("/auth/perfil/{telefono}")
def get_perfil(telefono: str):
    _validate_phone_number(telefono) # Add phone number validation
    try:
        client = get_sheets_client()
        spreadsheet = client.open("FEDRO128")
        sheet = spreadsheet.worksheet("Cuadro")
        cell = sheet.find(telefono)
        if not cell:
            return {"identificado": False, "error": "No matching record found"}
        row = sheet.row_values(cell.row)
        rut_value = row[0]
        nombre_completo_value = f"{row[4]} {row[2]} {row[3]}"
        grado_value = 0
        try:
            grado_value = int(row[8])
        except ValueError:
            print(f"Advertencia: Grado '{row[8]}' no es entero para {telefono}. Usando 0.")
        return {
            "identificado": True,
            "rut": rut_value,
            "nombre_completo": nombre_completo_value,
            "grado": grado_value,
            "status": "Regular",
            "api_version": VERSION
        }
    except Exception as e:
        # Re-raise HTTPException directly if it comes from validation
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")


# --- ENDPOINT: BÚSQUEDA DE RUT Y DV POR TELÉFONO ---
@app.get("/auth/rut/{telefono}")
def get_rut(telefono: str):
    _validate_phone_number(telefono) # Add phone number validation
    try:
        client = get_sheets_client()
        spreadsheet = client.open("FEDRO128")
        sheet = spreadsheet.worksheet("Cuadro")
        cell = sheet.find(telefono)
        if not cell:
            return {"identificado": False, "error": "No matching record found"}
        row = sheet.row_values(cell.row)
        rut_full = row[0]
        dv_value = row[1]
        rut_numeric_str = rut_full.replace(".", "").split("-")[0]
        try:
            rut_numeric = int(rut_numeric_str)
        except ValueError:
            print(f"Advertencia: RUT '{rut_full}' no pudo convertirse a int.")
            rut_numeric = rut_numeric_str
        return {
            "identificado": True,
            "rut": rut_numeric,
            "dv": dv_value,
            "api_version": VERSION
        }
    except Exception as e:
        # Re-raise HTTPException directly if it comes from validation
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")


# --- ENDPOINT: BÚSQUEDA DE DATOS COMPLETOS POR RUT (sin DV) ---
@app.get("/auth/clientall/{rut_without_dv}")
def get_clientall(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Cuadro")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found"}
        return {
            "identificado": True,
            "data": row_data,
            "api_version": VERSION
        }
    except Exception as e:
        # Re-raise HTTPException directly if it comes from validation
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")

# --- ENDPOINT: Obtener Membresía Anual por RUT ---
@app.get("/financial/membresia_anual/{rut_without_dv}")
def get_membresia_anual(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Membresía Anual: Columna E (Índice 4)
        membresia_anual_value = row_data[4] if len(row_data) > 4 else "N/A"
        return {
            "identificado": True,
            "rut": rut_without_dv,
            "membresia_anual": membresia_anual_value,
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Membresia Anual): {str(e)}")

# --- ENDPOINT: Obtener Deuda de Arrastre por RUT ---
@app.get("/financial/deuda_arrastre/{rut_without_dv}")
def get_deuda_arrastre(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Deuda de arrastre 2024: Columna G (Índice 6)
        deuda_arrastre_value = row_data[6] if len(row_data) > 6 else "N/A"
        return {
            "identificado": True,
            "rut": rut_without_dv,
            "deuda_arrastre_2024": deuda_arrastre_value,
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Deuda Arrastre): {str(e)}")

# --- ENDPOINT: Obtener Cuota Anual por RUT ---
@app.get("/financial/cuota_anual/{rut_without_dv}")
def get_cuota_anual(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Cuota anual: Columna I (Índice 8)
        cuota_anual_value = row_data[8] if len(row_data) > 8 else "N/A"
        return {
            "identificado": True,
            "rut": rut_without_dv,
            "cuota_anual": cuota_anual_value,
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Cuota Anual): {str(e)}")

# --- ENDPOINT: Obtener Pagado a la Fecha por RUT ---
@app.get("/financial/pagado_a_la_fecha/{rut_without_dv}")
def get_pagado_a_la_fecha(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Pagado a la fecha: Columna K (Índice 10)
        pagado_a_la_fecha_value = row_data[10] if len(row_data) > 10 else "N/A"
        return {
            "identificado": True,
            "rut": rut_without_dv,
            "pagado_a_la_fecha": pagado_a_la_fecha_value, # Corrected typo
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Pagado a la Fecha): {str(e)}")

# --- ENDPOINT: Obtener Deuda por RUT ---
@app.get("/financial/deuda/{rut_without_dv}")
def get_deuda(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Deuda: Columna S (Índice 18)
        deuda_value = row_data[18] if len(row_data) > 18 else "N/A"
        return {
            "identificado": True,
            "rut": rut_without_dv,
            "deuda": deuda_value,
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")

# --- ENDPOINT: Obtener Mensaje por RUT ---
@app.get("/financial/mensaje/{rut_without_dv}")
def get_mensaje(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Mensaje: Columna T (Índice 19)
        mensaje_value = row_data[19] if len(row_data) > 19 else "N/A"
        return {
            "identificado": True,
            "rut": rut_without_dv,
            "mensaje": mensaje_value,
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")

# --- ENDPOINT: Obtener Todos los Datos Financieros por RUT ----
@app.get("/financial/all/{rut_without_dv}")
def get_financial_all(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        membresia_anual_value    = row_data[4]  if len(row_data) > 4  else "N/A"
        deuda_arrastre_value     = row_data[6]  if len(row_data) > 6  else "N/A"
        cuota_anual_value        = row_data[8]  if len(row_data) > 8  else "N/A"
        pagado_a_la_fecha_value  = row_data[10] if len(row_data) > 10 else "N/A"
        deuda_value              = row_data[18] if len(row_data) > 18 else "N/A"
        mensaje_value            = row_data[19] if len(row_data) > 19 else "N/A"

        return {
            "identificado": True,
            "rut": rut_without_dv,
            "membresia_anual": membresia_anual_value,
            "deuda_arrastre_2024": deuda_arrastre_value,
            "cuota_anual": cuota_anual_value,
            "pagado_a_la_fecha": pagado_a_la_fecha_value,
            "deuda": deuda_value,
            "mensaje": mensaje_value,
            "api_version": VERSION
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Consolidado Financiero): {str(e)}")


def _get_biblioteca_folder_id():
    drive_client = get_drive_client() # Use new drive client
    # Search for a folder named 'BIBLIOTECA'
    query = "name = 'BIBLIOTECA' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_client.files().list(q=query, fields="files(id)", pageSize=1000).execute() # Added pageSize
    items = results.get('files', [])
    if not items:
        raise HTTPException(status_code=404, detail="Folder 'BIBLIOTECA' not found in Google Drive.")
    return items[0]['id']


# --- ENDPOINTS DE BIBLIOTECA ---
@app.get("/library/list_files")
def list_all_drive_files():
    try:
        biblioteca_folder_id = _get_biblioteca_folder_id()
        print(f"BIBLIOTECA folder ID: {biblioteca_folder_id}")
        drive_client = get_drive_client() # Use new drive client
        # List all files within the 'BIBLIOTECA' folder
        query = f"'{biblioteca_folder_id}' in parents and trashed = false"
        results = drive_client.files().list(q=query, fields="files(id, name, size, fileExtension, owners)", pageSize=1000).execute() # Added pageSize
        items = results.get('files', [])

        files_list = []
        if not items:
            return {"status": "success", "message": "No files found in BIBLIOTECA folder.", "files": []}
        else:
            for item in items:
                owner_name = item['owners'][0]['displayName'] if 'owners' in item and item['owners'] else 'Desconocido'
                files_list.append({
                    "id": item['id'],
                    "name": item['name'],
                    "size_bytes": item.get('size'),
                    "extension": item.get('fileExtension'),
                    "owner": owner_name
                })
            return {"status": "success", "total_files": len(files_list), "files": files_list}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar archivos de Drive: {str(e)}")

@app.get("/library/get_file_id/{file_name}")
def get_drive_file_id(file_name: str):
    try:
        biblioteca_folder_id = _get_biblioteca_folder_id()
        drive_client = get_drive_client() # Use new drive client
        # Search for a file with the exact name within the 'BIBLIOTECA' folder
        query = f"name = '{file_name}' and '{biblioteca_folder_id}' in parents and trashed = false"
        results = drive_client.files().list(q=query, fields="files(id, name)", pageSize=1000).execute() # Added pageSize
        items = results.get('files', [])

        if not items:
            return {"status": "not found", "file_name": file_name, "file_id": None, "message": f"File '{file_name}' not found in BIBLIOTECA folder."}
        else:
            # Assuming the first result is the desired one if multiple files have the same name
            file_info = items[0]
            return {"status": "success", "file_name": file_info['name'], "file_id": file_info['id'], "message": "File found."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar ID del archivo en Drive: {str(e)}")

@app.get("/library/search_files/{search_key}")
def search_drive_files_by_name(search_key: str):
    try:
        biblioteca_folder_id = _get_biblioteca_folder_id()
        drive_client = get_drive_client() # Use new drive client
        # Search for files where the name contains the search_key within the 'BIBLIOTECA' folder
        query = f"name contains '{search_key}' and '{biblioteca_folder_id}' in parents and trashed = false"
        results = drive_client.files().list(q=query, fields="files(id, name, size, fileExtension, owners)", pageSize=1000).execute() # Added pageSize
        items = results.get('files', [])

        matching_files = []
        if not items:
            return {"status": "success", "search_key": search_key, "total_matches": 0, "files": [], "message": f"No files matching '{search_key}' found in BIBLIOTECA folder."}
        else:
            for item in items:
                owner_name = item['owners'][0]['displayName'] if 'owners' in item and item['owners'] else 'Desconocido'
                matching_files.append({
                    "id": item['id'],
                    "name": item['name'],
                    "size_bytes": item.get('size'),
                    "extension": item.get('fileExtension'),
                    "owner": owner_name
                })
            return {"status": "success", "search_key": search_key, "total_matches": len(matching_files), "files": matching_files}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar archivos en Drive: {str(e)}")

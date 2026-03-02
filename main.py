import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
import gspread
from fastapi.middleware.cors import CORSMiddleware

# --- METADATA DEL PROYECTO ---
VERSION = "1.1.1-stable"
app = FastAPI(title="FEDRO API", version=VERSION)

# --- Configuración CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HTML TESTER INCRUSTADO ---
TESTER_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FEDRO API Tester</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0c10; --surface: #111318; --surface2: #181c24;
            --border: #1e2430; --accent: #00e5a0; --accent2: #0070f3;
            --accent3: #ff4d6d; --text: #e8eaf0; --muted: #5a6070;
            --mono: 'Space Mono', monospace; --sans: 'Syne', sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }
        body::before {
            content: ''; position: fixed; inset: 0;
            background-image: linear-gradient(rgba(0,229,160,0.03) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(0,229,160,0.03) 1px, transparent 1px);
            background-size: 40px 40px; pointer-events: none; z-index: 0;
        }
        .wrapper { position: relative; z-index: 1; max-width: 860px; margin: 0 auto; padding: 48px 24px 80px; }
        header { margin-bottom: 56px; display: flex; align-items: flex-start; gap: 20px; }
        .logo-badge {
            width: 52px; height: 52px; background: var(--accent); border-radius: 12px;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
            font-family: var(--mono); font-size: 11px; font-weight: 700; color: #000;
            letter-spacing: -0.5px; line-height: 1.1; text-align: center; padding: 6px;
        }
        .header-text h1 { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: var(--text); line-height: 1; margin-bottom: 8px; }
        .header-text h1 span { color: var(--accent); }
        .header-text p { font-family: var(--mono); font-size: 12px; color: var(--muted); }
        .header-text p code { color: var(--accent); background: rgba(0,229,160,0.08); padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .status-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 40px; font-family: var(--mono); font-size: 11px; color: var(--muted); }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 2s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; margin-bottom: 20px; overflow: hidden; transition: border-color 0.2s; }
        .card:hover { border-color: #2a3040; }
        .card-header { padding: 20px 24px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
        .method-badge { font-family: var(--mono); font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: rgba(0,112,243,0.15); color: var(--accent2); border: 1px solid rgba(0,112,243,0.25); letter-spacing: 1px; }
        .endpoint-path { font-family: var(--mono); font-size: 14px; color: var(--text); flex: 1; }
        .endpoint-path .param { color: var(--accent); }
        .card-body { padding: 20px 24px 24px; }
        label { display: block; font-family: var(--mono); font-size: 11px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
        .input-row { display: flex; gap: 10px; align-items: stretch; }
        input[type="text"] { flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px; font-family: var(--mono); font-size: 13px; color: var(--text); outline: none; transition: border-color 0.2s, box-shadow 0.2s; }
        input[type="text"]:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,229,160,0.1); }
        input[type="text"]::placeholder { color: var(--muted); }
        button { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 12px 20px; font-family: var(--sans); font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity 0.15s, transform 0.1s; white-space: nowrap; display: flex; align-items: center; gap: 7px; }
        button:hover { opacity: 0.88; }
        button:active { transform: scale(0.97); }
        button.loading { opacity: 0.6; pointer-events: none; }
        .result-box { margin-top: 16px; border-radius: 10px; overflow: hidden; background: var(--surface2); border: 1px solid var(--border); display: none; }
        .result-box.visible { display: block; }
        .result-header { padding: 8px 14px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); }
        .result-label { font-family: var(--mono); font-size: 10px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }
        .status-code { font-family: var(--mono); font-size: 11px; padding: 2px 8px; border-radius: 5px; }
        .status-code.ok { background: rgba(0,229,160,0.12); color: var(--accent); }
        .status-code.error { background: rgba(255,77,109,0.12); color: var(--accent3); }
        .result-body { padding: 14px; max-height: 300px; overflow-y: auto; }
        pre { font-family: var(--mono); font-size: 12px; line-height: 1.7; color: #a8b4c8; white-space: pre-wrap; word-break: break-all; }
        pre .json-key { color: #7ec8e3; }
        pre .json-string { color: #a8e6b0; }
        pre .json-number { color: #ffd580; }
        pre .json-bool { color: #ff8c69; }
        pre .json-null { color: var(--muted); }
        .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.2); border-top-color: #000; border-radius: 50%; animation: spin 0.6s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        footer { margin-top: 60px; text-align: center; font-family: var(--mono); font-size: 11px; color: var(--muted); }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    </style>
</head>
<body>
<div class="wrapper">
    <header>
        <div class="logo-badge">FE<br>DRO</div>
        <div class="header-text">
            <h1>FEDRO <span>API</span> Tester</h1>
            <p>Conectado a <code>fedro128-production.up.railway.app</code></p>
        </div>
    </header>
    <div class="status-bar">
        <div class="status-dot"></div>
        RAILWAY &middot; PRODUCCI&Oacute;N &middot; REST API
    </div>

    <div class="card">
        <div class="card-header">
            <span class="method-badge">GET</span>
            <span class="endpoint-path">/auth/perfil/<span class="param">{telefono}</span></span>
        </div>
        <div class="card-body">
            <label for="telefonoPerfil">Tel&eacute;fono &mdash; formato internacional</label>
            <div class="input-row">
                <input type="text" id="telefonoPerfil" placeholder="+56912345678">
                <button onclick="getPerfil(this)"><span>&#8594;</span> Obtener Perfil</button>
            </div>
            <div class="result-box" id="boxPerfil">
                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusPerfil"></span></div>
                <div class="result-body"><pre id="resultPerfil"></pre></div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="method-badge">GET</span>
            <span class="endpoint-path">/auth/rut/<span class="param">{telefono}</span></span>
        </div>
        <div class="card-body">
            <label for="telefonoRut">Tel&eacute;fono &mdash; formato internacional</label>
            <div class="input-row">
                <input type="text" id="telefonoRut" placeholder="+56912345678">
                <button onclick="getRut(this)"><span>&#8594;</span> Obtener RUT</button>
            </div>
            <div class="result-box" id="boxRut">
                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusRut"></span></div>
                <div class="result-body"><pre id="resultRut"></pre></div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="method-badge">GET</span>
            <span class="endpoint-path">/auth/clientall/<span class="param">{rut_without_dv}</span></span>
        </div>
        <div class="card-body">
            <label for="rutClientall">RUT &mdash; sin d&iacute;gito verificador, sin puntos</label>
            <div class="input-row">
                <input type="text" id="rutClientall" placeholder="12345678">
                <button onclick="getClientall(this)"><span>&#8594;</span> Obtener Cliente</button>
            </div>
            <div class="result-box" id="boxClientall">
                <div class="result-header"><span class="result-label">Response</span><span class="status-code" id="statusClientall"></span></div>
                <div class="result-body"><pre id="resultClientall"></pre></div>
            </div>
        </div>
    </div>

    <footer>FEDRO 128 &middot; API TESTER &middot; RAILWAY PRODUCTION</footer>
</div>
<script>
    const BASE = '';

    function syntaxHighlight(json) {
        if (typeof json !== 'string') json = JSON.stringify(json, null, 2);
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\\s*:)?|\\b(true|false|null)\\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g, function(match) {
            let cls = 'json-number';
            if (/^"/.test(match)) cls = /:$/.test(match) ? 'json-key' : 'json-string';
            else if (/true|false/.test(match)) cls = 'json-bool';
            else if (/null/.test(match)) cls = 'json-null';
            return '<span class="' + cls + '">' + match + '</span>';
        });
    }

    async function callApi(path, inputId, boxId, preId, statusId, btn, label) {
        const val = document.getElementById(inputId).value.trim();
        if (!val) { alert('Ingresa un valor primero.'); return; }
        const box = document.getElementById(boxId);
        const pre = document.getElementById(preId);
        const statusEl = document.getElementById(statusId);
        btn.classList.add('loading');
        btn.innerHTML = '<span class="spinner"></span> Cargando...';
        box.classList.add('visible');
        pre.innerHTML = '<span style="color:var(--muted)">Esperando respuesta...</span>';
        statusEl.textContent = '';
        statusEl.className = 'status-code';
        try {
            const url = BASE + path.replace('{p}', encodeURIComponent(val));
            const res = await fetch(url);
            const data = await res.json();
            statusEl.textContent = res.status;
            statusEl.classList.add(res.ok ? 'ok' : 'error');
            pre.innerHTML = syntaxHighlight(JSON.stringify(data, null, 2));
        } catch (err) {
            statusEl.textContent = 'ERROR';
            statusEl.classList.add('error');
            pre.innerHTML = '<span style="color:var(--accent3)">' + err.message + '</span>';
        } finally {
            btn.classList.remove('loading');
            btn.innerHTML = '<span>&#8594;</span> ' + label;
        }
    }

    function getPerfil(btn)    { callApi('/auth/perfil/{p}',   'telefonoPerfil', 'boxPerfil',   'resultPerfil',   'statusPerfil',   btn, 'Obtener Perfil'); }
    function getRut(btn)       { callApi('/auth/rut/{p}',      'telefonoRut',    'boxRut',      'resultRut',      'statusRut',      btn, 'Obtener RUT'); }
    function getClientall(btn) { callApi('/auth/clientall/{p}','rutClientall',   'boxClientall','resultClientall','statusClientall',btn, 'Obtener Cliente'); }
</script>
</body>
</html>"""


# --- CAPA DE CONFIANZA: IDENTIDAD DE DATOS (CUENTA FEDRO) ---
def get_sheets_client():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("Error: GOOGLE_CREDS_JSON no configurada en Railway.")
    info_json = json.loads(creds_json)
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = service_account.Credentials.from_service_account_info(info_json, scopes=scopes)
    return gspread.authorize(creds)


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
@app.get("/tester", response_class=HTMLResponse)
def get_tester():
    return HTMLResponse(content=TESTER_HTML)


# --- ENDPOINT: BÚSQUEDA POR TELÉFONO → PERFIL ---
@app.get("/auth/perfil/{telefono}")
def get_perfil(telefono: str):
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
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")


# --- ENDPOINT: BÚSQUEDA DE RUT Y DV POR TELÉFONO ---
@app.get("/auth/rut/{telefono}")
def get_rut(telefono: str):
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
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")


# --- ENDPOINT: BÚSQUEDA DE DATOS COMPLETOS POR RUT (sin DV) ---
@app.get("/auth/clientall/{rut_without_dv}")
def get_clientall(rut_without_dv: str):
    try:
        client = get_sheets_client()
        spreadsheet = client.open("FEDRO128")
        sheet = spreadsheet.worksheet("Cuadro")
        rut_column_values = sheet.col_values(1)
        found_row_index = -1
        for i, rut_full_with_dv in enumerate(rut_column_values):
            cleaned_rut_in_sheet = rut_full_with_dv.replace(".", "").split('-')[0]
            cleaned_input_rut = rut_without_dv.replace(".", "").split('-')[0]
            if cleaned_rut_in_sheet == cleaned_input_rut:
                found_row_index = i + 1
                break
        if found_row_index == -1:
            return {"identificado": False, "error": "No matching record found"}
        row_data = sheet.row_values(found_row_index)
        return {
            "identificado": True,
            "data": row_data,
            "api_version": VERSION
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")

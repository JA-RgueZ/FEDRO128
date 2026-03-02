import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
import gspread
from fastapi.middleware.cors import CORSMiddleware

# --- METADATA DEL PROYECTO ---
VERSION = "1.1.10-stable" # Versión actualizada
app = FastAPI(title="FEDRO API", version=VERSION)

# --- Configuración CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HTML TESTER INCRUSTADO ---
TESTER_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FEDRO API Tester</title>
</head>
<body>
    <h1>FEDRO API Tester</h1>
    <p>API Version: v{api_version_placeholder}</p>
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

# --- Helper function to get a row by RUT from a specific worksheet ---
def _get_row_by_rut_from_sheet(rut_without_dv: str, sheet_name: str):
    try:
        client = get_sheets_client()
        spreadsheet = client.open("FEDRO128")
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Si la hoja no se encuentra, retornamos None para que el endpoint pueda manejarlo específicamente
        print(f"Advertencia: La hoja de cálculo '{sheet_name}' no fue encontrada.")
        return None
    except Exception as e:
        # Captura otros errores de gspread o autenticación y los eleva como HTTPException más descriptivo
        raise HTTPException(status_code=500, detail=f"Error al acceder a la fuente de datos '{sheet_name}': {str(e)}")

    if sheet_name == "Tesoreria":
        print(f"Buscando RUT: {rut_without_dv} en la hoja '{sheet_name}'.") # Debugging line

    # Assuming RUT is always the first column (col_values(1))
    rut_column_values = sheet.col_values(1)

    found_row_index = -1
    cleaned_input_rut = rut_without_dv.replace(".", "").split('-')[0].strip() # Ensure input is clean

    for i, rut_full_with_dv in enumerate(rut_column_values):
        # Clean and compare RUTs
        cleaned_rut_in_sheet = rut_full_with_dv.replace(".", "").split('-')[0].strip()

        if sheet_name == "Tesoreria":
            print(f"  Comparando '{cleaned_input_rut}' con '{cleaned_rut_in_sheet}' de la fila {i+1}.") # Debugging line

        if cleaned_rut_in_sheet == cleaned_input_rut:
            found_row_index = i + 1  # gspread rows are 1-indexed
            break

    if found_row_index == -1:
        if sheet_name == "Tesoreria":
            print(f"RUT '{rut_without_dv}' no encontrado en la hoja '{sheet_name}'.") # Debugging line
        return None  # No matching record found

    if sheet_name == "Tesoreria":
        print(f"RUT '{rut_without_dv}' encontrado en la fila {found_row_index} de la hoja '{sheet_name}'.") # Debugging line
    row_data = sheet.row_values(found_row_index)
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
    return HTMLResponse(content=TESTER_HTML.replace('{api_version_placeholder}', VERSION))


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
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Cuadro")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found"}
        return {
            "identificado": True,
            "data": row_data,
            "api_version": VERSION
        }
    except Exception as e:
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
            "pagado_a_la_fecha": pagado_a_la_fecha_value,
            "api_version": VERSION
        }
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Deuda): {str(e)}")

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
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Mensaje): {str(e)}")

# --- ENDPOINT: Obtener Todos los Datos Financieros por RUT ---
@app.get("/financial/all/{rut_without_dv}")
def get_financial_all(rut_without_dv: str):
    try:
        row_data = _get_row_by_rut_from_sheet(rut_without_dv, "Tesoreria")
        if row_data is None:
            return {"identificado": False, "error": "No matching record found in Tesoreria"}

        # Extraer todos los valores según los índices proporcionados
        membresia_anual_value = row_data[4] if len(row_data) > 4 else "N/A"     # Columna E (Índice 4)
        deuda_arrastre_value = row_data[6] if len(row_data) > 6 else "N/A"    # Columna G (Índice 6)
        cuota_anual_value = row_data[8] if len(row_data) > 8 else "N/A"       # Columna I (Índice 8)
        pagado_a_la_fecha_value = row_data[10] if len(row_data) > 10 else "N/A" # Columna K (Índice 10)
        deuda_value = row_data[18] if len(row_data) > 18 else "N/A"           # Columna S (Índice 18)
        mensaje_value = row_data[19] if len(row_data) > 19 else "N/A"         # Columna T (Índice 19)

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
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API (Consolidado Financiero): {str(e)}")

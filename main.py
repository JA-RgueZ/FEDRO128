import os
import json
from fastapi import FastAPI, HTTPException
from google.oauth2 import service_account
import gspread

# --- METADATA DEL PROYECTO ---
# Usamos VERSION para trazabilidad en los logs de Railway
VERSION = "1.0.5-stable"
app = FastAPI(title="FEDRO API", version=VERSION)

# --- CAPA DE CONFIANZA: IDENTIDAD DE DATOS (CUENTA FEDRO) ---
def get_sheets_client():
    # Recupera el JSON de la Service Account desde las variables de entorno
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("Error: GOOGLE_CREDS_JSON no configurada en Railway.")

    info_json = json.loads(creds_json)

    # Definición de Scopes para evitar el error 403
    # Esto permite que la Service Account "entre" a Sheets y Drive
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    creds = service_account.Credentials.from_service_account_info(
        info_json,
        scopes=scopes
    )
    return gspread.authorize(creds)

# --- ENDPOINT DE SALUD (HEALTH CHECK) ---
@app.get("/")
def health_check():
    # Verifica que las llaves maestras estén cargadas en el entorno
    return {
        "status": "FEDRO Online",
        "version": VERSION,
        "database": "FEDRO128 / Cuadro",
        "ia_brain": "Configurado" if os.environ.get("GEMINI_API_KEY") else "Faltante"
    }

# --- ENDPOINT DE IDENTIDAD: BÚSQUEDA POR TELÉFONO (ETAPA 2) ---
# Este endpoint vincula el WhatsApp entrante con el RUT y Grado del QH
@app.get("/auth/perfil/{telefono}")
def get_perfil(telefono: str):
    try:
        client = get_sheets_client()

        # 1. Abre el archivo principal definido en el plan (FEDRO128)
        spreadsheet = client.open("FEDRO128")

        # 2. Selecciona la pestaña específica de la base de miembros
        sheet = spreadsheet.worksheet("Cuadro")

        # 3. Busca el teléfono en la hoja para identificar al QH
        cell = sheet.find(telefono)

        if not cell:
            return {"identificado": False, "error": "QH no encontrado"}

        # 4. Extrae los datos (usando la nueva información de columnas)
        # Columnas: RUT, DV, Apellido Paterno, Apellido Materno, Nombres, Nombre simple, Fnac, edad, Grado, Tipo Miembro, Celular, Email
        row = sheet.row_values(cell.row)

        rut_value = row[0] # RUT
        # Combinar Nombres (índice 4), Apellido Paterno (índice 2), Apellido Materno (índice 3)
        nombre_completo_value = f"{row[4]} {row[2]} {row[3]}"
        
        grado_value = 0 # Default value if conversion fails
        try:
            # 'Grado' está en el índice 8 según la lista de columnas proporcionada
            grado_value = int(row[8])
        except ValueError:
            # If conversion fails, print a warning and use the default value
            print(f"Advertencia: El valor de Grado '{row[8]}' no es un entero para el teléfono {telefono}. Usando 0 como predeterminado.")

        # Retorna el Perfil/Oficio para determinar comandos autorizados en n8n
        return {
            "identificado": True,
            "rut": rut_value,
            "nombre_completo": nombre_completo_value,
            "grado": grado_value,
            "status": "Regular",
            "api_version": VERSION
        }

    except Exception as e:
        # Captura errores de permisos (403) o conexión para debug en logs
        raise HTTPException(status_code=500, detail=f"Error en FEDRO-API: {str(e)}")

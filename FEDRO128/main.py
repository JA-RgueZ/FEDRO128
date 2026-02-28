import os
import re
import gspread
from fastapi import FastAPI, HTTPException
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Configuración de Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
# En Railway, pegaremos el contenido del JSON de la Service Account en una variable
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

def get_sheet_client():
    creds = Credentials.from_service_account_info(eval(GOOGLE_CREDS_JSON), scopes=SCOPE)
    return gspread.authorize(creds)

def sanitize_id(raw_id: str) -> str:
    """Normaliza RUT: '9.123.456-K' -> '9123456K'"""
    if not raw_id: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(raw_id)).upper()

@app.get("/people/search")
async def get_people(phone: str):
    try:
        client = get_sheet_client()
        # Nombre del archivo que compartiste: FEDRO128
        sheet = client.open("FEDRO128").worksheet("Cuadro")
        records = sheet.get_all_records()
        
        search_phone = re.sub(r'\D', '', phone)
        
        # Búsqueda de QH por celular (Columna K)
        for row in records:
            if re.sub(r'\D', '', str(row['Celular'])) == search_phone:
                return {
                    "person_id": sanitize_id(row['RUT']),
                    "display_name": str(row['Nombre Simple']).strip(),
                    "rank": int(row['Grado']),
                    "email_address": str(row['Email']).lower().strip(),
                    "contact_phone": search_phone,
                    "status": "active"
                }
        
        raise HTTPException(status_code=404, detail="QH no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

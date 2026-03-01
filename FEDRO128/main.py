import os
import json
from fastapi import FastAPI, HTTPException
import google.generativeai as genai
from google.oauth2 import service_account
import gspread

app = FastAPI(title="FEDRO API v1.0")

# --- CAPA DE CONFIANZA ---
def get_infra():
    # 1. Configurar IA (Cuenta Personal)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    
    # 2. Configurar Datos (Cuenta FEDRO)
    creds_raw = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_raw:
        return None, None
    
    info_json = json.loads(creds_raw)
    creds = service_account.Credentials.from_service_account_info(
        info_json, 
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    client = gspread.authorize(creds)
    return genai, client

@app.get("/")
def health_check():
    ai, data = get_infra()
    return {
        "status": "FEDRO Online",
        "ia_connected": ai is not None,
        "data_connected": data is not None
    }

# Endpoint de Identidad (Fase 2, Punto 2)
@app.get("/auth/perfil/{telefono}")
def get_perfil(telefono: str):
    _, gc = get_infra()
    if not gc:
        raise HTTPException(status_code=500, detail="Credenciales de datos no configuradas")
    
    # Aquí irá la lógica para buscar en Google Sheets
    # Por ahora devolvemos un esquema de prueba (Mock)
    return {
        "identificado": True,
        "telefono": telefono,
        "rol": "Buscando en Sheets...",
        "mensaje": "V1.0 MVP activa"
    }

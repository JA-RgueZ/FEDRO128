{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": [],
      "authorship_tag": "ABX9TyMZwtCKuxibmoULSh2nwfBR",
      "include_colab_link": true
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "view-in-github",
        "colab_type": "text"
      },
      "source": [
        "<a href=\"https://colab.research.google.com/github/JA-RgueZ/FEDRO128/blob/main/main.py\" target=\"_parent\"><img src=\"https://colab.research.google.com/assets/colab-badge.svg\" alt=\"Open In Colab\"/></a>"
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "import os\n",
        "import json\n",
        "from fastapi import FastAPI, HTTPException\n",
        "from google.oauth2 import service_account\n",
        "import gspread\n",
        "\n",
        "# --- METADATA DEL PROYECTO ---\n",
        "VERSION = \"1.0.2-auth-fixed\"\n",
        "app = FastAPI(title=\"FEDRO API\", version=VERSION)\n",
        "\n",
        "# --- CONFIGURACIÓN DE IDENTIDAD DE DATOS (CUENTA FEDRO) ---\n",
        "def get_sheets_client():\n",
        "    creds_json = os.environ.get(\"GOOGLE_CREDS_JSON\")\n",
        "    if not creds_json:\n",
        "        print(\"ERROR: Variable GOOGLE_CREDS_JSON no configurada en Railway\")\n",
        "        raise ValueError(\"GOOGLE_CREDS_JSON no configurada\")\n",
        "\n",
        "    info_json = json.loads(creds_json)\n",
        "\n",
        "    # Scopes obligatorios para evitar el error 403\n",
        "    scopes = [\n",
        "        'https://www.googleapis.com/auth/spreadsheets',\n",
        "        'https://www.googleapis.com/auth/drive'\n",
        "    ]\n",
        "\n",
        "    creds = service_account.Credentials.from_service_account_info(\n",
        "        info_json,\n",
        "        scopes=scopes\n",
        "    )\n",
        "    return gspread.authorize(creds)\n",
        "\n",
        "# --- ENDPOINT DE SALUD Y VERIFICACIÓN ---\n",
        "@app.get(\"/\")\n",
        "def health_check():\n",
        "    return {\n",
        "        \"status\": \"FEDRO Online\",\n",
        "        \"version\": VERSION,\n",
        "        \"ia_brain\": \"Configurado\" if os.environ.get(\"GEMINI_API_KEY\") else \"Faltante\"\n",
        "    }\n",
        "\n",
        "# --- ENDPOINT DE BÚSQUEDA DE MIEMBROS (ETAPA 2) ---\n",
        "@app.get(\"/auth/perfil/{telefono}\")\n",
        "def get_perfil(telefono: str):\n",
        "    try:\n",
        "        print(f\"Iniciando búsqueda para: {telefono}\")\n",
        "        client = get_sheets_client()\n",
        "\n",
        "        # 1. Abre el archivo por el nombre definido en el plan\n",
        "        spreadsheet = client.open(\"FEDRO128\")\n",
        "\n",
        "        # 2. Selecciona la pestaña \"Cuadro\"\n",
        "        sheet = spreadsheet.worksheet(\"Cuadro\")\n",
        "\n",
        "        # 3. Busca el teléfono en la hoja\n",
        "        cell = sheet.find(telefono)\n",
        "\n",
        "        if not cell:\n",
        "            print(f\"Búsqueda finalizada: Teléfono {telefono} no encontrado.\")\n",
        "            return {\"identificado\": False, \"error\": \"QH no encontrado\"}\n",
        "\n",
        "        # 4. Extraer datos (A=RUT, B=Nombre, C=Celular, D=Grado)\n",
        "        row = sheet.row_values(cell.row)\n",
        "\n",
        "        print(f\"QH Identificado: {row[1]}\")\n",
        "\n",
        "        return {\n",
        "            \"identificado\": True,\n",
        "            \"rut\": row[0],\n",
        "            \"nombre_completo\": row[1],\n",
        "            \"grado\": int(row[3]),\n",
        "            \"status\": \"Regular\",\n",
        "            \"api_version\": VERSION\n",
        "        }\n",
        "\n",
        "    except Exception as e:\n",
        "        print(f\"ERROR CRÍTICO: {str(e)}\")\n",
        "        raise HTTPException(status_code=500, detail=f\"Error: {str(e)}\")"
      ],
      "metadata": {
        "id": "gruxyNDgJj5F"
      },
      "execution_count": null,
      "outputs": []
    }
  ]
}
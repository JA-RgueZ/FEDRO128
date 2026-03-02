{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": [],
      "authorship_tag": "ABX9TyOSH7P6MSQYmniZqywncAXo",
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
        "<a href=\"https://colab.research.google.com/github/JA-RgueZ/FEDRO128/blob/main/.py\" target=\"_parent\"><img src=\"https://colab.research.google.com/assets/colab-badge.svg\" alt=\"Open In Colab\"/></a>"
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
        "VERSION = \"1.0.3-stable\"\n",
        "app = FastAPI(title=\"FEDRO API\", version=VERSION)\n",
        "\n",
        "# --- CAPA DE CONFIANZA: IDENTIDAD DE DATOS (CUENTA FEDRO) ---\n",
        "def get_sheets_client():\n",
        "    # Recupera el JSON de la Service Account desde las variables de entorno\n",
        "    creds_json = os.environ.get(\"GOOGLE_CREDS_JSON\")\n",
        "    if not creds_json:\n",
        "        raise ValueError(\"Error: GOOGLE_CREDS_JSON no configurada en Railway.\")\n",
        "\n",
        "    info_json = json.loads(creds_json)\n",
        "\n",
        "    # Definición de Scopes para evitar el error 403\n",
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
        "# --- ENDPOINT DE SALUD (HEALTH CHECK) ---\n",
        "@app.get(\"/\")\n",
        "def health_check():\n",
        "    # Verifica que las llaves maestras estén cargadas\n",
        "    return {\n",
        "        \"status\": \"FEDRO Online\",\n",
        "        \"version\": VERSION,\n",
        "        \"database\": \"FEDRO128 / Cuadro\",\n",
        "        \"ia_brain\": \"Configurado\" if os.environ.get(\"GEMINI_API_KEY\") else \"Faltante\"\n",
        "    }\n",
        "\n",
        "# --- ENDPOINT DE IDENTIDAD: BÚSQUEDA POR TELÉFONO (ETAPA 2) ---\n",
        "# Este endpoint vincula el WhatsApp entrante con el RUT y Grado\n",
        "@app.get(\"/auth/perfil/{telefono}\")\n",
        "def get_perfil(telefono: str):\n",
        "    try:\n",
        "        client = get_sheets_client()\n",
        "\n",
        "        # 1. Abre el archivo principal definido en el plan\n",
        "        spreadsheet = client.open(\"FEDRO128\")\n",
        "\n",
        "        # 2. Selecciona la pestaña específica \"Cuadro\"\n",
        "        sheet = spreadsheet.worksheet(\"Cuadro\")\n",
        "\n",
        "        # 3. Busca el teléfono en la hoja para identificar al QH\n",
        "        cell = sheet.find(telefono)\n",
        "\n",
        "        if not cell:\n",
        "            return {\"identificado\": False, \"error\": \"QH no encontrado\"}\n",
        "\n",
        "        # 4. Extrae los datos (A=RUT, B=Nombre, C=Celular, D=Grado)\n",
        "        row = sheet.row_values(cell.row)\n",
        "\n",
        "        # Retorna el Perfil para determinar comandos autorizados\n",
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
        "        # Captura errores de permisos o conexión\n",
        "        raise HTTPException(status_code=500, detail=f\"Error en FEDRO-API: {str(e)}\")"
      ],
      "metadata": {
        "id": "XiKWyZwhMGhv"
      },
      "execution_count": null,
      "outputs": []
    }
  ]
}
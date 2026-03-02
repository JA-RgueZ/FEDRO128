{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": [],
      "authorship_tag": "ABX9TyN6NH6Bw114V5IEGP+91/UV",
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
        "# Usamos VERSION para trazabilidad en los logs de Railway\n",
        "VERSION = \"1.0.5-stable\"\n",
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
        "    # Esto permite que la Service Account \"entre\" a Sheets y Drive\n",
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
        "    # Verifica que las llaves maestras estén cargadas en el entorno\n",
        "    return {\n",
        "        \"status\": \"FEDRO Online\",\n",
        "        \"version\": VERSION,\n",
        "        \"database\": \"FEDRO128 / Cuadro\",\n",
        "        \"ia_brain\": \"Configurado\" if os.environ.get(\"GEMINI_API_KEY\") else \"Faltante\"\n",
        "    }\n",
        "\n",
        "# --- ENDPOINT DE IDENTIDAD: BÚSQUEDA POR TELÉFONO (ETAPA 2) ---\n",
        "# Este endpoint vincula el WhatsApp entrante con el RUT y Grado del QH\n",
        "@app.get(\"/auth/perfil/{telefono}\")\n",
        "def get_perfil(telefono: str):\n",
        "    try:\n",
        "        client = get_sheets_client()\n",
        "\n",
        "        # 1. Abre el archivo principal definido en el plan (FEDRO128)\n",
        "        spreadsheet = client.open(\"FEDRO128\")\n",
        "\n",
        "        # 2. Selecciona la pestaña específica de la base de miembros\n",
        "        sheet = spreadsheet.worksheet(\"Cuadro\")\n",
        "\n",
        "        # 3. Busca el teléfono en la hoja para identificar al QH\n",
        "        cell = sheet.find(telefono)\n",
        "\n",
        "        if not cell:\n",
        "            return {\"identificado\": False, \"error\": \"QH no encontrado\"}\n",
        "\n",
        "        # 4. Extrae los datos (usando la nueva información de columnas)\n",
        "        # Columnas: RUT, DV, Apellido Paterno, Apellido Materno, Nombres, Nombre simple, Fnac, edad, Grado, Tipo Miembro, Celular, Email\n",
        "        row = sheet.row_values(cell.row)\n",
        "\n",
        "        rut_value = row[0] # RUT\n",
        "        # Combinar Nombres (índice 4), Apellido Paterno (índice 2), Apellido Materno (índice 3)\n",
        "        nombre_completo_value = f\"{row[4]} {row[2]} {row[3]}\"\n",
        "\n",
        "        grado_value = 0 # Default value if conversion fails\n",
        "        try:\n",
        "            # 'Grado' está en el índice 8 según la lista de columnas proporcionada\n",
        "            grado_value = int(row[8])\n",
        "        except ValueError:\n",
        "            # If conversion fails, print a warning and use the default value\n",
        "            print(f\"Advertencia: El valor de Grado '{row[8]}' no es un entero para el teléfono {telefono}. Usando 0 como predeterminado.\")\n",
        "\n",
        "        # Retorna el Perfil/Oficio para determinar comandos autorizados en n8n\n",
        "        return {\n",
        "            \"identificado\": True,\n",
        "            \"rut\": rut_value,\n",
        "            \"nombre_completo\": nombre_completo_value,\n",
        "            \"grado\": grado_value,\n",
        "            \"status\": \"Regular\",\n",
        "            \"api_version\": VERSION\n",
        "        }\n",
        "\n",
        "    except Exception as e:\n",
        "        # Captura errores de permisos (403) o conexión para debug en logs\n",
        "        raise HTTPException(status_code=500, detail=f\"Error en FEDRO-API: {str(e)}\")"
      ],
      "metadata": {
        "id": "XiKWyZwhMGhv"
      },
      "execution_count": 3,
      "outputs": []
    },
    {
      "cell_type": "code",
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 383
        },
        "id": "new_cell_2",
        "outputId": "ce7ae59e-5af3-4eeb-d269-ddf30d72c73f"
      },
      "source": [
        "import nest_asyncio\n",
        "import uvicorn\n",
        "from pyngrok import ngrok\n",
        "import os\n",
        "import threading\n",
        "import time\n",
        "\n",
        "# Aplicar nest_asyncio para permitir que uvicorn corra dentro del bucle de eventos de Colab\n",
        "nest_asyncio.apply()\n",
        "\n",
        "# Definir el puerto para la aplicación FastAPI\n",
        "port = 8000\n",
        "\n",
        "# Iniciar el túnel de ngrok\n",
        "try:\n",
        "    # Asegúrate de que `ngrok` esté autenticado si es necesario (para cuentas gratuitas o personalizadas)\n",
        "    # Si no tienes un token de autenticación, ngrok podría limitar tus túneles o no funcionar.\n",
        "    # Puedes obtener uno en ngrok.com y luego ejecutar ngrok.set_auth_token(\"TU_TOKEN_AQUI\")\n",
        "    public_url = ngrok.connect(port)\n",
        "    print(f\"Tu aplicación FastAPI está disponible públicamente en: {public_url}\")\n",
        "except Exception as e:\n",
        "    print(f\"Error al iniciar el túnel ngrok: {e}\")\n",
        "    public_url = None\n",
        "\n",
        "if public_url:\n",
        "    # Función para ejecutar Uvicorn en un hilo separado\n",
        "    def run_uvicorn():\n",
        "        # Pasamos \"__main__:app\" como string para que Uvicorn busque el objeto 'app'\n",
        "        # en el contexto global del cuaderno, que es el módulo '__main__'.\n",
        "        uvicorn.run(\"__main__:app\", host=\"0.0.0.0\", port=port, log_level=\"info\")\n",
        "\n",
        "    # Iniciar Uvicorn en un hilo separado para no bloquear el notebook\n",
        "    thread = threading.Thread(target=run_uvicorn)\n",
        "    thread.start()\n",
        "\n",
        "    print(\"Servidor Uvicorn iniciado en un hilo separado.\")\n",
        "    print(\"Puedes seguir usando el notebook.\")\n",
        "else:\n",
        "    print(\"Servidor Uvicorn no iniciado debido a un error con ngrok.\")"
      ],
      "execution_count": 4,
      "outputs": [
        {
          "output_type": "error",
          "ename": "ModuleNotFoundError",
          "evalue": "No module named 'pyngrok'",
          "traceback": [
            "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
            "\u001b[0;31mModuleNotFoundError\u001b[0m                       Traceback (most recent call last)",
            "\u001b[0;32m/tmp/ipython-input-3036/2038940030.py\u001b[0m in \u001b[0;36m<cell line: 0>\u001b[0;34m()\u001b[0m\n\u001b[1;32m      1\u001b[0m \u001b[0;32mimport\u001b[0m \u001b[0mnest_asyncio\u001b[0m\u001b[0;34m\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[1;32m      2\u001b[0m \u001b[0;32mimport\u001b[0m \u001b[0muvicorn\u001b[0m\u001b[0;34m\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[0;32m----> 3\u001b[0;31m \u001b[0;32mfrom\u001b[0m \u001b[0mpyngrok\u001b[0m \u001b[0;32mimport\u001b[0m \u001b[0mngrok\u001b[0m\u001b[0;34m\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[0m\u001b[1;32m      4\u001b[0m \u001b[0;32mimport\u001b[0m \u001b[0mos\u001b[0m\u001b[0;34m\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[1;32m      5\u001b[0m \u001b[0;32mimport\u001b[0m \u001b[0mthreading\u001b[0m\u001b[0;34m\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n",
            "\u001b[0;31mModuleNotFoundError\u001b[0m: No module named 'pyngrok'",
            "",
            "\u001b[0;31m---------------------------------------------------------------------------\u001b[0;32m\nNOTE: If your import is failing due to a missing package, you can\nmanually install dependencies using either !pip or !apt.\n\nTo view examples of installing some common dependencies, click the\n\"Open Examples\" button below.\n\u001b[0;31m---------------------------------------------------------------------------\u001b[0m\n"
          ],
          "errorDetails": {
            "actions": [
              {
                "action": "open_url",
                "actionText": "Open Examples",
                "url": "/notebooks/snippets/importing_libraries.ipynb"
              }
            ]
          }
        }
      ]
    }
  ]
}
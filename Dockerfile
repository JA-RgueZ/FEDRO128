# Usamos una imagen base ligera
FROM python:3.12-slim

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los archivos de requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Railway asigna un puerto dinámico, lo capturamos
ENV PORT=8080
EXPOSE 8080

# Comando para iniciar la API
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
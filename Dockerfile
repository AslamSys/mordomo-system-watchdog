FROM python:3.12-alpine

WORKDIR /app

# Instala dependências nativas necessárias para o psutil compilar em Alpine
RUN apk add --no-cache gcc musl-dev linux-headers python3-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para iniciar
CMD ["python", "main.py"]

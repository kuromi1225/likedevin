FROM python:3.9

WORKDIR /app

RUN apt-get update && apt-get install -y curl

RUN curl -L -o /usr/local/bin/maverick https://github.com/jasonkneen/maverick/releases/download/v0.0.20/maverick-cli-linux-amd64 && \
    chmod +x /usr/local/bin/maverick

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


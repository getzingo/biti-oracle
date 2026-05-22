FROM python:3.13
LABEL authors="getzi"

WORKDIR /app

COPY api_server_image/api-requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . .

RUN mv /app/utils/api/server/oracle_api.py oracle_api.py

CMD ["fastapi", "run", "oracle_api.py", "--port", "80"]
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir streamlit

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

CMD ["streamlit", "run", "AppV1.3.py", "--server.port=8501", "--server.address=0.0.0.0"]

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY utils/ utils/
COPY app.py .

EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"
CMD ["python3", "app.py"]
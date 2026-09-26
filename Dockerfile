# Backend image (FastAPI). Build: docker build -t legalease .
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000 8501
# Default: backend. For the frontend use:
#   docker run -p 8501:8501 -e BACKEND_URL=http://<backend-host>:8000 legalease \
#     streamlit run frontend/app.py --server.address 0.0.0.0
CMD ["uvicorn", "legalEaseAPI.main:app", "--host", "0.0.0.0", "--port", "8000"]

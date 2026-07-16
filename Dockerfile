FROM python:3.11-slim

WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# The FastAPI server serves the frontend + streams pipeline runs over SSE.
# LLM reasoning is enabled when OPENAI_API_KEY is set in the Dokploy environment;
# otherwise the pipeline runs on its rule-based fallback (never crashes).
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

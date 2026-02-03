FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- CHANGED LINE BELOW ---
# Instead of copying just one file, we copy everything (.) to the workdir (.)
COPY . .
# --------------------------

CMD ["python", "index_files_es.py"]
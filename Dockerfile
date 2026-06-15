FROM python:3.10-slim

WORKDIR /app

# Install git (required to clone and diff repositories)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy code and install package
COPY . .
RUN pip install -e .

# Run the FastAPI server using Uvicorn
CMD ["uvicorn", "n3mo.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
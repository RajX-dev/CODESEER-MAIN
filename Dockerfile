FROM python:3.10-slim

WORKDIR /app

# 1. Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy code and install package
COPY . .
RUN pip install -e .

# Default command (keeps container running if needed)
CMD ["tail", "-f", "/dev/null"]
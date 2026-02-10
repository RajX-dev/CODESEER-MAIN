FROM python:3.10-slim

WORKDIR /app

# 1. Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Create the 'n3mo' command shortcut
# This tells Linux: "When user types 'n3mo', run 'python /app/src/cli.py'"
RUN echo '#!/bin/bash\npython /app/src/cli.py "$@"' > /usr/local/bin/n3mo && \
    chmod +x /usr/local/bin/n3mo

# 3. Set Python path so imports work correctly
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# 4. Copy the rest of the code
COPY . .

# Default command (keeps container running if needed)
CMD ["tail", "-f", "/dev/null"]
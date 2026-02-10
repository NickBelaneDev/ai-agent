FROM python:3.12-slim

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install git to allow pip to install dependencies from git repositories
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create a non-root user with an explicit, high UID.
# We use 10001 to avoid conflicts with the standard host user (usually UID 1000).
RUN useradd -m -u 10001 ai-agent-user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with ownership set to the non-root user
COPY --chown=ai-agent-user:ai-agent-user . .

EXPOSE 8000

USER ai-agent-user
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "120"]
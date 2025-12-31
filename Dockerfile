# Use a slim Python base image for a smaller footprint
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8083

# Run the application using the Uvicorn CLI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8083"]
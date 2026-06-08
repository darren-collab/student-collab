FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose ports
EXPOSE 8000 8001

# Run Daphne (WebSocket server) and Django
CMD ["sh", "-c", "daphne -b 0.0.0.0 -p 8001 CollabSpace.asgi:application & python manage.py runserver 0.0.0.0:8000"]

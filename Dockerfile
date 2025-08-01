# Stage 1: Build stage with build-essentials
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Final production stage
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser

# Copy python dependencies from builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Create database directory and change ownership of the app directory
RUN mkdir -p /app/database
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port and run the application
EXPOSE 5001

# Set the entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app"]
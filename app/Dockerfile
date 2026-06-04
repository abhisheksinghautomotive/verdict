# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Install compilation tools for build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into /install
RUN pip install --no-cache-dir --target=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

# Install tini for PID 1 signal forwarding
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create a hardened non-root user with UID 10001
RUN useradd -u 10001 -m appuser

# Configure python environment variables
ENV PYTHONPATH=/install
ENV PATH=/install/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency packages from builder
COPY --from=builder /install /install

# Copy application files under the app/ package namespace
COPY main.py /app/app/main.py
COPY tests/ /app/app/tests/

# Set proper file permissions for the non-root user
RUN chown -R appuser:appuser /app /install

# Switch to the non-root user
USER 10001

EXPOSE 8080

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

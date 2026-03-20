FROM python:3.14-slim

# lxml needs libxml2 and libxslt at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the Python package (resources are bundled inside the package)
COPY python/ ./python/

# Install the package (production deps only)
RUN pip install --no-cache-dir ./python/

# Pre-create runtime directories so volume mounts work even without user data
RUN mkdir -p config var/export var/logs var/cache

CMD ["xmltvfr", "export"]
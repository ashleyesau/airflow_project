# Use your specified Astro Runtime base image
FROM astrocrpublic.azurecr.io/runtime:3.0-6

# Set working directory inside container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to root user to install system-level dependencies
USER root

# Copy packages.txt and install system-level dependencies if packages.txt is not empty
COPY packages.txt /app/packages.txt
RUN if [ -s /app/packages.txt ]; then \
      apt-get update && \
      xargs -a /app/packages.txt apt-get install -y --no-install-recommends && \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Switch back to the non-root user (usually 'astro') for security
USER astro

# Copy project folders into the image
COPY dags/ /app/dags/
COPY plugins/ /app/plugins/
COPY include/ /app/include/

# Keep dbt folder path consistent with your DAG/Cosmos config.
# If your DAG expects manifest at /app/dbt/target/manifest.json, keep this as is.
COPY dbt/ /app/dbt/

# Copy Airflow configuration file if you want it baked in (optional)
COPY airflow.cfg /app/airflow.cfg

# Entrypoint and CMD are inherited from the base image

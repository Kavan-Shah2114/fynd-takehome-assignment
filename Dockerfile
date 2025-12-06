# Use an official lightweight Python image
FROM python:3.11-slim

# set workdir
WORKDIR /app

# copy requirements first (caches installs)
COPY requirements.txt /app/requirements.txt

# install system deps for packages that might need build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# install python deps
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# copy app code
COPY . /app

# Expose port expected by HF: 7860 or $PORT; we'll use 7860 convention
ENV PORT=7860

# Entry: run streamlit on $PORT binding to 0.0.0.0
CMD ["bash", "-lc", "streamlit run user_dashboards.py --server.port $PORT --server.address 0.0.0.0"]
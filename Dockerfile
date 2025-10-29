FROM debian:stable-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    make \
    gcc \
    g++ \
    python3 \
    python3-pip \
    git \
    ca-certificates \
    iverilog \
    gtkwave \
    yosys \
    verilator \
    libpython3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    numpy \
    pillow \
    cocotb==2.0.0 \
    streamlit \
    opencv-python

# Set working directory
WORKDIR /workspace

# Copy project files
COPY . /workspace

# Expose Streamlit port
EXPOSE 8501

# Default command
CMD ["make", "ui"]

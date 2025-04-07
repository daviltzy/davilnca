# Base image
FROM python:3.9-slim

# Install system dependencies, build tools, and libraries
# (Keep this lengthy block as is - it benefits from caching if base image doesn't change)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget tar xz-utils fonts-liberation fontconfig \
    build-essential yasm cmake meson ninja-build nasm libssl-dev \
    libvpx-dev libx264-dev libx265-dev libnuma-dev libmp3lame-dev \
    libopus-dev libvorbis-dev libtheora-dev libspeex-dev \
    libfreetype6-dev libfontconfig1-dev libgnutls28-dev libaom-dev \
    libdav1d-dev librav1e-dev libsvtav1-dev libzimg-dev libwebp-dev \
    git pkg-config autoconf automake libtool libfribidi-dev libharfbuzz-dev \
    && rm -rf /var/lib/apt/lists/*

# Install SRT, SVT-AV1, libvmaf, fdk-aac, libunibreak, libass, FFmpeg...
# (Keep all these RUN git clone ... make install blocks as is)
# ... [SRT Installation] ...
# ... [SVT-AV1 Installation] ...
# ... [libvmaf Installation] ...
# ... [fdk-aac Installation] ...
# ... [libunibreak Installation] ...
# ... [libass Installation] ...
# ... [FFmpeg Installation] ...

# Add /usr/local/bin to PATH
ENV PATH="/usr/local/bin:${PATH}"

# Set work directory
WORKDIR /app

# Set environment variable for Whisper cache
ENV WHISPER_CACHE_DIR="/app/whisper_cache"

# Create cache directory (owner will be set later)
RUN mkdir -p ${WHISPER_CACHE_DIR}

# === Python Dependencies - Install these BEFORE copying app code/fonts ===
# Copy the requirements file first to optimize caching
COPY requirements.txt ./

# Install Python dependencies, upgrade pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install openai-whisper && \
    pip install jsonschema

# === Fonts - Copy AFTER Python deps, BEFORE app code ===
# Copy fonts into the custom fonts directory
COPY ./fonts /usr/share/fonts/custom

# Rebuild the font cache
RUN fc-cache -f -v

# === Application Code & Final Setup ===
# Copy the rest of the application code
COPY . .

# Create the appuser
RUN useradd -m appuser

# Give appuser ownership of the /app directory (including code and cache dir)
# Do this AFTER copying code and creating the directory
RUN chown -R appuser:appuser /app

# Switch to the appuser
USER appuser

# --- REMOVED: Model download during build ---
# REMOVED: RUN python -c "import os; print(os.environ.get('WHISPER_CACHE_DIR')); import whisper; whisper.load_model('base')"
# ---> Your application should handle model download at runtime <---

# Expose the port the app runs on
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create the run script (ensure correct ownership/permissions if needed, though chown above helps)
# Switch back to root temporarily if needed to create script in /app owned by root? Or just let appuser own it.
# USER root # Optional: Temporarily switch back if needed for permissions, then back to appuser
RUN echo '#!/bin/bash\n\
gunicorn --bind 0.0.0.0:8080 \
    --workers ${GUNICORN_WORKERS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-300} \
    --worker-class sync \
    --keep-alive 80 \
    app:app' > /app/run_gunicorn.sh && \
    chmod +x /app/run_gunicorn.sh
# USER appuser # Switch back if you switched to root

# Run the shell script as appuser
CMD ["/app/run_gunicorn.sh"]

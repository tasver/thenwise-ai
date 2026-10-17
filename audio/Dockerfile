FROM pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 HF_HOME=/workspace/cache
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git libsndfile1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-deps chatterbox-tts==0.1.7 && pip install --no-cache-dir faster-whisper soundfile librosa huggingface_hub paramiko
COPY audio/speech.py /opt/thenwise/speech.py
WORKDIR /workspace
ENTRYPOINT ["python","/opt/thenwise/speech.py"]

FROM pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 HF_HOME=/workspace/cache THENWISE_MODELS=/workspace-global/models
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg curl tini libgl1 libglib2.0-0 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/Comfy-Org/ComfyUI.git /opt/ComfyUI && cd /opt/ComfyUI && git checkout ba994879b88d0ebd9950b1e5c1e923d928f216ba && pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir huggingface_hub paramiko
RUN git clone https://github.com/city96/ComfyUI-GGUF.git /opt/ComfyUI/custom_nodes/ComfyUI-GGUF && git clone https://github.com/kijai/ComfyUI-KJNodes.git /opt/ComfyUI/custom_nodes/comfyui-kjnodes && git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git /opt/ComfyUI/custom_nodes/comfyui-videohelpersuite && git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git /opt/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper
RUN for d in /opt/ComfyUI/custom_nodes/*; do if [ -f "$d/requirements.txt" ]; then pip install --no-cache-dir -r "$d/requirements.txt"; fi; done
COPY scripts /opt/thenwise/scripts
COPY config /opt/thenwise/config
COPY workflows /opt/thenwise/workflows
COPY video/start.sh /opt/thenwise/start.sh
RUN chmod +x /opt/thenwise/start.sh && mkdir -p /workspace/input /workspace/output /workspace/jobs
WORKDIR /opt/ComfyUI
EXPOSE 8188
ENTRYPOINT ["/usr/bin/tini","--","/opt/thenwise/start.sh"]

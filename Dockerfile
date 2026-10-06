FROM python:3.14-slim

# CPU by default; NVIDIA build: --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV PYTHONUTF8=1 PYTHONUNBUFFERED=1
WORKDIR /src
COPY laia /src/laia
COPY LICENSE pyproject.toml MANIFEST.in README.md /src/
RUN python -m pip install --no-cache-dir torch==2.14.1 torchvision==0.29.1 --index-url ${TORCH_INDEX_URL} \
    && python -m pip install --no-cache-dir . \
    && pylaia-htr-create-model --help > /dev/null

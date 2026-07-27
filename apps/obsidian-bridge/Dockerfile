# Debian slim rather than Alpine: pydantic-core and the rest of the FastAPI /
# MCP stack ship manylinux wheels, so this builds without a compiler.
FROM docker.io/library/python:3.14-slim

COPY ./requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY ./src/bridge /app/bridge

# Matches the `node` user (uid 1000) that owns the OpenClaw PVC this runs
# beside: the bridge writes captures and transcripts into the shared vault,
# so a different uid cannot write the volume.
USER 1000
WORKDIR /app
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

CMD ["python", "-m", "bridge.main"]

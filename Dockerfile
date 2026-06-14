# ==============================================
# Stage 1: Build the frontend app (produces app.tgz)
# ==============================================
FROM node:22-alpine AS builder

WORKDIR /build

# Copy workspace-level files first for layer caching
COPY package.json yarn.lock ./
COPY packages/agent-mesh/package.json packages/agent-mesh/
COPY packages/agent-mesh-ui/package.json packages/agent-mesh-ui/

RUN yarn install --frozen-lockfile

# Copy source and build
COPY babel.config.js ./
COPY packages/ packages/

RUN yarn build


# ==============================================
# Stage 2: Splunk + uvicorn runtime
# ==============================================
FROM splunk/splunk:latest

USER root

# Directory layout must satisfy config.py path resolution:
#   Path(__file__).resolve().parents[2]  (from server/agent_mesh/config.py)
#   = /opt/agent-mesh/
RUN mkdir -p /opt/agent-mesh/server \
             /opt/agent-mesh/packages/agent-mesh/src/main/resources/splunk/default

# Copy built app from stage 1
COPY --from=builder /build/target/app.tgz /tmp/app.tgz

# Copy server code
COPY server/requirements.txt /opt/agent-mesh/server/
COPY server/agent_mesh/ /opt/agent-mesh/server/agent_mesh/

# Copy agents.conf to the path FileConfReader expects
COPY packages/agent-mesh/src/main/resources/splunk/default/agents.conf \
     /opt/agent-mesh/packages/agent-mesh/src/main/resources/splunk/default/agents.conf

# Copy Docker support files
COPY docker/entrypoint.sh /opt/agent-mesh/entrypoint.sh
COPY docker/indexes.conf /tmp/indexes.conf
RUN chmod +x /opt/agent-mesh/entrypoint.sh

# Create Python venv and install dependencies (image ships Python 3.13)
RUN python3 -m venv /opt/agent-mesh/.venv \
    && /opt/agent-mesh/.venv/bin/pip install --no-cache-dir \
        -r /opt/agent-mesh/server/requirements.txt

# Environment
ENV SPLUNK_START_ARGS="--accept-license"
ENV SPLUNK_GENERAL_TERMS="--accept-sgt-current-at-splunk-com"
ENV AGENT_MESH_SETTINGS_STORE=dev
ENV AGENT_MESH_DEV_MODE=1
ENV AGENT_MESH_CONF_SOURCE=file

EXPOSE 8000 8089 8765

USER ansible

ENTRYPOINT ["/opt/agent-mesh/entrypoint.sh"]

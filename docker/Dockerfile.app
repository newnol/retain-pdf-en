FROM rust:1.81-slim-bookworm AS builder

ARG TYPST_VERSION=0.14.2
ARG CMARKER_VERSION=0.1.8
ARG MITEX_VERSION=0.2.6

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/rust_api/Cargo.toml backend/rust_api/Cargo.lock backend/rust_api/build.rs ./backend/rust_api/
COPY backend/rust_api/src ./backend/rust_api/src

WORKDIR /build/backend/rust_api
RUN cargo build --release

FROM python:3.11-slim-bookworm AS typstsrc

ARG TYPST_VERSION=0.14.2
ARG CMARKER_VERSION=0.1.8
ARG MITEX_VERSION=0.2.6

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tar \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/typst /opt/typst/bin /opt/typst-packages/preview

RUN set -eux; \
    curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
    -o /tmp/typst/typst.tar.xz \
    && tar -xJf /tmp/typst/typst.tar.xz -C /tmp/typst \
    && cp /tmp/typst/typst-x86_64-unknown-linux-musl/typst /opt/typst/bin/typst

RUN set -eux; \
    for pkg in cmarker:${CMARKER_VERSION} mitex:${MITEX_VERSION}; do \
      name="${pkg%%:*}"; \
      version="${pkg##*:}"; \
      mkdir -p "/tmp/typst/${name}" "/opt/typst-packages/preview/${name}/${version}"; \
      curl -fsSL "https://packages.typst.org/preview/${name}-${version}.tar.gz" \
        -o "/tmp/typst/${name}.tar.gz"; \
      tar -xzf "/tmp/typst/${name}.tar.gz" -C "/tmp/typst/${name}"; \
      cp -R "/tmp/typst/${name}/." "/opt/typst-packages/preview/${name}/${version}/"; \
    done

FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROJECT_ROOT=/app \
    RUST_API_ROOT=/app/backend/rust_api \
    RUST_API_DATA_ROOT=/data \
    OUTPUT_ROOT=/data/jobs \
    PYTHON_BIN=python3 \
    TYPST_BIN=/usr/local/bin/typst \
    TYPST_PACKAGE_PATH=/app/backend/typst-packages \
    RETAIN_PDF_FONT_PATH=/usr/local/share/fonts/source-han-serif/SourceHanSerifSC-Regular.otf \
    RETAIN_PDF_TITLE_BOLD_FONT_PATH=/usr/local/share/fonts/source-han-serif/SourceHanSerifSC-Bold.otf \
    RETAIN_PDF_TYPST_FONT_FAMILY="Source Han Serif SC" \
    RUST_API_PORT=41000 \
    RUST_API_SIMPLE_PORT=42000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    fontconfig \
    fonts-noto-cjk \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=typstsrc /opt/typst/bin/typst /usr/local/bin/typst
COPY --from=typstsrc /opt/typst-packages /app/backend/typst-packages

RUN mkdir -p /usr/local/share/fonts/source-han-serif

COPY backend/fonts/SourceHanSerifSC-Regular.otf /usr/local/share/fonts/source-han-serif/SourceHanSerifSC-Regular.otf
COPY backend/fonts/SourceHanSerifSC-Bold.otf /usr/local/share/fonts/source-han-serif/SourceHanSerifSC-Bold.otf
COPY docker/fontconfig/65-source-han-serif-alias.conf /etc/fonts/conf.d/65-source-han-serif-alias.conf

RUN fc-scan /usr/local/share/fonts/source-han-serif/SourceHanSerifSC-Regular.otf >/dev/null \
    && fc-scan /usr/local/share/fonts/source-han-serif/SourceHanSerifSC-Bold.otf >/dev/null \
    && fc-cache -f

COPY docker/requirements-app.txt /tmp/requirements-app.txt
RUN pip install --no-cache-dir -r /tmp/requirements-app.txt

COPY --from=builder /build/backend/rust_api/target/release/rust_api /usr/local/bin/rust_api
COPY backend/scripts /app/backend/scripts
COPY backend/rust_api/auth.local.example.json /app/backend/rust_api/auth.local.example.json
COPY docker/entrypoint-app.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/backend/rust_api /app/backend/scripts /data/uploads /data/downloads /data/db /data/jobs

VOLUME ["/data"]

EXPOSE 41000 42000

ENTRYPOINT ["/entrypoint.sh"]

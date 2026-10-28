# docsctl-Builder: Quarto (inkl. Pandoc + Typst) + mermaid-cli (Chromium) + docsctl (Engine unter /opt/docsctl)
# Alle Versionen gepinnt. Netz wird nur beim Image-Bau gebraucht; der Build-Lauf
# selbst läuft mit network_mode: none.
FROM mirror.gcr.io/library/node:22.23.4-trixie-slim

ARG QUARTO_VERSION=1.10.19
ARG MMDC_VERSION=12.0.0

ENV DEBIAN_FRONTEND=noninteractive \
    PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl chromium fontconfig fonts-dejavu-core fonts-noto-color-emoji \
      python3 python3-yaml python3-jsonschema poppler-utils make \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/quarto.deb \
      "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.deb" \
 && dpkg -i /tmp/quarto.deb && rm /tmp/quarto.deb \
 && quarto --version

RUN npm install -g "@mermaid-js/mermaid-cli@${MMDC_VERSION}" && npm cache clean --force

# Brand-Schriften werden zur Laufzeit aus /work/brands und /opt/docsctl/brands gelesen (kein Rebuild je Brand).
COPY builder/fonts.conf /etc/fonts/conf.d/99-doku-brands.conf
COPY builder/puppeteer.json /opt/doku/puppeteer.json

# Versionsnachweis ins Image schreiben
RUN { echo "quarto $(quarto --version)"; \
      echo "pandoc $(quarto pandoc --version | head -1)"; \
      echo "typst $(quarto typst --version 2>&1)"; \
      echo "mmdc $(mmdc --version)"; \
      echo "chromium $(chromium --version)"; } > /opt/doku/VERSIONS && cat /opt/doku/VERSIONS

ENV HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    DENO_DIR=/tmp/.cache/deno
# Engine: Regeln, Vorlagen, Portal-Optik, Branding neutral. Für Engine-Entwicklung ./ nach /opt/docsctl mounten.
COPY docsctl /opt/docsctl/docsctl
COPY spec /opt/docsctl/spec
COPY quarto /opt/docsctl/quarto
COPY portal /opt/docsctl/portal
COPY brands /opt/docsctl/brands
COPY SPEC.md /opt/docsctl/SPEC.md
WORKDIR /work
ENTRYPOINT ["python3", "/opt/docsctl/docsctl/docsctl.py"]
CMD ["build"]

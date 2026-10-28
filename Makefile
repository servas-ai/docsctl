# docsctl – Builder-Image und Selbsttest. Alles läuft in Docker.
IMAGE ?= docsctl:2026.10

.PHONY: help image check build

help:
	@echo "make image   Builder-Image $(IMAGE) bauen"
	@echo "make check   eigenes Handbuch (docs/) gegen die Konvention prüfen"
	@echo "make build   eigenes Handbuch bauen -> build/site"

image:
	docker build -t $(IMAGE) .

check:
	bin/docsctl check --path docs

build:
	bin/docsctl build

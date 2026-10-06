#!/bin/sh
set -eu
# Builds locally only. Publishing a private image must be done explicitly.
docker build -f Dockerfile . -t "${PYLAIA_IMAGE_TAG:-pylaia:local}"

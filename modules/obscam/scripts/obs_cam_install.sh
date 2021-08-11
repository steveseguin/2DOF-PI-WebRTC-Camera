#!/bin/bash

echo "[INFO] Insall and build dependencies and gstreamer"

. obs_cam_install.base.sh
. obs_cam_install.deps.sh
. obs_cam_install.gst.core.sh
. obs_cam_install.gst.extra.sh

echo "[INFO] System is ready"
echo "[INFO] To run obs ninja:"
echo "[INFO]   cd ../app"
echo "[INFO]   python3 server.py Your_Stream_ID"
echo ""
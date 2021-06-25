#!/bin/bash

export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0
export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-libav"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-libav/gst-libav-1.18.4.tar.xz
tar -xf gst-libav-1.18.4.tar.xz
# make an installation folder
cd ./gst-libav-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -D buildtype=release -D gst_debug=false -D gtk_doc=disabled -D target=rpi -D header_path=/opt/vc/include/IL/ -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-rtsp-server"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-rtsp-server/gst-rtsp-server-1.18.4.tar.xz
tar -xf gst-rtsp-server-1.18.4.tar.xz
# make an installation folder
cd ./gst-rtsp-server-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -D buildtype=release -D gst_debug=false -D gtk_doc=disabled -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig


cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-omx"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-omx/gst-omx-1.18.4.tar.xz
tar -xf gst-omx-1.18.4.tar.xz
# make an installation folder
cd ./gst-omx-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -D target=rpi -D header_path=/opt/vc/include/IL/ -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -Dexamples=disabled -Dx11=disabled -Dglx=disabled -Dopengl=disabled -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig


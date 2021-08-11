#!/bin/bash

export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0
export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gstreamer"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gstreamer/gstreamer-1.18.4.tar.xz
tar -xf gstreamer-1.18.4.tar.xz
# make an installation folder
cd ./gstreamer-1.18.4
mkdir build
cd ./build
# run meson (a kind of cmake)
meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled --wrap-mode=nofallback -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-plugins-base"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-plugins-base/gst-plugins-base-1.18.4.tar.xz
tar -xf gst-plugins-base-1.18.4.tar.xz
# make an installation folder
cd ./gst-plugins-base-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-plugins-good"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-plugins-good/gst-plugins-good-1.18.4.tar.xz
tar -xf gst-plugins-good-1.18.4.tar.xz
# make an installation folder
cd ./gst-plugins-good-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D target=rpi -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-plugins-ugly"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-plugins-ugly/gst-plugins-ugly-1.18.4.tar.xz
tar -xf gst-plugins-ugly-1.18.4.tar.xz
# make an installation folder
cd ./gst-plugins-ugly-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" ..
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-plugins-bad"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-plugins-bad/gst-plugins-bad-1.18.4.tar.xz
tar -xf gst-plugins-bad-1.18.4.tar.xz
# make an installation folder
cd ./gst-plugins-bad-1.18.4
mkdir build
cd ./build
meson --prefix=/usr -D buildtype=release -D gtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" -D examples=disabled -D x11=disabled -D glx=disabled -D opengl=disabled -D gst-plugins-bad:webrtc=enabled -D gst-plugins-bad:webrtcdsp=enabled -D target=rpi  ..
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-python"
echo "[INFO]"
wget https://gstreamer.freedesktop.org/src/gst-python/gst-python-1.18.4.tar.xz
tar -xf gst-python-1.18.4.tar.xz
cd ./gst-python-1.18.4/
mkdir build
cd ./build
meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled
ninja -j4
sudo ninja install
sudo ldconfig

cd /usr/local/src
echo "[INFO]"
echo "[INFO] Building gst-nice plugin"
echo "[INFO]"
cd ./libnice/build
meson --reconfigure -D buildtype=release -D gst_debug=false
ninja -j4
sudo ninja install
sudo ldconfig

echo "[INFO]"
echo "[INFO] Install python extsions"
echo "[INFO]"
sudo python3 -m pip install websockets

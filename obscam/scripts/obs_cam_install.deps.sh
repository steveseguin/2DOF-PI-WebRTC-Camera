#!/bin/bash
echo "[INFO]"
echo "[INFO] Creating source directory"
echo "[INFO]"
sudo mkdir /usr/local/src
sudo chmod 777 /usr/local/src
cd /usr/local/src

echo "[INFO]"
echo "[INFO] Building libnice"
echo "[INFO]"
git clone https://github.com/libnice/libnice.git
cd libnice/
meson --prefix=/usr -D buildtype=release -D gst_debug=false build 
ninja -C build -j4
sudo ninja -C build install
sudo cp /usr/lib/gstreamer-1.0/* /usr/lib/arm-linux-gnueabihf/gstreamer-1.0/

echo "[INFO]"
echo "[INFO] Building libsrtp"
echo "[INFO]"
cd ..
sudo apt-get install libwebrtc-audio-processing-dev -y
sudo apt-get remove libsrtp-dev -y
git clone https://github.com/cisco/libsrtp/
cd libsrtp
./configure --prefix=/usr --enable-openssl
make -j4
sudo make install -j4
sudo ldconfig

echo "[INFO]"
echo "[INFO] Building usrsctp"
echo "[INFO]"
cd ..
sudo apt-get remove libsctp-dev -y
git clone https://github.com/sctplab/usrsctp
cd usrsctp
./bootstrap
libtoolize
./configure --prefix=/usr
libtoolize
make -j4
sudo make install -j4
sudo ldconfig

echo "[INFO]"
echo "[INFO] ffmpeg libraries"
echo "[INFO]"
cd /usr/local/src
mkdir ffmpeg-libraries
cd ffmpeg-libraries
echo "[INFO]"
echo "[INFO] Building ffmpeg - fdk-aac"
echo "[INFO]"
git clone --depth 1 https://github.com/mstorsjo/fdk-aac.git
cd fdk-aac/
autoreconf -fiv
./configure
make -j4
sudo make install
cd ..
echo "[INFO]"
echo "[INFO] Building ffmpeg - libvpx"
echo "[INFO]"
git clone --depth 1 https://chromium.googlesource.com/webm/libvpx
cd libvpx
./configure --disable-examples --disable-tools --disable-unit_tests --disable-docs --enable-shared
make -j4
sudo make install
sudo ldconfig
cd ..
echo "[INFO]"
echo "[INFO] Building ffmpeg - zimg"
echo "[INFO]"
git clone -b release-2.9.3 https://github.com/sekrit-twc/zimg.git
cd zimg
sh autogen.sh
./configure 
make -j4
sudo make install

echo "[INFO]"
echo "[INFO] Building ffmpeg"
echo "[INFO]"
cd /usr/local/src
# && git clone --depth 1 https://github.com/FFmpeg/FFmpeg.git \
# we are cloning n4.4 since post n4.4 avcodec_get_context_defaults3 was removed from ffmpeg, but the gst-libav has not yet been updated, 
# resulting in a build failure. This should be reverted once gst-libav has been updated. 
git clone --depth 1 -b n4.4 https://github.com/FFmpeg/FFmpeg.git
cd FFmpeg
sudo ./configure --extra-cflags="-I/usr/local/include" --extra-ldflags="-L/usr/local/lib" --enable-libopencore-amrnb  --enable-librtmp --enable-libopus --enable-libopencore-amrwb --enable-gmp --enable-version3 --enable-libdrm --enable-shared  --enable-pic --enable-libvpx --enable-libfdk-aac --target-os=linux --enable-gpl --enable-omx --enable-omx-rpi --enable-pthreads --enable-hardcoded-tables  --enable-omx --enable-nonfree --enable-libfreetype --enable-libx264 --enable-libmp3lame --enable-mmal --enable-indev=alsa --enable-outdev=alsa --disable-vdpau --extra-ldflags="-latomic"
libtoolize
make -j4
libtoolize
sudo make install -j4
sudo ldconfig


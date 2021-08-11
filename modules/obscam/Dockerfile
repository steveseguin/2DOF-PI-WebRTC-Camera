FROM balenalib/raspberrypi3-python:3.7.4

RUN apt-get update && apt-get upgrade && apt-get install -y \
    libomxil-bellagio-dev libfreetype6-dev libmp3lame-dev libx264-dev fonts-freefont-ttf libasound2-dev meson \
    g++ git scons libqt4-dev libqt4-sql-sqlite libportmidi-dev libopusfile-dev libshout3-dev libtag1-dev libprotobuf-dev protobuf-compiler \
    libusb-1.0 libusb-1.0-0-dev libfftw3-dev libmad0-dev libchromaprint-dev librubberband-dev libsqlite3-dev  \
    libid3tag0-dev libflac-dev libupower-glib-dev liblilv-dev libjack-dev libjack0 portaudio19-dev libmp4v2-dev cmake  \
    build-essential autotools-dev automake autoconf checkinstall libtool autopoint libxml2-dev zlib1g-dev libglib2.0-dev \
    pkg-config bison flex python3-dev python-gi-dev python3-gi python-gst-1.0 wget tar gtk-doc-tools libgudev-1.0-dev libcdparanoia-dev \
    libtheora-dev libvisual-0.4-dev iso-codes libraw1394-dev libiec61883-dev libavc1394-dev \
    libv4l-dev libcaca-dev libspeex-dev libpng-dev libjpeg-dev libdv4-dev libwavpack-dev libsoup2.4-dev libbz2-dev \
    libcdaudio-dev libdc1394-22-dev ladspa-sdk libass-dev libcurl4-gnutls-dev libdca-dev libdvdnav-dev \
    libexempi-dev libexif-dev libfaad-dev libgme-dev libgsm1-dev libiptcdata0-dev libkate-dev libmimic-dev libmms-dev \
    libmodplug-dev libmpcdec-dev libofa0-dev libopus-dev librtmp-dev libsndfile1-dev libsoundtouch-dev libspandsp-dev \
    libxvidcore-dev libvpx-dev libzvbi-dev liba52-0.7.4-dev libcdio-dev libdvdread-dev libmpeg2-4-dev libopencore-amrnb-dev libopencore-amrwb-dev \
    libsidplay1-dev libtwolame-dev yasm libgirepository1.0-dev freeglut3 weston wayland-protocols pulseaudio libpulse-dev libssl-dev \
    ccache curl libcap-dev libdrm-dev libegl1-mesa-dev libgl1-mesa-dev libgles2-mesa-dev libgmp-dev libgsl0-dev \
    libmpg123-dev libogg-dev liborc-0.4-dev libpango1.0-dev libvorbis-dev libwebp-dev unzip libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -y autoremove

RUN cd /usr/local/src && git clone https://github.com/libnice/libnice.git \
    && cd libnice/ \
    && meson --prefix=/usr -D buildtype=release -D gst_debug=false build \
    && ninja -C build -j4 \
    && ninja -C build install \
    && sudo ldconfig \
    && rm -rf /usr/local/src/libnice

RUN cd /usr/local/src \
    && apt-get update \
    && apt-get install libwebrtc-audio-processing-dev -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -y autoremove \
    && git clone https://github.com/cisco/libsrtp/ \
    && cd libsrtp \
    && ./configure --prefix=/usr --enable-openssl \
    && make -j4 \
    && make install -j4 \
    && ldconfig \
    && rm -rf /usr/local/src/libsrtp


RUN cd /usr/local/src \
    && git clone https://github.com/sctplab/usrsctp \
    && cd usrsctp \
    && ./bootstrap \
    && libtoolize \
    && ./configure --prefix=/usr \
    && libtoolize \ 
    && make -j4 \
    && make install -j4 \
    && ldconfig \
    && rm -rf /usr/local/src/usrsctp

RUN cd /usr/local/src \
    && git clone --depth 1 https://github.com/mstorsjo/fdk-aac.git \
    && cd fdk-aac/ \
    && autoreconf -fiv \
    && ./configure \
    && make -j4 \
    && make install \
    && ldconfig \
    && rm -rf /usr/local/src/fdk-aac

RUN cd /usr/local/src \
    && git clone --depth 1 https://chromium.googlesource.com/webm/libvpx \
    && cd libvpx \
    && ./configure --disable-examples --disable-tools --disable-unit_tests --disable-docs --enable-shared \
    && make -j4 \
    && make install \
    && ldconfig \
    && rm -rf /usr/local/src/libvpx

RUN cd /usr/local/src \
    && git clone -b release-2.9.3 https://github.com/sekrit-twc/zimg.git \
    && cd zimg \
    && sh autogen.sh \
    && ./configure \
    && make -j4 \
    && make install \
    && ldconfig \
    && rm -rf /usr/local/src/zimg

RUN cd /usr/local/src \
    && git clone --depth 1 https://github.com/raspberrypi/userland.git \
    && cd userland \ 
    && ./buildme \ 
    && echo "/opt/vc/lib" > /etc/ld.so.conf.d/00-vmcs.conf \
    && ldconfig \ 
    && cd .. \
    # && git clone --depth 1 https://github.com/FFmpeg/FFmpeg.git \
    # we are cloning n4.4 since post n4.4 avcodec_get_context_defaults3 was removed from ffmpeg, but the gst-libav has not yet been updated, 
    # resulting in a build failure. This should be reverted once gst-libav has been updated. 
    && git clone --depth 1 -b n4.4 https://github.com/FFmpeg/FFmpeg.git \
    && cd FFmpeg \
    && ./configure --extra-cflags="-I/usr/local/include" --extra-ldflags="-L/usr/local/lib" --enable-libopencore-amrnb  --enable-librtmp --enable-libopus --enable-libopencore-amrwb --enable-gmp --enable-version3 --enable-libdrm --enable-shared  --enable-pic --enable-libvpx --enable-libfdk-aac --target-os=linux --enable-gpl --enable-omx --enable-omx-rpi --enable-pthreads --enable-hardcoded-tables  --enable-omx --enable-nonfree --enable-libfreetype --enable-libx264 --enable-libmp3lame --enable-mmal --enable-indev=alsa --enable-outdev=alsa --disable-vdpau --extra-ldflags="-latomic" \
    && libtoolize \
    && make -j4 \
    && libtoolize \
    && make install -j4 \
    && ldconfig \ 
    && rm -rf /usr/local/src/userland \
    && rm -rf /usr/local/src/FFmpeg

RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && wget https://gstreamer.freedesktop.org/src/gstreamer/gstreamer-1.18.4.tar.xz \
    && tar -xf gstreamer-1.18.4.tar.xz \
    && cd ./gstreamer-1.18.4 \
    && mkdir build \
    && cd ./build \
    && meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled --wrap-mode=nofallback -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" .. \
    && ninja -j4 \
    && ninja install \
    && ldconfig \ 
    && rm -rf /usr/local/src/gstreamer-1.18.4 \
    && rm /usr/local/src/gstreamer-1.18.4.tar.xz

RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && wget https://gstreamer.freedesktop.org/src/gst-plugins-base/gst-plugins-base-1.18.4.tar.xz \
    && tar -xf gst-plugins-base-1.18.4.tar.xz \ 
    && cd ./gst-plugins-base-1.18.4 \
    && mkdir build \
    && cd ./build \
    && meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" .. \
    && ninja -j4 \
    && ninja install \
    && ldconfig \ 
    && rm -rf /usr/local/src/gst-plugins-base-1.18.4 \
    && rm /usr/local/src/gst-plugins-base-1.18.4.tar.xz

RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && wget https://gstreamer.freedesktop.org/src/gst-plugins-good/gst-plugins-good-1.18.4.tar.xz \
    && tar -xf gst-plugins-good-1.18.4.tar.xz \
    && cd ./gst-plugins-good-1.18.4 \
    && mkdir build \
    && cd ./build \
    && meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D target=rpi -D package-name="GStreamer 1.18.4 BLFS" .. \
    && ninja -j4 \
    && ninja install \
    && ldconfig \ 
    && rm -rf /usr/local/src/gst-plugins-good-1.18.4 \
    && rm /usr/local/src/gst-plugins-good-1.18.4.tar.xz

RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && wget https://gstreamer.freedesktop.org/src/gst-plugins-ugly/gst-plugins-ugly-1.18.4.tar.xz \
    && tar -xf gst-plugins-ugly-1.18.4.tar.xz \
    && cd ./gst-plugins-ugly-1.18.4 \
    && mkdir build \
    && cd ./build \ 
    && meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" .. \
    && ninja -j4 \
    && ninja install \
    && ldconfig \ 
    && rm -rf /usr/local/src/gst-plugins-ugly-1.18.4 \
    && rm /usr/local/src/gst-plugins-ugly-1.18.4.tar.xz


RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && wget https://gstreamer.freedesktop.org/src/gst-plugins-bad/gst-plugins-bad-1.18.4.tar.xz \
    && tar -xf gst-plugins-bad-1.18.4.tar.xz \
    && cd ./gst-plugins-bad-1.18.4 \
    && mkdir build \
    && cd ./build \
    && meson --prefix=/usr -D buildtype=release -D gtk_doc=disabled -D gst_debug=false -D package-origin=https://gstreamer.freedesktop.org/src/gstreamer/ -D package-name="GStreamer 1.18.4 BLFS" -D examples=disabled -D x11=disabled -D glx=disabled -D opengl=disabled -D gst-plugins-bad:webrtc=enabled -D gst-plugins-bad:webrtcdsp=enabled -D target=rpi  .. \
    && ninja -j4 \
    && ninja install \
    && ldconfig \ 
    && rm -rf /usr/local/src/gst-plugins-bad-1.18.4 \
    && rm /usr/local/src/gst-plugins-bad-1.18.4.tar.xz

RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && git clone https://github.com/libnice/libnice.git \
    && cd libnice/ \
    && meson --prefix=/usr -D buildtype=release -D gst_debug=false build \
    && ninja -C build -j4 \
    && ninja -C build install \
    && sudo ldconfig \
    && rm -rf /usr/local/src/libnice

COPY requirements.txt ./
RUN python3 -m pip install websockets &&  python3 -m pip install -r requirements.txt 

RUN export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0 \
    && export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib \
    && cd /usr/local/src \
    && wget https://gstreamer.freedesktop.org/src/gst-python/gst-python-1.18.4.tar.xz \
    && tar -xf gst-python-1.18.4.tar.xz \
    && cd ./gst-python-1.18.4/ \
    && mkdir build \
    && cd ./build \
    && meson --prefix=/usr -Dbuildtype=release -Dgst_debug=false -Dgtk_doc=disabled \
    && ninja -j4 \
    && ninja install \
    && ldconfig \ 
    && rm -rf /usr/local/src/gst-python-1.18.4 \
    && rm /usr/local/src/gst-python-1.18.4.tar.xz

ADD scripts /scripts
ADD app /app
WORKDIR /app

ENV PYTHONUNBUFFERED=1
CMD ["python3","app.py"]

# Build time is about 90 min
# docker buildx build --platform linux/arm/v7 --pull --rm -f "Dockerfile" -t obs-cam:pi "."
# docker build  --pull --rm -f "Dockerfile" -t obs-cam:pi "."
# docker run -d --network host --privileged --env-file env_file --device /dev/vchiq --device /dev/video0 --name obs-cam obs-cam:pi
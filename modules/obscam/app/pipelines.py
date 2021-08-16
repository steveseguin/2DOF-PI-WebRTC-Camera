# Copyright (c) 2021 Avanade
# Author: Thor Schueler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# 
# Just keeping some interesting pipelines I played with...
#

test_video_pipeline = '''
webrtcbin name=sendrecv bundle-policy=max-bundle
 videotestsrc ! {custom}  videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay !
 queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! tee name=videotee ! sendrecv.
 audiotestsrc is-live=true wave=red-noise ! audioconvert ! audioresample ! queue ! opusenc ! rtpopuspay !
 queue ! application/x-rtp,media=audio,encoding-name=OPUS,payload=96 ! tee name=audiotee ! sendrecv.
''' # test source with video and audio.
    # not used anymore. This was prior to the dynamic multi-client handling.

test_video_pipeline = '''
tee name=videotee ! queue ! fakesink
videotestsrc ! {custom} videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay ! queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! videotee.
tee name=audiotee ! queue ! fakesink
audiotestsrc is-live=true wave=ticks apply-tick-ramp=true tick-interval=200000000 freq=5000 volume=0.4 marker-tick-period=10 sine-periods-per-tick=20 !  queue ! opusenc ! rtpopuspay ! queue leaky=1 max-size-time=16000000 max-size-buffers=0 max-size-bytes=0 ! application/x-rtp,media=audio,encoding-name=OPUS,payload=96 ! audiotee.
''' # test source with video and audio.
    # I had problems getting the audio reliably to start. 

test_video_pipeline = '''
tee name=audiotee ! queue ! fakesink
audiotestsrc is-live=true wave=ticks apply-tick-ramp=true tick-interval=200000000 freq=5000 volume=0.4 marker-tick-period=10 sine-periods-per-tick=20 ! audioconvert ! queue ! opusenc ! rtpopuspay ! queue ! application/x-rtp,media=audio,encoding-name=OPUS,payload=96 ! audiotee.
''' # test source with video and audio.
    # audio only pipeline

test_video_pipeline = '''
tee name=videotee ! queue ! fakesink 
videotestsrc ! {custom} videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay ! queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! videotee. 
''' # test source with video and audio.
    # video only pipeline

    
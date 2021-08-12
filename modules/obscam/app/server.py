import argparse
import asyncio
import datetime
import json
import logging
import os
import random
import ssl
import sys
import time
import gi
import websockets

gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import Gst, GstSdp, GstWebRTC


class WebRTCClient:
    def __init__(self, pipeline, peer_id, server='wss://apibackup.obs.ninja:443'):
        ###
        ###  To avoid causing issues for production; default server is api.backup.obs.ninja. 
        ###  Streams can be view at https://backup.obs.ninja/?password=false&view={peer_id} as a result.
        ###
        self.__conn = None
        self.__pipe = None
        self.__webrtc = None
        self.__UUID = None
        self.__session = None
        self.__peer_id = peer_id
        self.__server = server 
        self.__pipeline = pipeline
        self.__logger = logging.getLogger('htxi.modules.camera.webrtc')
        self.__clients = 0

    #
    # region public properties
    #
    @property
    def Clients(self) -> int:
        return self.__clients

    @property
    def Pipeline(self) -> str:
        return self.__pipeline
    
    @Pipeline.setter
    def Pipeline(self, pipeline:str):
        if pipeline != self.__pipeline:
            self.__logger.info(f"{datetime.datetime.now()}: Pipeline property has changed... restarting stream.")
            self.__pipeline = pipeline
            self.__pipe.set_state(Gst.State.NULL)
            self.__clients = 0


    @property 
    def StreamId(self) -> str:
        return self.__peer_id

    @StreamId.setter
    def StreamId(self, stream_id:str):
        if stream_id != self.__peer_id:
            self.__logger.info(f"{datetime.datetime.now()}: StreamId property has changed... restarting stream.")
            self.__peer_id = stream_id
            self.__pipe.set_state(Gst.State.NULL)
            self.__clients = 0

    @property
    def Server(self) -> str:
        return self.__server

    @Server.setter
    def Server(self, server:str):
        if server != self.server:
            self.__logger.info(f"{datetime.datetime.now()}: StreamId property has changed... restarting stream.")
            self.__server = server
            self.__clients = 0
            self.connect()
    #
    # endregion
    #

    #
    # region public methods
    #
    async def connect(self):  
        if self.__conn is not None: 
            self.__conn.close()
            self.__conn = None

        sslctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        msg = json.dumps({"request":"seed","streamID":self.__peer_id})
        self.__logger.info(f"{datetime.datetime.now()}: {msg}")
        self.__logger.info(f"{datetime.datetime.now()}: Connect")
        self.__conn = await websockets.connect(self.__server, ssl=sslctx)
        await self.__conn.send(msg)

    async def loop(self):
        try:
            self.__logger.info(f"{datetime.datetime.now()}: LOOP START")
            assert self.__conn
            self.__logger.info(f"{datetime.datetime.now()}: WSS CONNECTED")
            async for message in self.__conn:
                msg = json.loads(message)
                self.__logger.debug(f"{datetime.datetime.now()}: MESSAGE LOOP RECEIVED: {msg}")

                if 'UUID' in msg: self.__UUID = msg['UUID']
                if 'session' in msg: self.__session = msg['session']
                if 'description' in msg:
                    msg = msg['description']
                    if 'type' in msg:
                        if msg['type'] == "offer":
                            self.__start_pipeline()
                            await self.__handle_offer(msg)
                        elif msg['type'] == "answer":
                            await self.__handle_sdp(msg)
                            
                elif 'candidates' in msg:
                    for ice in msg['candidates']:
                        await self.__handle_sdp(ice)
                        
                elif 'request' in msg:
                    if 'offerSDP' in  msg['request']:
                        self.__start_pipeline()
                else:
                    self.__logger.warning(f"{datetime.datetime.now()}: Received unknown message: {message}")
        except asyncio.CancelledError:
            self.__logger.info(f"{datetime.datetime.now()}: Reveived cancellation request. Exiting...")
        except Exception as e:
            self.__logger.error(f"{datetime.datetime.now()}: Unexpected error: {e}")
            raise
        finally: 
            self.__logger.info(f"{datetime.datetime.now()}: Ending WebRTC loop.")
        return 0
    #
    # endregion
    #


    #
    # region private methods
    #
    def __create_answer(self):
        promise = Gst.Promise.new_with_change_func(self.__on_answer_created, self.__webrtc, None)
        self.__webrtc.emit('create-answer', None, promise)

    async def __handle_sdp(self, msg):
        assert (self.__webrtc)
        if 'sdp' in msg:
            self.__logger.info(f"{datetime.datetime.now()}: HANDLE SDP")
            msg = msg
            assert(msg['type'] == 'answer')
            sdp = msg['sdp']
            self.__logger.debug(f"{datetime.datetime.now()}: Received answer:\n{sdp}")
            res, sdpmsg = GstSdp.SDPMessage.new()
            GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
            answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg)
            promise = Gst.Promise.new()
            self.__webrtc.emit('set-remote-description', answer, promise)
            promise.interrupt()
        elif 'candidate' in msg:
            self.__logger.info(f"{datetime.datetime.now()}: HANDLE CANDIDATE")
            candidate = msg['candidate']
            sdpmlineindex = msg['sdpMLineIndex']
            self.__webrtc.emit('add-ice-candidate', sdpmlineindex, candidate)

    async def __handle_offer(self, msg):
        assert (self.__webrtc)
        if 'sdp' in msg:
            self.__logger.info(f"{datetime.datetime.now()}: HANDLE SDP OFFER")
            msg = msg
            assert(msg['type'] == 'offer')
            sdp = msg['sdp']
            self.__logger.debug(f"{datetime.datetime.now()}: Received offer:\n{sdp}")
            res, sdpmsg = GstSdp.SDPMessage.new()
            GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
            offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)
            promise = Gst.Promise.new()
            self.__webrtc.emit('set-remote-description', offer, promise)
            promise.interrupt()
            self.__create_answer()

    def __on_answer_created(self, promise, _, __):
        self.__logger.info(f"{datetime.datetime.now()}: ON ANSWER CREATED")
        promise.wait()
        reply = promise.get_reply()
        answer = reply.get_value('answer')
        promise = Gst.Promise.new()
        self._webrtc.emit('set-local-description', answer, promise)
        promise.interrupt()
        self.__logger.info(f"{datetime.datetime.now()}: SEND SDP ANSWER")
        text = answer.sdp.as_text()
        msg = json.dumps({'description': {'type': 'answer', 'sdp': text, 'UUID': self.__UUID, 'session': self.__session}})
        self.__logger.info(f"{datetime.datetime.now()}: {msg}")
        asyncio.new_event_loop().run_until_complete(self.__conn.send(msg))
        self.__logger.info(f"{datetime.datetime.now()}: SENT MESSAGE")

    def __on_connection_state(self, _, prop):
        self.__logger.info(f"{datetime.datetime.now()}: Connection status change: {self.__webrtc.get_property(prop.name).value_nick}")

    def __on_ice_connection_state(self, _, prop):
        self.__logger.info(f"{datetime.datetime.now()}: ICE connection status change: {self.__webrtc.get_property(prop.name).value_nick}")

    def __on_incoming_decodebin_stream(self, _, pad): 
        #
        # If daring to capture inbound video; support not assured at this point.
        #
        self.__logger.info(f"{datetime.datetime.now()}: ON INCOMING")
        if not pad.has_current_caps():
            self.__logger.warning(f"{datetime.datetime.now()}: {pad} has no caps, ignoring")
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        if name.startswith('video'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('videoconvert')
            sink = Gst.ElementFactory.make('autovideosink')
            self.__pipe.add(q)
            self.__pipe.add(conv)
            self.__ipe.add(sink)
            self.__pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(sink)
        elif name.startswith('audio'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('audioconvert')
            resample = Gst.ElementFactory.make('audioresample')
            sink = Gst.ElementFactory.make('autoaudiosink')
            self.__pipe.add(q)
            self.__pipe.add(conv)
            self.__pipe.add(resample)
            self.__pipe.add(sink)
            self.__pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(resample)
            resample.link(sink)

    def __on_incoming_stream(self, _, pad):
        self.__logger.info(f"{datetime.datetime.now()}: ON INCOMING STREAM")
        try:
            if Gst.PadDirection.SRC != pad.direction:
                return
        except:
            return
        self.__logger.info(f"{datetime.datetime.now()}: INCOMING STREAM")
        decodebin = Gst.ElementFactory.make('decodebin')
        decodebin.connect('pad-added', self.__on_incoming_decodebin_stream)
        self.__pipe.add(decodebin)
        decodebin.sync_state_with_parent()
        self.__webrtc.link(decodebin)

    def __on_negotiation_needed(self, element):
        self.__logger.info(f"{datetime.datetime.now()}: ON NEGO NEEDED")
        promise = Gst.Promise.new_with_change_func(self.__on_offer_created, element, None)
        element.emit('create-offer', None, promise)

    def __on_offer_created(self, promise, _, __):  
        ###
        ### This is all based on the legacy API of OBS.Ninja; 
        ### gstreamer-1.19 lacks support for the newer API.
        ###
        self.__logger.info(f"{datetime.datetime.now()}: ON OFFER CREATED")
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer') 
        promise = Gst.Promise.new()
        self.__webrtc.emit('set-local-description', offer, promise)
        promise.interrupt()
        self.__logger.info(f"{datetime.datetime.now()}: SEND SDP OFFER")
        text = offer.sdp.as_text()
        msg = json.dumps({'description': {'type': 'offer', 'sdp': text}, 'UUID': self.__UUID, 'session': self.__session, 'streamID':self.__peer_id})
        self.__logger.debug(f"{datetime.datetime.now()}: {msg}")
        asyncio.new_event_loop().run_until_complete(self.__conn.send(msg))
        self.__logger.info(f"{datetime.datetime.now()}: SENT MESSAGE")

    def __send_ice_candidate_message(self, _, mlineindex, candidate):
        self.__logger.info(f"{datetime.datetime.now()}: SEND ICE - UUID: {self.__UUID}, {candidate}")
        icemsg = json.dumps({'candidates': [{'candidate': candidate, 'sdpMLineIndex': mlineindex}], 'session':self.__session, 'type':'local', 'UUID':self.__UUID})
        asyncio.new_event_loop().run_until_complete(self.__conn.send(icemsg))

    def __start_pipeline(self):
        self.__logger.info(f"{datetime.datetime.now()}: START PIPE")
        if self.__pipe is not None: 
            self.__logger.info(f"{datetime.datetime.now()}: Resetting existing pipeline...")
            self.__pipe.set_state(Gst.State.NULL)
        self.__pipe = Gst.parse_launch(self.__pipeline)
        self.__webrtc = self.__pipe.get_by_name('sendrecv')
        self.__webrtc.connect('on-negotiation-needed', self.__on_negotiation_needed)
        self.__webrtc.connect('on-ice-candidate', self.__send_ice_candidate_message)
        self.__webrtc.connect('pad-added', self.__on_incoming_stream)
        self.__webrtc.connect('notify::ice-connection-state', self.__on_ice_connection_state)
        self.__webrtc.connect('notify::connection-state', self.__on_connection_state)
        self.__pipe.set_state(Gst.State.PLAYING)


    #
    # endregion
    #

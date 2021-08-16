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
from gi.repository import Gst, GstSdp, GstWebRTC, GObject
from typing import Dict, List


class WebRTCClient:
    """This class implements a WebRTC gstreamer source"""

    def __init__(self, pipeline:str, stream_id:str, server:str='wss://apibackup.obs.ninja:443', logging_level:int = logging.INFO, max_clients:int=5):
        """
        Initializes the class. 

        :param pipeline:    The basic streaming pipeline to use. This is a standard gstreamer pipeline, but note two things:
                            - the pipeline should contain a tee called audiotee, a tee called videotee or both. 
                            - the pipeline is started immidiately, so after the tee, you probably want to use a fakesink. As 
                              clients connect, we will add additional branches with a queue and a webrtcbin to the pipeline. 
        :type pipeline:     str

        :param stream_id:   The of the stream. Clients will need to know that to connect. 
        :type stream_id:    str

        :param server:      The signaling server. To avoid causing issues for production; default server is api.backup.obs.ninja. 
                            Streams can be view at https://backup.obs.ninja/?password=false&view={stream_id} as a result.
        :type server:       str

        :param logging_level The logging level for the class. The logger uses htxi.modules.camera.webrtc. Defaults to logging.INFO
        :type logging_level  int

        :param max_clients  The maximum number of clients to allow concurrently. The behaior of this is a bit crazy right now. Since I have not
                            found a good way to detect when a remote clients drops off, so when this limit is reached, all clients are disconnected to free up
                            dead connections. Since gst webrtcbin supports renegotiation, active clients will simply reconnect. This needs to be
                            reworked once I figure out how to detect dropoffs to simply deny additional requests. 
        :type max_clients   int
        """
        self.__conn = None
        self.__connected:bool  = False
        self.__pipe = None
        self.__session = None
        self.__webrtc_collection:Dict[str, object] = {}
        self.__stream_id:str = stream_id
        self.__server:str = server 
        self.__pipeline:str = pipeline
        self.__logger = logging.getLogger('htxi.modules.camera.webrtc')
        self.__logger.setLevel(logging_level)
        self.__restart = False
        self.__max_clients = max_clients
        self.__client_monitoring_period = 60

    #
    # region public properties
    #
    @property
    def Clients(self) -> int:
        """ 
        Gets the number of connected clients. We really have not figured that out yet correctly, so this right now
        will show the number of active webrtcbins in the pipeline. Unfortunately, i do not know yet how to detect
        whether a client disconnects from the feed...
        """
        return len(self.__webrtc_collection)

    @property 
    def ClientMonitoringPeriod(self) -> int:
        """
        Gets the period with which we'll monitor for client connection health
        """
        return self.__client_monitoring_period

    @ClientMonitoringPeriod.setter
    def ClientMonitoringPeriod(self, period:int):
        """
        Sets the period with which we'll monitor for client connection health
        """
        self.__client_monitoring_period = period

    @property
    def MaxClients(self) -> int:
        """
        Gets the maximum number of clients to allow concurrently. The behaior of this is a bit crazy right now. Since I have not
        found a good way to detect when a remote clients drops off, so when this limit is reached, all clients are disconnected to free up
        dead connections. Since gst webrtcbin supports renegotiation, active clients will simply reconnect. This needs to be
        reworked once I figure out how to detect dropoffs to simply deny additional requests.
        """
        return self.__max_clients

    @MaxClients.setter
    def MaxClients(self, max_clients:int):
        """
        Sets the ceiling for concurrent connections. 
        """
        self.__max_clients = max_clients

    @property
    def Pipeline(self) -> str:
        """
        Gets the pipeline string
        """
        return self.__pipeline
    
    @Pipeline.setter
    def Pipeline(self, pipeline:str):
        """
        Sets the pipeline string. Setting the pipeline will reset it and lead to a disconnect of all clients
        """
        if pipeline != self.__pipeline:
            self.__logger.info(f"{datetime.datetime.now()}: Pipeline property has changed... restarting stream.")
            self.__pipeline = pipeline
            self.__remove_all_clients()
            self.__start_pipeline()
            
    @property 
    def StreamId(self) -> str:
        """
        Gets the stream id
        """
        return self.__stream_id

    @StreamId.setter
    def StreamId(self, stream_id:str):
        """
        Sets the stream id. This will require a reconnect and all clients will be dropped from the pipeline. However, the 
        pipeline itself will not restart. 
        """
        if stream_id != self.__stream_id:
            self.__logger.info(f"{datetime.datetime.now()}: StreamId property has changed... restarting stream.")
            self.__stream_id = stream_id
            self.__remove_all_clients()
            self.__restart = True
            asyncio.create_task(self.connect())
            

    @property
    def Server(self) -> str:
        """
        Gets the signaling server
        """
        return self.__server

    @Server.setter
    def Server(self, server:str):
        '''
        Sets the signalling server. This will require a reconned and all clients will be dropped from the pipeline. However, the 
        pipeline itself will not restart. 
        '''
        if server != self.__server or True:
            self.__logger.info(f"{datetime.datetime.now()}: Server property has changed... restarting stream.")
            self.__server = server
            self.__remove_all_clients()
            self.__restart = True
            asyncio.create_task(self.connect())
            
    #
    # endregion
    #

    #
    # region public methods
    #
    async def connect(self): 
        """
        Connects to the signaling server. This method should be called prior to entering the message loop. 
        """ 
        self.__logger.info(f"{datetime.datetime.now()}: Initiating connection to signaling server.")
        if self.__conn is not None: 
            self.__connected = False
            await self.__conn.close()
            self.__conn = None
            
        sslctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        msg = json.dumps({"request":"seed","streamID":self.__stream_id})
        self.__logger.info(f"{datetime.datetime.now()}: {msg}")
        self.__logger.info(f"{datetime.datetime.now()}: Connect")
        self.__conn = await websockets.connect(self.__server, ssl=sslctx)
        await self.__conn.send(msg)
        self.__connected = True
        self.__logger.info(f"{datetime.datetime.now()}: WSS connected")
        
    async def loop(self):
        """
        Message loop listening to the signaling server and serving various peer requesteds. This loop should run until you no longer
        want to serve clients.
        """
        hasrun = False
        self.__start_pipeline()

        while not hasrun or self.__restart:
            hasrun = True
            while not self.__connected: await asyncio.sleep(0.1)
            self.__restart  = False
            ret = await self.__loop()
        
        return ret
    #
    # endregion
    #


    #
    # region private methods
    #
    def __add_client(self, client_id:str):
        """
        Adds a new webrtcbin branch to the gstreamer pipeline and wires up the control structure. 

        :param client_id    The id of the remote peer
        :type client_id     str
        """
        self.__logger.debug(f"{datetime.datetime.now()}: Pipeline status: {self.__pipe.get_state(0)[1].value_nick}")

        if client_id in self.__webrtc_collection.keys():
            self.__logger.debug(f"{datetime.datetime.now()}: Found existing pipeline segment for client id. Removing....")
            self.__remove_client(client_id)

        atee = self.__pipe.get_by_name('audiotee')
        vtee = self.__pipe.get_by_name('videotee')
        if vtee is None and atee is None: 
            self.__logger.error(f"{datetime.datetime.now()}: Pipeline does not contain audio or video tee. Cannot proceed adding a client.")
            raise Exception("Pipeline does not contain audio or video tee. Cannot proceed adding a client.")

        self.__logger.info(f"{datetime.datetime.now()}: Creating new pipeline segment")
        qa = None
        qv = None
        webrtc = Gst.ElementFactory.make("webrtcbin", client_id)
        webrtc.set_property('bundle-policy', GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE) 

        if vtee is not None:
            self.__logger.info(f"{datetime.datetime.now()}: Found video-tee to attach new stream")
            qv = Gst.ElementFactory.make('queue', f"v-queue-{client_id}")
            self.__pipe.add(qv)
        
        if atee is not None:
            self.__logger.info(f"{datetime.datetime.now()}: Found audio-tee to attach new stream")
            qa = Gst.ElementFactory.make('queue', f"a-queue-{client_id}")
            self.__pipe.add(qa)  

        self.__logger.info(f"{datetime.datetime.now()}: Linking new pipeline segment")
        self.__pipe.add(webrtc)
        if vtee is not None and qv is not None: 
            if not Gst.Element.link(vtee, qv): raise Exception ("Could not link vtee -> qv")
            if not Gst.Element.link(qv, webrtc): raise Exception ("Could not link qv -> webrtcbin")
        if atee is not None and qa is not None: 
            if not Gst.Element.link(atee, qa): raise Exception ("Could not link atee -> qa")
            if not Gst.Element.link(qa, webrtc): raise Exception ("Could not link qa -> webrtcbin")
            
        self.__logger.info(f"{datetime.datetime.now()}: Wiring new webrtcbin to control structure")
        webrtc.connect('on-negotiation-needed', self.__on_negotiation_needed)
                    # This is the gstwebrtc entry point where we create the offer and so on. It
                    # will be called when the pipeline goes to PLAYING.
                    # Important: We must connect this ***after*** webrtcbin has been linked to a source via
                    # get_element.link() and before we go from NULL->READY otherwise webrtcbin
                    # will create an SDP offer with no media lines in it. 

        webrtc.connect('on-ice-candidate', self.__send_ice_candidate_message)
        webrtc.connect('notify::ice-connection-state', self.__on_ice_connection_state)
        webrtc.connect('notify::connection-state', self.__on_connection_state)
        self.__webrtc_collection[client_id] = webrtc

        self.__logger.info(f"{datetime.datetime.now()}: Set new GST branch to playing")    
        if qv is not None: qv.sync_state_with_parent()
        if qa is not None: qa.sync_state_with_parent()
        webrtc.sync_state_with_parent()
        self.__pipe.set_state(Gst.State.PLAYING)
        self.__logger.info(f"{datetime.datetime.now()}: Pipeline status: {self.__pipe.get_state(0)[1].value_nick}")
        
    async def __check_clients_occasionally(self):
        """
        Occasionally checks for the health of the connection to the peers. This does currently not work. Needs to be reviewed, but the idea is to identify
        and disconnect abandoned peers. 

        The behaior of this is a bit crazy right now. Since I have not
        found a good way to detect when a remote clients drops off, we are using max_clients. When this limit is reached, all clients are disconnected to free up
        dead connections. Since gst webrtcbin supports renegotiation, active clients will simply reconnect. This needs to be
        reworked once I figure out how to detect dropoffs to simply deny additional requests.
        
        I did experiment with get-stats, (see __on_get_stats below) but have not yet found a good way.... 
        """
        self.__logger.debug(f"{datetime.datetime.now()}: Checking client connection status") 
        while True:
            for client_id, webrtcbin in self.__webrtc_collection.items():
                self.__logger.debug(f"{datetime.datetime.now()}: Checking status of {client_id}: {webrtcbin.get_property('connection-state').value_nick}, {webrtcbin.get_property('ice-connection-state').value_nick}, {webrtcbin.get_state(0)[1].value_nick}")
                if self.__logger.getEffectiveLevel() == logging.DEBUG:
                    promise = Gst.Promise.new_with_change_func(self.__on_get_stats, client_id, None)
                    webrtcbin.emit("get-stats", None, promise)
            if len(self.__webrtc_collection) >= self.__max_clients: 
                self.__logger.warning(f"{datetime.datetime.now()}: Active client threads exceed maximum allowed: {len(self.__webrtc_collection)}/{self.__max_clients}. Clearing out clients....")
                self.__remove_all_clients()
            await asyncio.sleep(self.__client_monitoring_period)   

    def __on_get_stats(self, promise:Gst.Promise, client_id:str, __):
        """
        Callback used by webrtcbin to inform us that the stats promise has been resolved and starts are ready. 

        :param promise      Fullfilled promise contianing the stats data. 
        :type promise       Gst.Promise

        :param client_id    Id of the client bracnh for which the stats are obtained. 
        :type client_id     str 
        """
        def __field_inspector(id, value, _):
            self.__logger.debug(f"{datetime.datetime.now()}: {id} - {value}")
            return True
        
        self.__logger.debug(f"{datetime.datetime.now()}: recevied stats for {client_id}")
        reply = promise.get_reply()
        self.__logger.debug(f"{datetime.datetime.now()}: {reply.get_name_id()} - {reply.get_name()} - {reply.n_fields()} fields")
        reply.foreach(__field_inspector, None)
        val = reply.id_get_value(2849)
        if reply.n_fields() > 5:
            val = reply.get_value(reply.nth_field_name(5))
            val.foreach(__field_inspector, None)
            self.__logger.debug(f"{datetime.datetime.now()}: {reply.has_field('remote-inbound-rtp')} - {reply.nth_field_name(5)} - {val.get_name()} - {val.to_string()}")

    async def __handle_sdp(self, client_id:str, msg:Dict[str, object]):
        """
        Handles the SDP communication. This method is called by loop when an SDP anwer is received.  

        :param client_id    The id of the peer
        :type client_id     str

        :param msg          The message to be processed
        :type message       Dict[str, object]
        """
        webrtc = self.__webrtc_collection[client_id]
        assert (webrtc)
        if 'sdp' in msg:
            self.__logger.info(f"{datetime.datetime.now()}: Handle SDP")
            msg = msg
            assert(msg['type'] == 'answer')
            sdp = msg['sdp']
            self.__logger.debug(f"{datetime.datetime.now()}: Received answer:\n{sdp}")
            res, sdpmsg = GstSdp.SDPMessage.new()
            GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
            answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg)
            promise = Gst.Promise.new()
            webrtc.emit('set-remote-description', answer, promise)
            promise.interrupt()

    async def __handle_candidate(self, client_id:str, msg:Dict[str, object]):
        """
        Handles the candidate negotiation  

        :param client_id    The id of the peer
        :type client_id     str

        :param msg          The message to be processed
        :type message       Dict[str, object]
        """
        webrtc = self.__webrtc_collection[client_id]
        assert (webrtc)
        if 'candidate' in msg:
            self.__logger.info(f"{datetime.datetime.now()}: Handle CANDIDATE")
            candidate = msg['candidate']
            sdpmlineindex = msg['sdpMLineIndex']
            webrtc.emit('add-ice-candidate', sdpmlineindex, candidate)  

    async def __loop(self):
        """
        The main loop that listens via socket connection to the signaling server to initiate
        peer connections.
        """
        uuid:str = None
        try:
            assert self.__conn
            self.__logger.info(f"{datetime.datetime.now()}: Start message loop")
            asyncio.get_event_loop().create_task(self.__check_clients_occasionally())
            async for message in self.__conn:
                msg = json.loads(message)
                self.__logger.debug(f"{datetime.datetime.now()}: Message loop received message: {msg}")

                if 'UUID' in msg: uuid = msg['UUID']
                if 'session' in msg: self.__session = msg['session']
                if 'description' in msg:
                    msg = msg['description']
                    if 'type' in msg:
                        if msg['type'] == "offer": 
                            self.__logger.warning(f"{datetime.datetime.now()}: Received incoming offer. Incoming calls are not supported for this use.")
                        elif msg['type'] == "answer":
                            await self.__handle_sdp(uuid, msg)
                            
                elif 'candidates' in msg:
                    for ice in msg['candidates']:
                        await self.__handle_candidate(uuid, ice)
                        
                elif 'request' in msg:
                    if 'offerSDP' in  msg['request']:
                        self.__logger.info(f"{datetime.datetime.now()}: Received streaming request")
                        self.__add_client(uuid)
                else:
                    self.__logger.warning(f"{datetime.datetime.now()}: Received unknown message: {message}")
        except asyncio.CancelledError:
            self.__logger.info(f"{datetime.datetime.now()}: Reveived cancellation request. Exiting...")
            self.__pipe.set_state(Gst.State.NULL)
            self.__remove_all_clients()
            await self.__conn.close()
            del self.__pipe
        except Exception as e:
            self.__logger.error(f"{datetime.datetime.now()}: Unexpected error: {e}")
            raise
        finally: 
            self.__logger.info(f"{datetime.datetime.now()}: Ending WebRTC loop.")
        return 0

    def __on_connection_state(self, webrtcbin:Gst.Element, prop:object):
        """
        Handles connection state changes on the WebRtcBin

        :param webrtcbin    The webrtcbin that detected the connection state change
        :type webrtcbin     Gst.Element (GstWebRTC)

        :param prop         The property causin the change. In this case this will be Connection-State
        :type prop          object
        """
        self.__logger.info(f"{datetime.datetime.now()}: Connection status change: {webrtcbin.get_property(prop.name).value_nick}")

    def __on_ice_connection_state(self, webrtcbin:Gst.Element, prop:object):
        """
        Handles ICE connection state changes on the WebRtcBin

        :param webrtcbin    The webrtcbin that detected the connection state change
        :type webrtcbin     Gst.Element (GstWebRTC)

        :param prop         The property causin the change. In this case this will be Ice-Connection-State
        :type prop          object
        """
        self.__logger.info(f"{datetime.datetime.now()}: ICE connection status change: {webrtcbin.get_property(prop.name).value_nick}")

    def __on_message(bus: Gst.Bus, message: Gst.Message, loop: GObject.MainLoop):
        """
        Listens on the GST bus for messages

        :param bus      GST pipeline message bus
        :type bus       Gst.Bus

        :param message  Message reveived
        :type message   Gst.Message

        :param loop     GST main loop
        :type loop      GObject.MainLoop
        """
        mtype = message.type
        #
        #    Gstreamer Message Types and how to parse
        #    https://lazka.github.io/pgi-docs/Gst-1.0/flags.html#Gst.MessageType 
        #
        if mtype == Gst.MessageType.EOS: 
            self.__logger.warning(f"{datetime.datetime.now()}: GST message: EOS. Exiting") 
            loop.quit()
        elif mtype == Gst.MessageType.ERROR: 
            err, debug = message.parse_error() 
            self.__logger.error(f"{datetime.datetime.now()}: GST pipeline error: {err}, {debug}") 
            loop.quit()
        elif mtype == Gst.MessageType.WARNING: 
            err, debug = message.parse_warning() 
            self.__logger.warning(f"{datetime.datetime.now()}: GST pipeline warning: {err}, {debug}") 
        else:
            self.__logger.info(f"{datetime.datetime.now()}: GST pipeline message: {mtype}, {message}") 
        return True

    def __on_negotiation_needed(self, webrtcbin):
        self.__logger.info(f"{datetime.datetime.now()}: Negotiation request. Creating offer....")
        promise = Gst.Promise.new_with_change_func(self.__on_offer_created, webrtcbin, None)
        webrtcbin.emit('create-offer', None, promise)

    def __on_offer_created(self, promise:Gst.Promise, webrtcbin:Gst.Element, __): 
        """
        Creates on offer for the peer

        :param promise      The promise related to the offer
        :type promise       Gst.Promise

        :param webrtcbin    The webrtcbin element
        :type webrtcbin     Gst.Element (WebRTCBin)
        """ 
        ###
        ### This is all based on the legacy API of OBS.Ninja; 
        ### gstreamer-1.19 lacks support for the newer API.
        ###
        uuid = webrtcbin.name
        self.__logger.debug(f"{datetime.datetime.now()}: Start offering creating for UUID: {uuid}")
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer') 
        promise = Gst.Promise.new()
        webrtcbin.emit('set-local-description', offer, promise)
        promise.interrupt()
        self.__logger.info(f"{datetime.datetime.now()}: Sending SDP offer")
        text = offer.sdp.as_text()
        msg = json.dumps({'description': {'type': 'offer', 'sdp': text}, 'UUID': uuid, 'session': self.__session, 'streamID':self.__stream_id})
        self.__logger.debug(f"{datetime.datetime.now()}: SDP offer message: {msg}")
        asyncio.new_event_loop().run_until_complete(self.__conn.send(msg))
        self.__logger.info(f"{datetime.datetime.now()}: SDP offer message sent")

    def __send_ice_candidate_message(self, webrtcbin:Gst.Element, mlineindex:int, candidate:str):
        """
        Assemble and send ICE message for a particular candidate

        :param webrtcbin        The WebRTCBin element
        :type webrtcbin         Gst.Element     (WebRTCBin) 

        :param mlineindex       The candidate index
        :type mlineindex        int

        :param candidate        Candidate information
        :type candidate         str
        """
        uuid = webrtcbin.name
        self.__logger.debug(f"{datetime.datetime.now()}: SENDING ICE - UUID: {uuid}")
        icemsg = json.dumps({'candidates': [{'candidate': candidate, 'sdpMLineIndex': mlineindex}], 'session':self.__session, 'type':'local', 'UUID':uuid})
        asyncio.new_event_loop().run_until_complete(self.__conn.send(icemsg))
        self.__logger.info(f"{datetime.datetime.now()}: SENT ICE - UUID: {uuid}, {candidate}")

    def __start_pipeline(self):
        """
        Parse and start the gst pipeline. If a pipeline already exists, this pipeline will be torn down firts. 
        """
        self.__logger.info(f"{datetime.datetime.now()}: Pre-roll GST pipeline")
        if self.__pipe is not None: 
            self.__logger.info(f"{datetime.datetime.now()}: Found existing pipeline. Resetting and releasing.")
            self.__pipe.set_state(Gst.State.NULL)
            del self.__pipe
        self.__pipe = Gst.parse_launch(self.__pipeline)
        if self.__pipe.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.__logger.error(f"{datetime.datetime.now()}: Could not start pipeline {self.__pipeline}")
            raise Exception(f"Could not start pipeline {self.__pipeline}")
        bus = self.__pipe.get_bus()
        bus.connect("message", self.__on_message, None)
        self.__logger.info(f"{datetime.datetime.now()}: Pipeline status: {self.__pipe.get_state(0)[1].value_nick}")
        while self.__pipe.get_state(0)[1] is not Gst.State.PLAYING:
            time.sleep(1)
            self.__logger.info(f"{datetime.datetime.now()}: Pipeline status: {self.__pipe.get_state(0)[1].value_nick}")

    def __remove_all_clients(self):
        """
        Removes all active clients. 
        """
        ids = []
        self.__logger.info(f"{datetime.datetime.now()}: Stopping pipeline")
        if self.__pipe.set_state(Gst.State.NULL) == Gst.StateChangeReturn.FAILURE: self.__logger.error(f"{datetime.datetime.now()}: Could not stop pipeline")
        while True:
            self.__logger.info(f"{datetime.datetime.now()}: Pipeline status: {self.__pipe.get_state(0)[1].value_nick}")
            if self.__pipe.get_state(0)[1] is Gst.State.NULL: break
            time.sleep(1)

        for client_id in self.__webrtc_collection.keys(): ids.append(client_id)
        for client_id in ids:self.__remove_client(client_id)
        
        self.__logger.info(f"{datetime.datetime.now()}: Restarting pipeline")
        if self.__pipe.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE: self.__logger.error(f"{datetime.datetime.now()}: Could not start pipeline")
        while True:
            self.__logger.info(f"{datetime.datetime.now()}: Pipeline status: {self.__pipe.get_state(0)[1].value_nick}")
            if self.__pipe.get_state(0)[1] is Gst.State.PLAYING: break
            time.sleep(1)
            


    def __remove_client(self, client_id:str):
        """
        Removes a client and dismantels the webrtcbin scaffold associated with the client. 

        :param client_id    ID of the peer to remove
        :type client_id     str
        """
        webrtc = self.__pipe.get_by_name(client_id)
        qa = self.__pipe.get_by_name(f"a-queue-{client_id}")
        qv = self.__pipe.get_by_name(f"v-queue-{client_id}")
        atee = self.__pipe.get_by_name('audiotee')
        vtee = self.__pipe.get_by_name('videotee')

        if atee is not None and qa is not None: atee.unlink(qa)
        if vtee is not None and qv is not None: vtee.unlink(qv)

        self.__pipe.remove(webrtc)
        webrtc.set_state(Gst.State.NULL)
        del self.__webrtc_collection[client_id]
        del webrtc
        if qa is not None: 
            self.__pipe.remove(qa)
            qa.set_state(Gst.State.NULL)
            del qa
        if qv is not None:
            self.__pipe.remove(qv)
            qv.set_state(Gst.State.NULL)
            del qv
        self.__logger.info(f"{datetime.datetime.now()}: Removed GST branch for client {client_id}")

    #
    # endregion
    #

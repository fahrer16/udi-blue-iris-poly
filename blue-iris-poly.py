#!/usr/bin/env python3
"""
This NodeServer has been modified by markv58 (Mark Vittes) to include a ping function to test if the Blue Iris
pc is up and running. There are other modifications to update driver panels in the ISY should they be blank.
This is a NodeServer for Blue Iris written by fahrer16 (Brian Feeney) 
based on the template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com
Blue Iris json functionality based on 'blueiriscmd' project by magapp (https://github.com/magapp/blueiriscmd)
"""

import polyinterface
import requests, json, hashlib
import sys
import os

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super().__init__(polyglot)
        self.name = 'Blue Iris'
        self.initialized = False
        self.hostup = True
        self.tries = 0

    def start(self):
        LOGGER.info('Started Blue Iris NodeServer for v2 NodeServer version %s', str(VERSION))
        try:
            if 'host' in self.polyConfig['customParams']:
                self.host = self.polyConfig['customParams']['host']
            else:
                self.host = ""

            if 'user' in self.polyConfig['customParams']:
                self.user = self.polyConfig['customParams']['user']
            else:
                self.user = ""

            if 'password' in self.polyConfig['customParams']:
                self.password = self.polyConfig['customParams']['password']
            else:
                self.password = ""

            if 'port' in self.polyConfig['customParams']:
                self.port = self.polyConfig['customParams']['port']
            else:
                self.port =  ""

            if self.host == "" or self.port =="" or self.user == "" or self.password == "":
                LOGGER.error('Blue Iris requires \'host\', \'port\', \'user\', and \'password\' parameters to be specified in custom configuration.')
                return False
            else:
                if self.connect(): 
                    self.discover()
        except Exception as ex:
            LOGGER.error('Error starting Blue Iris NodeServer: %s', str(ex))

    def connect(self):
        try:
            LOGGER.info('Connecting to Blue Iris host %s', str(self.host))
            self.url = "http://" + self.host + ":" + self.port + "/json"

            #Retrieve session ID from Blue Iris Server
            r = requests.post(self.url, data=json.dumps({"cmd":"login"}))
            if r.status_code != 200:
                LOGGER.error('Error establishing connection to Blue Iris, status code: %s', str(r.status.code))
                return False
            self.session = r.json()["session"]

            #Log into Blue Iris Server using username, password, and session ID obtained earlier.
            _data = ("%s:%s:%s" % (self.user, self.session, self.password)).encode('utf-8')
            self.loginHash = hashlib.md5(_data).hexdigest()
            r = requests.post(self.url, data=json.dumps({"cmd":"login", "session": self.session, "response": self.loginHash}))
            LOGGER.debug("Initializing Blue Iris Connection, session: %s", str(self.session))
            if r.status_code != 200 or r.json()["result"] != "success":
                LOGGER.error('Error logging into Blue Iris Server: %s', str(r.text))
                return False

            #Get System Name:
            self.system_name = r.json()["data"]["system name"]
            LOGGER.info('Connected to %s', str(self.system_name))
            return True

        except Exception as ex:
            LOGGER.error('Error connecting to Blue Iris Server, host: %s.  %s', str(self.host), str(ex))
            return False

    def fillPanels(self, command):
        self.reportDrivers()

    def shortPoll(self):
        if not self.initialized or not self.hostup: return False #ensure discovery is completed and host is up before polling
        try:
            self.cameras = self.cmd("camlist")
            for node in self.nodes:
                self.nodes[node].query()
        except Exception as ex:
            LOGGER.error('Error processing shortPoll for %s: %s', self.name, str(ex))
            
    def longPoll(self):
        if not self.initialized: return False #ensure discovery is completed before polling.
        response = os.system("ping -c 1 " + self.host)
        if response == 0:
            self.hostup = True
            self.setDriver('GV3',1)
            self.reportDrivers()
        else:
            LOGGER.info('The Blue Iris computer is Down')
            self.setDriver('GV3',0)
            self.hostup = False

    def query(self, command=None):
        try:
            _status = self.cmd("status")
            self.setDriver('GV1',_status["signal"])
            self.setDriver('GV2',_status["profile"])
            self.setDriver('GV3',int(self.hostup))
        except Exception as ex:
            LOGGER.error('Error querying Blue Iris %s', self.name)

    def discover(self, *args, **kwargs):
        LOGGER.debug('Beginning Discovery on %s', str(self.name))
        self.setDriver('GV3',1)
        try:
            self.cameras = self.cmd("camlist")
            for cam in self.cameras:
                if 'ptz' in cam: #If there is not a 'ptz' element for this item, it's not a camera
                    _shortName = cam['optionValue']
                    _address = _shortName.lower() #ISY address must be lower case but Blue Iris requires the name to be passed in the same case as it is defined so b$
                    _name = cam['optionDisplay']
                    if _address not in self.nodes and _name[0] != '+': #if the name starts with '+', it's not a camera
                        if cam['ptz']:
                            self.addNode(camNodePTZ(self, self.address, _address, _name, _shortName))
                        else:
                            self.addNode(camNode(self, self.address, _address, _name, _shortName))
            self.initialized = True
            return True
        except Exception as ex:
            LOGGER.error('Error discovering cameras on Blue-Iris: %s', str(ex))
            return False

    def delete(self):
        LOGGER.info('Deleting Blue Iris controller')

    def cmd(self, cmd, params=dict()):
        try:
            #LOGGER.debug('Sending command to Blue Iris, cmd: %s, params: %s', str(cmd), str(params))
            args = {"session": self.session, "response": self.loginHash, "cmd": cmd}
            args.update(params)
            r = requests.post(self.url, data=json.dumps(args))

            # if r.status_code != 200 or r.json()["result"] != "success":
            if r.status_code != 200:
                LOGGER.error('Error sending command to Blue Iris, status code: %s: %s', str(r.status_code), str(r.text))

            _response = r.json()
            #LOGGER.debug('Blue Iris Command Response: %s', str(_response))
            if 'data' in _response:
                self.tries = 0
                return _response["data"]
            elif 'session' in _response and 'result' in _response:
                if _response['result'] == 'fail' and self.tries <= 2:
                    self.tries += 1
                    if self.connect():
                        return self.cmd(cmd, params) #retry this command after re-connecting
                else:
                    self.tries = 0
                    return True
            else:
                self.tries = 0
                return True
        except Exception as ex:
            LOGGER.error('Error sending command to Blue Iris: %s', str(ex))
            return False

    def setState(self, command = None):
        try:
            LOGGER.info('Command received to set Blue Iris Server State: %s', str(command))
            _state = int(command.get('value'))
            if _state >=0 and _state <=2:
                self.cmd("status",{"signal":_state})
                return True
            else:
                LOGGER.error('Commanded state must be between 0 and 2 but received %i', _state)
                return False
        except Exception as ex:
            LOGGER.error('Error setting state of Blue Iris Server: %s', str(ex))
            return False

    def setProfile(self, command = None):
        try:
            LOGGER.info('Command received to set Blue iris Profile: %s', str(command))
            _profile = int(command.get('value'))
            if _profile >= 0 and _profile <= 7:
                self.cmd("status",{"profile":_profile})
                return True
            else:
                LOGGER.error('Commanded profile must be between 0 and 7 but received %i', _profile)
                return False
        except Exception as ex:
            LOGGER.error('Error setting profile of Blue Iris Server: %s', str(ex))
            return False

    id = 'controller'
    commands = {'DISCOVER': discover, 'UPDATE': fillPanels, 'SET_STATE': setState, 'SET_PROFILE': setProfile}
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2}, #Polyglot connection status
                {'driver': 'GV1', 'value': 1, 'uom': 25}, #Blue Iris Server Status (0=red, 1=green, 2=yellow)
                {'driver': 'GV2', 'value': 1, 'uom': 56}, #Blue Iris Profile
                {'driver': 'GV3', 'value': 1, 'uom':2} #Host ping status
                ] 

class camNode(polyinterface.Node):
    def __init__(self, controller, primary, address, name, shortName):
        super().__init__(controller, primary, address, name)
        self.shortName = shortName

    def start(self):
        self.query()

    def trigger(self, command):
        LOGGER.info('Triggering camera: %s', str(self.name))
        self.parent.cmd("trigger", {"camera": self.shortName})
        #TODO: Admin access required for this command, add check that it completed successfully

    def pause(self, command):
        LOGGER.info('Pausing camera: %s', str(self.name))
        self.parent.cmd("camconfig", {"camera": self.shortName, "pause":-1})

    def unpause(self, command):
        LOGGER.info('Un-Pausing camera: %s', str(self.name))
        self.parent.cmd("camconfig", {"camera": self.shortName, "pause":0})

    def enable(self, command):
        LOGGER.info('Enable camera: %s', str(self.name))
        self.parent.cmd("camconfig", {"camera": self.shortName, "enable": True})

    def disable(self, command):
        LOGGER.info('disabling camera: %s', str(self.name))
        self.parent.cmd("camconfig", {"camera": self.shortName, "enable": False})

    def fillPanels(self, command):
        self.reportDrivers()

    def query(self, command=None):
        try:
            for cam in self.parent.cameras:
                if cam['optionValue'] == self.shortName:
                    _cam = cam
                    break
        except Exception as ex:
            LOGGER.error('Error querying %s: %s', self.address, str(ex))
            return False
            
        try:
            self.setDriver('ST', int(_cam["isTriggered"]))
            self.setDriver('GV1', int(_cam["isEnabled"]))
            _connected = _cam["isOnline"] and not _cam["isNoSignal"]
            self.setDriver('GV2', int(_connected))
            self.setDriver('GV3', int(_cam["isMotion"]))
            self.setDriver('GV4', int(_cam["isAlerting"]))
            self.setDriver('GV5', int(_cam["isPaused"]))
            self.setDriver('GV6', int(_cam["isRecording"]))
            self.setDriver('GV7', _cam["profile"])
        except Exception as ex:
            LOGGER.error('Error querying %s: %s', self.name, str(ex))
            return False

    def ptz(self, command=None):
        try:
            if command is None:
                LOGGER.error('No command passed for PTZ on camera: %s', self.address)
                return False
            LOGGER.debug('Processing PTZ command for camera %s: %s', self.name, str(command))
            _cmd = command.get('cmd').lower()
            _value = int(command.get('value'))
            if _cmd =='ptz':
                LOGGER.info('Processing PTZ command for camera %s', self.name)
                self.parent.cmd("ptz",{"camera":self.shortName, "button":_value})
            elif _cmd == 'position':
                LOGGER.info('Processing Position command for camera %s', self.name)
                self.parent.cmd("ptz",{"camera":self.shortName, "button":(_value + 100)})
            elif _cmd == 'ir':
                LOGGER.info('Processing IR command for camera %s', self.name)
                self.parent.cmd("ptz",{"camera":self.shortName, "button":(_value + 34)})

        except Exception as ex:
            LOGGER.error('Error processing PTZ command for %s: %s', self.name, str(ex))    
            
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}, #Triggered, true or false
               {'driver': 'GV1', 'value':0, 'uom': 2}, #Enabled, true or false
               {'driver': 'GV2', 'value':0, 'uom': 2}, #Connected (online and signal present), true or false
               {'driver': 'GV3', 'value':0, 'uom': 2}, #Motion Detected, true or false
               {'driver': 'GV4', 'value':0, 'uom': 2}, #Alert Active, true or false
               {'driver': 'GV5', 'value':0, 'uom': 2}, #Paused, true or false
               {'driver': 'GV6', 'value':0, 'uom': 2}, #Recording, true or false
               {'driver': 'GV7', 'value':0, 'uom': 56} #Profile number
               ]
    id = 'camNode'
    commands = {
                    'DON': trigger, 'PAUSE': pause, 'CONTINUE': unpause,
                    'ENABLE': enable, 'DISABLE': disable, 'UPDATE': fillPanels,
                    'IR':ptz
                }

class camNodePTZ(camNode):
    def __init__(self, controller, primary, address, name, shortName):
        super().__init__(controller, primary, address, name, shortName)

    def start(self):
        super().start()

    def trigger(self, command):
        super().trigger(command)

    def pause(self, command):
        super().pause(command)

    def unpause(self, command):
        super().unpause(command)

    def enable(self, command):
        super().enable(command)

    def disable(self, command):
        super().disable(command)

    def query(self, command=None):
        super().query(command)

    def ptz(self, command=None):
        super().ptz(command)

    def fillPanels(self,command):
        self.reportDrivers()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}, #Triggered, true or false
               {'driver': 'GV1', 'value':0, 'uom': 2}, #Enabled, true or false
               {'driver': 'GV2', 'value':0, 'uom': 2}, #Connected (online and signal present), true or false
               {'driver': 'GV3', 'value':0, 'uom': 2}, #Motion Detected, true or false
               {'driver': 'GV4', 'value':0, 'uom': 2}, #Alert Active, true or false
               {'driver': 'GV5', 'value':0, 'uom': 2}, #Paused, true or false
               {'driver': 'GV6', 'value':0, 'uom': 2}, #Recording, true or false
               {'driver': 'GV7', 'value':0, 'uom': 56} #Profile number
               ]
    id = 'camNodePTZ'
    commands = {
                    'DON': trigger, 'PAUSE': pause, 'CONTINUE': unpause, 
                    'ENABLE': enable, 'DISABLE': disable, 'UPDATE': fillPanels, 'PTZ':ptz, 
                    'IR':ptz, 'POSITION':ptz
                }
                
if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('BlueIrisNodeServer')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)   

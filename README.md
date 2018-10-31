# Blue Iris Polyglot
This is the Blue Iris Node Server for the ISY Polyglot V2 interface.  
(c) fahrer16 aka Brian Feeney.  
MIT license. 

Blue Iris uses a JSON API documented in the software's help file.  See the Blue Iris website here: http://blueirissoftware.com/.
The Polyglot v2 Template written by Einstein42 was used as a template: https://github.com/Einstein42/udi-polyglot-interface
The Blue Iris python project developed by magapp was used as an example for utilizing the Blue Iris JSON API: https://github.com/magapp/blueiriscmd
This node server will import cameras as ISY Nodes, continuously poll for new events, and allow for commands to be issued to cameras.


# Installation Instructions:
1. Backup ISY (just in case)
2. Install the node from the Polyglot v2 Node Store or clone this github repo into the /.polyglot/nodeservers folder for the user that runs polyglot v2:
`Assuming you're logged in as the user that runs polyglot, cd cd ~/.polyglot/nodeservers
`git clone https://github.com/fahrer16/udi-blue-iris-poly.git
3. Install pre-requisites using install.sh script
  * 'chmod +x ./install.sh
  * 'install.sh
4. Add Node Server into Polyglot instance.
  * Follow instructions here, starting with "Open Polyglot": https://github.com/Einstein42/udi-polyglotv2/wiki/Creating-a-NodeServer   

## Polyglot Custom Configuration Parameters
* REQUIRED: Key:'host' Value: The IP address or host name of the Blue Iris server.  If port 80 is not used, add the port into the host value. i.e. "192.168.1.100:81", "BlueIrisServer:90", etc...
* REQUIRED: Key:'user' Value: The Blue Iris user name to be used when connecting to Blue Iris.  This user will need to have administrator access in order to be able to trigger cameras.
* REQUIRED: Key:'password' Value: The password of the Blue Iris user.
* REQUIRED: Key:'hostip' Value: The ip address of the host computer in quotations. i.e. "192.168.1.100"
 
## Version History:
* 1.0.0: Initial Release
* 1.0.1: Corrected "bool" editor in profile
* 1.1.0: Added command to set server profile


import octoprint.plugin
import flask

class HoleCommandAPIPlugin(octoprint.plugin.SimpleApiPlugin):
    
    # Store coordinates extracted from @hole command
    def __init__(self):
        self.coordinates = None
        self.layerheight = None

    # Handle the custom @hole AT command
    def custom_atcommand_handler(self, comm, phase, command, parameters, tags=None, *args, **kwargs):
        if command != "hole":
            return
        if tags is None:
            tags = set()
        coords = parameters.split()
        if len(coords) < 2 or (len(coords) % 2 != 0):
            print("Invalid @hole command. Correct usage: @hole x1 y1 x2 y2")
            self._logger.info("Invalid @hole command. Correct usage: @hole x1 y1 x2 y2")
            return
        
        # Extract coordinates from the parameters
        try:
            coords_list = list(map(float, coords))
            # Create pairs of coordinates
            coordinate_pairs = []
            for i in range(0, len(coords_list), 2):
                    coordinate_pairs.append((coords_list[i], coords_list[i + 1]))

            
            # Convert each 2D pair into a 3D coordinate by appending the Z-value
            z_value = comm._currentZ
            coordinates3d = [(x, y, z_value) for x, y in coordinate_pairs]
            self.coordinates = coordinates3d
            self._logger.info(f"Extracted coordinates from @hole command: {self.coordinates}")
            #once extracted successfully, we tell printer to pause
            #comm.setPause(True, tags=tags)
            #move bed forward backward
            comm.sendCommand('G91')
            comm.sendCommand('G1 Z10')
            comm.sendCommand('G90')
            comm.sendCommand('G0 Y220')
            comm.sendCommand('@pause')
        except ValueError:
            self._logger.error("Failed to extract coordinates from @hole command")

    # API GET request handling
    def on_api_get(self, request):
        # Return the coordinates if set, or a default response
        if self.coordinates:
            return flask.jsonify(coordinates=self.coordinates)
        else:
            return flask.jsonify(message="No coordinates set")


    
__plugin_name__ = "Hole Command API Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    plugin = HoleCommandAPIPlugin()


    global __plugin_implementation__ 
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ =  {"octoprint.comm.protocol.atcommand.queuing": plugin.custom_atcommand_handler}
import octoprint.plugin
import flask

class InsituCommandAPIPlugin(octoprint.plugin.SimpleApiPlugin):
    
    # Store coordinates and command type
    def __init__(self):
        self.coordinates = None
        self.command_type = None

    # Handle the custom @magnet or @insert AT commands
    def custom_atcommand_handler(self, comm, phase, command, parameters, tags=None, *args, **kwargs):
        if command not in ["magnet", "insert"]:
            return
        if tags is None:
            tags = set()

        # Set command_type depending on the command received
        if command == "magnet":
            self.command_type = "magnet"
        elif command == "insert":
            self.command_type = "insert"
        
        coords = parameters.split()
        if len(coords) < 2 or (len(coords) % 2 != 0):
            print("Invalid command. Correct usage: @magnet x1 y1 x2 y2 or @insert x1 y1 x2 y2")
            self._logger.info("Invalid command. Correct usage: @magnet x1 y1 x2 y2 or @insert x1 y1 x2 y2")
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
            self._logger.info(f"Extracted coordinates from @{self.command_type} command: {self.coordinates}")
            # Once extracted successfully, we tell the printer to pause
            comm.sendCommand('G91')
            comm.sendCommand('G1 Z10')
            comm.sendCommand('G90')
            comm.sendCommand('G0 Y220') #hardcoded, can we get this from somewhere?
            comm.sendCommand('@pause')
        except ValueError:
            self._logger.error(f"Failed to extract coordinates from @{self.command_type} command")

    # API GET request handling
    def on_api_get(self, request):
        # Return the coordinates and command type if set, or a default response
        if self.coordinates and self.command_type:
            return flask.jsonify(coordinates=self.coordinates, type=self.command_type)
        else:
            return flask.jsonify(message="No coordinates set or command type specified")


__plugin_name__ = "Magnet Insert API Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    plugin = InsituCommandAPIPlugin()

    global __plugin_implementation__ 
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ =  {"octoprint.comm.protocol.atcommand.queuing": plugin.custom_atcommand_handler}

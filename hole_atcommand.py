# coding=utf-8

import logging


def custom_atcommand_handler(comm, phase, command, parameters, tags=None, *args, **kwargs):
    if command != "hole":
        return

    if tags is None:
        tags = set()

    # Split parameters to get coordinates
    coords = parameters.split()
    if len(coords) < 2 or (len(coords) % 2 != 0):
        logging.info("Invalid @hole command. Correct usage: @hole x1 y1 x2 y2")
        return
    try:
        coords_list = list(map(float, coords))
        # Create pairs of coordinates
        coordinate_pairs = []
        for i in range(0, len(coords_list), 2):
                coordinate_pairs.append((coords_list[i], coords_list[i + 1]))
    except ValueError:
        logging.info("Invalid coordinates. Make sure to provide pairs of numerical values.")
        return


    if "script:afterPrintPaused" in tags:
        # This makes sure we don't run into an infinite loop if the user included @wait in the afterPrintPaused
        # GCODE script for whatever reason
        return

    comm.setPause(True, tags=tags)

__plugin_name__ = "Custom @ command"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.comm.protocol.atcommand.queuing": custom_atcommand_handler}

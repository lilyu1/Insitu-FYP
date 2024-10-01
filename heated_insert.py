import requests, time
import asyncio
from asyncua import Client, Node, ua
import datetime
import json
import aiohttp  # Import aiohttp for asynchronous HTTP requests

async def main():
    # ~~params~~
    apikey = '?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    IPadd = '172.32.1.210'
    # API addresses for OctoPi
    urlPrinter = 'http://'+IPadd+':5000/api/printer'  # General Printer Info
    urlJob = 'http://'+IPadd+':5000/api/job'  # Job Control
    urlHole = 'http://'+IPadd+':5000/api/plugin/holeCommandAPIplugin'
    urlHead = 'http://'+IPadd+':5000/api/printer/printhead'  # Printhead control (Jogging)
    urlTool = 'http://'+IPadd+':5000/api/printer/tool'  # Tool control (temperature)
    opcurl = 'opc.tcp://172.32.1.236:4840'
    nP = 3
    nodeStr = 'ns=2'+str(nP)+';s=R'+str(nP)
    magNodeStr = 'ns=3;s='
    progID = 75

    # ~~functions~~
    
    async def heat_inserts(session, str_coord, heat_temp=220, extrude_speed=5000, lower_down_speed=100, lower_down_amount=-5, hold_above=13):
        coords = json.loads(str_coord)

        for coord in coords:
            x, y, z = coord
            z = z + hold_above
            print(f'Moving to position: X={x}, Y={y}, Z={z}')

            # Jog the head to each coordinate (wait for each request to finish before moving to the next)
            async with session.post(urlHead + apikey, json={"command": "jog", "x": x, "y": y, "z": z, "absolute": True, "speed": extrude_speed}) as jog_response:
                if jog_response.status == 204:
                    print(f'Successfully jogged to position: X={x}, Y={y}, Z={z}')
                else:
                    print(f'Failed to jog to position: X={x}, Y={y}, Z={z}. Status: {jog_response.status}')
            
            # Lower the extruder
            async with session.post(urlHead + apikey, json={"command": "jog", "x": 0, "y": 0, "z": lower_down_amount, "absolute": False, "speed": lower_down_speed}) as lower_response:
                if lower_response.status == 204:
                    print(f'Successfully lowered extruder by {lower_down_amount} mm')
                else:
                    print(f'Failed to lower extruder. Status: {lower_response.status}')

            # Wait before moving to the next hole
            await asyncio.sleep(2)

    # Tell the robot to start
    async with Client(url=opcurl) as client:   
        print(f'getting nodes')
        # 1. Read values by getting node
        try:
            NODE_Pc_ProgID = client.get_node(nodeStr+'c_ProgID')
            NODE_Pc_Start = client.get_node(nodeStr+'c_Start')  # true or false
        except:
            print("Error: Node Definition")

        # Using aiohttp session for async HTTP calls
        async with aiohttp.ClientSession() as session:
            str_coord = '[[125,105,15]]'
            await heat_inserts(session, str_coord)

            # Optionally, continue with other steps such as printer_resume
            # await printer_resume()

if __name__ == '__main__':
    asyncio.run(main())

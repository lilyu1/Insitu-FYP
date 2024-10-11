import requests, time
import asyncio
from asyncua import Client, Node, ua
import datetime
import json
import aiohttp  # Import aiohttp for asynchronous HTTP requests

async def main():
    # ~~params~~
    #printerurl = 'http://172.32.1.210:5000/api/printer?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    apikey = '?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    IPadd = '172.32.1.210'
    # api addresses for octopi
    urlPrinter = 'http://'+IPadd+':5000/api/printer' # General Printer Info
    urlJob = 'http://'+IPadd+':5000/api/job' # Job Control
    urlHole = 'http://'+IPadd+':5000/api/plugin/insituCommandAPIplugin'
    urlHead = 'http://'+IPadd+':5000/api/printer/printhead'  # Printhead control (Jogging)
    urlTool = 'http://'+IPadd+':5000/api/printer/tool'   # Tool contorl (temperature)
    urlBed = 'http://'+IPadd+':5000/api/printer/bed' 
    opcurl = 'opc.tcp://172.32.1.236:4840'
    nP = 3
    nodeStr = 'ns=2'+str(nP)+';s=R'+str(nP)
    magNodeStr = 'ns=3;s='

    #program IDs
    magnet_ProgID = 75
    insert_ProgID = 76



    # ~~functions~~
    

    #polls printer pause
    async def polling_printer_pause():
        paused_flag = False
        while not paused_flag: #while printing
            now = datetime.datetime.now()
            print(f'polling {now}')
            try:
                response = requests.get(urlPrinter+apikey)
                printer_info = response.json()
                #print(printer_info)
                paused_flag = printer_info['state']['flags']['pausing'] #true or false
                print(paused_flag)
                await asyncio.sleep(1) #poll every 1 sec

                if paused_flag:
                    # # get hole coordinates from holecommandapi plugin
                    num_holes, str_coord, hole_type = await get_hole_info()
                    #returns 0,0,0 if error retrieving hole info
                    if num_holes == 0:
                        paused_flag = False #continue polling

            except:
                print('error with printer')
                print(printer_info)
            
        print('i have broken out - printer has paused due to plugin')
        return num_holes, str_coord, hole_type

    #update opcua control

    async def OPCUA_GetValue():
                try:
                    Pc_ProgID = await NODE_Pc_ProgID.get_value()
                    # print(Pc_ProgID)
                    # print(type(Pc_ProgID))
                    Pc_Start = await NODE_Pc_Start.get_value()
                    # print(Pc_Start)
                    # print(type(Pc_Start))

                    return Pc_ProgID, Pc_Start
                    
                except:
                    print("Error: OPCUA Reading Control Variables")

    async def robot_startprog(progID):
        print(f'setting node values to start program')
        Pc_ProgID = progID
        Pc_Start = True

        await NODE_Pc_ProgID.set_value(Pc_ProgID,ua.VariantType.Int32)
        print(f'prog id={progID} sent')
        await NODE_Pc_Start.set_value(Pc_Start,ua.VariantType.Boolean)
        print('start=true sent')


    async def robot_reset_prog():
        print(f'setting node values to off before program')
        Pc_ProgID = 0
        Pc_Start = False

        await NODE_Pc_ProgID.set_value(Pc_ProgID,ua.VariantType.Int32)
        print('prog id=0 sent')
        await NODE_Pc_Start.set_value(Pc_Start,ua.VariantType.Boolean)
        print('start=false sent')

    async def printer_resume():
        print('resume print via api')
        #check if robot has stopped moving
        robot_ready = False
        while not robot_ready:
            print('printer not ready to continue')
            progID, start = await OPCUA_GetValue()
            if progID == 0 and start == False:
                robot_ready = True
            await asyncio.sleep(1) #poll every 1 sec

        print('robot is clear (?), resume print')
        request = requests.post(urlJob+apikey,json={"command": "pause","action": "resume"})

    async def get_hole_info():
        try:
            print('getting coords from custom API. ')
            response_get = requests.get(urlHole+apikey)
            print(response_get.json())
            hole_type = response_get.json()['type']
            json_coords = response_get.json()['coordinates']
            print("coordinates ofc holes:", json_coords) #[[123,456,2],[111,222,2]]
            str_coord = str(json_coords)
            num_holes = len(eval(str_coord))
            return num_holes, str_coord, hole_type
        except:
            print("Error: Getting Hole Info")
            return 0,0,0
    
    async def send_coordinates_to_opcua(client, write_magCount, write_magInfo):
        print('sending coordinates to OPCUA. info to be sent: ')
        print(write_magCount, write_magInfo)
        print(type(write_magCount), type(write_magInfo))
        try:
            NODE_magCount = client.get_node(magNodeStr+'magCount')
            NODE_magInfo = client.get_node(magNodeStr+'magInfo')
        except:
            print("Error: Node Definition")

        # Set the values on the OPC UA server
        await NODE_magCount.set_value(write_magCount,ua.VariantType.Int32)
        print('magCount sent') #this works
        await NODE_magInfo.set_value(write_magInfo,ua.VariantType.String)
        print('magInfo sent')

    # ~~functions~~





    async def heat_inserts(session, str_coord, heat_temp=220, bed_temp=60, extrude_speed=5000, lower_down_speed=2, lower_down_amount=-6.2, hold_above=13):
        coords = json.loads(str_coord)

        # 1. Heat up the extruder and bed
        async with session.post(urlTool + apikey, json={"command": "target", "targets": {"tool0": heat_temp}}) as heat_response:
            if heat_response.status == 204:
                print(f'Heating up extruder to {heat_temp}°C')
            else:
                print(f'Failed to start heating extruder to {heat_temp}°C')

        async with session.post(urlBed + apikey, json={"command": "target", "target": bed_temp}) as bed_response:
            if bed_response.status == 204:
                print(f'Heating up bed to {bed_temp}°C')
            else:
                print(f'Failed to start heating bed to {bed_temp}°C')

        # 2. Poll for both extruder and bed temperatures until they reach their target values
        while True:
            async with session.get(urlPrinter + apikey) as temp_response:
                if temp_response.status == 200:
                    printer_data = await temp_response.json()
                    current_extruder_temp = printer_data['temperature']['tool0']['actual']
                    current_bed_temp = printer_data['temperature']['bed']['actual']
                    print(f'Current extruder temperature: {current_extruder_temp}°C')
                    print(f'Current bed temperature: {current_bed_temp}°C')

                    if current_extruder_temp >= heat_temp and current_bed_temp >= bed_temp:
                        print(f'Extruder heated to {heat_temp}°C and bed heated to {bed_temp}°C')
                        break  # Exit the loop and move to the next command
                else:
                    print(f'Failed to get temperatures. Status: {temp_response.status}')
                
            await asyncio.sleep(1)  # Wait 1 second before polling again

        # 3. Proceed with insert operations once heated
        for coord in coords:
            x, y, z = coord
            print(f'Moving to position: X={x}, Y={y}, Z={z+hold_above}')

            # Jog above hole
            async with session.post(urlHead + apikey, json={"command": "jog", "x": x, "y": y, "z": z+hold_above, "absolute": True, "speed": extrude_speed}) as jog_response:
                if jog_response.status == 204:
                    print(f'Successfully jogged to position: X={x}, Y={y}, Z={z+hold_above}')
                else:
                    print(f'Failed to jog to position: X={x}, Y={y}, Z={z+hold_above}. Status: {jog_response.status}')

            # Jog down to hole
            async with session.post(urlHead + apikey, json={"command": "jog", "x": x, "y": y, "z": z, "absolute": True, "speed": extrude_speed}) as jog_response:
                if jog_response.status == 204:
                    print(f'Successfully jogged to position: X={x}, Y={y}, Z={z}')
                else:
                    print(f'Failed to jog to position: X={x}, Y={y}, Z={z}. Status: {jog_response.status}')

            await asyncio.sleep(10)  # Wait for 5 seconds above insert

            # Lower the extruder
            async with session.post(urlHead + apikey, json={"command": "jog", "x": 0, "y": 0, "z": lower_down_amount, "absolute": False, "speed": lower_down_speed}) as lower_response:
                if lower_response.status == 204:
                    print(f'Successfully lowered extruder by {lower_down_amount} mm')
                else:
                    print(f'Failed to lower extruder. Status: {lower_response.status}')

            # Wait before moving to the next hole
            await asyncio.sleep(2)

            # Jog back above hole
            async with session.post(urlHead + apikey, json={"command": "jog", "x": 0, "y": 0, "z": -lower_down_amount + hold_above, "absolute": False, "speed": extrude_speed}) as jog_response:
                if jog_response.status == 204:
                    print(f'Successfully jogged to position: X={x}, Y={y}, Z={-lower_down_amount + hold_above}')
                else:
                    print(f'Failed to jog to position: X={x}, Y={y}, Z={-lower_down_amount + hold_above}. Status: {jog_response.status}')

            print('pulling up complete')

        async with session.post(urlHead + apikey, json={"command": "jog", "x": 0, "y": 0, "z": 50, "absolute": False, "speed": extrude_speed}) as jog_response:
            if jog_response.status == 204:
                print(f'Successfully jogged to position: X={x}, Y={y}, Z={-lower_down_amount + hold_above}')
            else:
                print(f'Failed to jog to position: X={x}, Y={y}, Z={-lower_down_amount + hold_above}. Status: {jog_response.status}')

                print('insert ')


    #tell the robot to start
    async with Client(url=opcurl) as client:   
        
        print(f'getting nodes')
        #1. read values by getting node
        try:
            NODE_Pc_ProgID = client.get_node(nodeStr+'c_ProgID')
            NODE_Pc_Start = client.get_node(nodeStr+'c_Start') #true or false
        except:
            print("Error: Node Definition")


        # #2. make sure program is not running
        await robot_reset_prog()

        # #3. waiting for printing to pause triggered by plugin. while loop inside
        num_holes, str_coord, hole_type = await polling_printer_pause()
        # # send to opcua server
        await send_coordinates_to_opcua(client, num_holes, str_coord)

        # #3. change the values by using set value. 75 for magnet.
        if hole_type == "magnet":
            await robot_startprog(magnet_ProgID)


        elif hole_type == "ïnsert":
            await robot_startprog(insert_ProgID)
            # Using aiohttp session for async HTTP calls
            async with aiohttp.ClientSession() as session:
                await heat_inserts(session, str_coord)

        # Continue with other steps such as printer_resume
        await printer_resume()


        


         

    
if __name__ == '__main__':
    asyncio.run(main())
    

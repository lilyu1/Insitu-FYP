import requests, time
import asyncio
from asyncua import Client, Node, ua, ua_client
import datetime
import json

async def main():
    # ~~params~~
    #printerurl = 'http://172.32.1.210:5000/api/printer?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    apikey = '?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    IPadd = '172.32.1.210'
    # api addresses for octopi
    urlPrinter = 'http://'+IPadd+':5000/api/printer' # General Printer Info
    urlJob = 'http://'+IPadd+':5000/api/job' # Job Control
    urlHole = 'http://'+IPadd+':5000/api/plugin/holeCommandAPIplugin'
    urlHead = 'http://'+IPadd+':5000/api/printer/printhead'  # Printhead control (Jogging)
    urlTool = 'http://'+IPadd+':5000/api/printer/tool'   # Tool contorl (temperature)
    opcurl = 'opc.tcp://172.32.1.236:4840'
    nP = 3
    nodeStr = 'ns=2'+str(nP)+';s=R'+str(nP)
    magNodeStr = 'ns=3;s='
    progID = 75

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
            except:
                print('error with printer')
                print(printer_info)
            
        print('i have broken out - printer has paused')
    #update opcua control

    async def OPCUA_GetValue():
                try:
                    Pc_ProgID = await NODE_Pc_ProgID.get_value()
                    print(Pc_ProgID)
                    print(type(Pc_ProgID))
                    Pc_Start = await NODE_Pc_Start.get_value()
                    print(Pc_Start)
                    print(type(Pc_Start))

                    return Pc_ProgID, Pc_Start
                    
                except:
                    print("Error: OPCUA Reading Control Variables")

    async def robot_startprog():
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
            progID, start = await OPCUA_GetValue()
            if progID == 0 and start == False:
                robot_ready = True

        print('robot is clear (?), resume print')
        request = requests.post(urlJob+apikey,json={"command": "pause","action": "resume"})

    async def get_hole_coords():
        response_get = requests.get(f'{urlHole}?apikey={apikey}')
        json_coords = response_get.json()['coordinates']
        print("coordinates of holes:", json_coords) #[[123,456,2],[111,222,2]]
        str_coord = str(json_coords)
        num_holes = len(eval(str_coord))
        return num_holes, str_coord
    
    async def send_coordinates_to_opcua(client, write_magCount, write_magInfo):

        try:
            NODE_magCount = client.get_node(magNodeStr+'magCount')
            NODE_magInfo = client.get_node(nodeStr+'magInfo')
        except:
            print("Error: Node Definition")
                
        # Set the values on the OPC UA server
        await NODE_magCount.set_value(write_magCount,ua.VariantType.Int32)
        print('magCount sent')
        await NODE_magInfo.set_value(write_magInfo,ua.VariantType.String)
        print('magInfo sent')

    def heat_inserts(str_coord, heat_temp=220, extrude_speed=5000, lower_down_speed=100, lower_down_amount=-5):
        coords = json.loads(str_coord)
        
        for coord in coords:
            x, y, z = coord
            print(f'Moving to position: X={x}, Y={y}, Z={z}')

            # Jog the head to each coordinate
            jog_response = requests.post(urlHead + apikey, json={"command": "jog", "x": x, "y": y, "z": z, "absolute": False, "speed": extrude_speed})
            if jog_response.status_code == 200:
                print(f'Jogged to position: X={x}, Y={y}, Z={z}')
            else:
                print(f'Failed to jog to position: X={x}, Y={y}, Z={z}')

            # Heat up the extruder
            heat_response = requests.post(urlTool + apikey, json={"command": "target", "targets": {"tool0": heat_temp}})
            if heat_response.status_code == 200:
                print(f'Heating up extruder to {heat_temp}°C')
            else:
                print(f'Failed to heat extruder to {heat_temp}°C')

            # Wait until the temperature is reached
            time.sleep(5)

            # Lower the extruder
            lower_response = requests.post(urlHead + apikey, json={"command": "jog", "x": 0, "y": 0, "z": lower_down_amount, "absolute": False, "speed": lower_down_speed})
            if lower_response.status_code == 200:
                print(f'Lowered extruder by {lower_down_amount} mm')
            else:
                print(f'Failed to lower extruder')

            # Wait before moving to the next hole
            time.sleep(2)



    #tell the robot to start
    async with Client(url=opcurl) as client:   
        
        print(f'getting nodes')
        #1. read values by getting node
        try:
            NODE_Pc_ProgID = client.get_node(nodeStr+'c_ProgID')
            NODE_Pc_Start = client.get_node(nodeStr+'c_Start') #true or false
        except:
            print("Error: Node Definition")


        #2. make sure program is not running
        await robot_reset_prog()

        #3. waiting for printing to pause. while loop inside
        await polling_printer_pause()

        # get hole coordinates from holecommandapi plugin
        num_holes, str_coord = await get_hole_coords()

        # send to opcua server
        send_coordinates_to_opcua(client, num_holes, str_coord)

        #3. change the values by using set value
        await robot_startprog()

        #4. move printer to over the coords
        await heat_inserts(str_coord)

        #5 poll for status to check when program is done running then resume
        await printer_resume()
        


         

    
if __name__ == '__main__':
    asyncio.run(main())
    

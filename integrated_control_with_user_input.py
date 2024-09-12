import requests, time
import asyncio
from asyncua import Client, Node, ua, ua_client
import datetime

async def main():
    # ~~params~~
    #printerurl = 'http://172.32.1.210:5000/api/printer?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    apikey = '?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
    IPadd = '172.32.1.210'
    # api addresses for octopi
    urlPrinter = 'http://'+IPadd+':5000/api/printer' # General Printer Info
    urlJob = 'http://'+IPadd+':5000/api/job' # Job Control
    urlHole = 'http://'+IPadd+':5000/api/plugin/holeCommandAPIplugin'
    opcurl = 'opc.tcp://172.32.1.236:4840'
    nP = 3
    nodeStr = 'ns=2'+str(nP)+';s=R'+str(nP)
    progID = 74

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
        hole_coords = response_get.json()['coordinates']
        print("coordinates of holes:", hole_coords) #[[123,456,2],[111,222,2]]
        return hole_coords
    
    async def send_coordinates_to_opcua(client, hole_coords):
        for i, (x, y, z) in enumerate(hole_coords):
            try:
                # Assuming you have node definitions for each coordinate (e.g., NODE_Hole_X1, NODE_Hole_Y1, NODE_Hole_Z1, etc.)
                node_x = client.get_node(f"ns=2;i={1000 + i*3}")  # Replace with actual node ID for X
                node_y = client.get_node(f"ns=2;i={1001 + i*3}")  # Replace with actual node ID for Y
                node_z = client.get_node(f"ns=2;i={1002 + i*3}")  # Replace with actual node ID for Z
                
                # Set the values on the OPC UA server
                await node_x.set_value(float(x), ua.VariantType.Float)
                await node_y.set_value(float(y), ua.VariantType.Float)
                await node_z.set_value(float(z), ua.VariantType.Float)

                print(f"Sent coordinates to OPC UA: X={x}, Y={y}, Z={z}")
            except Exception as e:
                print(f"Failed to send coordinates to OPC UA for hole {i+1}: {e}")


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
        hole_coords = await get_hole_coords()

        # send to opcua server


        #3. change the values by using set value
        await robot_startprog()
        #4 poll for status to check when program is done running then resume
        await printer_resume()
        


         

    
if __name__ == '__main__':
    asyncio.run(main())
    

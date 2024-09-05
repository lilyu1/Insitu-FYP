from statemachine import StateMachine, State
from asyncua import Client, Node, ua
import logging
import requests
import time
import asyncio

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')

# class PrinterStateMachine(StateMachine):
#     ###States
#     Init = State('Initialisation', initial=True)
#     ##Operational
#     Operational = State('Operational')
#     def on_enter_Operational(self):
#         global Pd_State
#         Pd_State='Operational'
#     #async def on_exitOperational(self):
#     ##Heating
#     Heating = State('Heating')
#     def on_enter_Heating(self):
#         global Pd_State
#         Pd_State='Heating'
#     #async def on_exitHeating(self):
#     ##Printing
#     Printing = State('Printing')
#     def on_enter_Printing(self):
#         global Pd_State
#         Pd_State='Printing'
#         #async def on_exitPrinting(self):
#     ##Cooldown
#     Cooldown = State('Cooldown')
#     def on_enter_Cooldown(self):
#         global urlHead
#         global apikey
#         req = requests.post(urlHead+apikey,json={"command": "home","axes": ["x","y"]})
#         global Pd_State
#         Pd_State='Cooldown'
#     #async def on_exitCooldown(self):
#     ##Part on Bed 
#     Partonbed = State('Part on Bed')
#     def on_enter_Partonbed(self):
#         global urlHead
#         global apikey
#         req = requests.post(urlHead+apikey,json={"command": "jog","x": 0,"y": 230,"z": 0, "absolute": False, "speed": 3600})
#         global Pd_State
#         Pd_State='Part on Bed'
#     #async def on_exitPartonbed(self):    
#     ##Cleaning Required
#     CleaningRequired = State('Cleaning Required')
#     def on_enter_CleaningRequired(self):
#         global Pd_State
#         Pd_State='Cleaning Required'
#         global urlHead
#         global apikey
#         req = requests.post(urlHead+apikey,json={"command": "jog","x": 0,"y": 0,"z": 20, "absolute": False, "speed": 8000})
#         req = requests.post(urlHead+apikey,json={"command": "home","axes": ["x","y"]}) 
#         req = requests.post(urlHead+apikey,json={"command": "jog","x": 0,"y": 230,"z": 0, "absolute": False, "speed": 8000})
#     #async def on_exitCleaningRequired(self):
#     ##Maintainence
#     Maintainence = State('Maintainence')
#     def on_enter_Maintainence(self):
#         global Pd_State
#         Pd_State='Maintainence'
#     #async def on_exitMaintainence(self):        
    
#     ##TRANSITIONS
#     StartUp = Init.to(Operational)
#     def on_StartUp(self):
#         print('Starting State Machine - Entering Operational')
#     StartPrint = Operational.to(Heating)
#     def on_StartPrint(self):
#         print("STATE: Heating - Print Started")
#     FakeClean = Operational.to(CleaningRequired)
#     MaintainenceMode = Operational.to(Maintainence)
#     def on_MaintainenceMode(self):
#         print("STATE: Maintainence Mode")
#     Heated = Heating.to(Printing)
#     def on_Heated(self):
#         print("STATE: Printing - Heating Complete")
#     CancelHeating = Heating.to(Cooldown)
#     def on_Heated(self):
#         print("STATE: Cooldown - Heating Cancelled")
#     PrintComplete = Printing.to(Cooldown)
#     def on_PrintComplete(self):
#         print("STATE: Cooldown - Printing Complete")
#     PrintCancelled = Printing.to(Cooldown)
#     def on_PrintCancelled(self):
#         print("STATE: Cooldown - Printing Cancelled")
#     CoolEmpty = Cooldown.to(CleaningRequired)
#     def on_CoolEmpty(self):
#         print("STATE: Cleaning Required - Cooldown Complete, No Part on Bed")
#     CoolPart = Cooldown.to(Partonbed)
#     def on_CoolPart(self):
#         print("STATE: Part on Bed - Cooldown Complete, Part to be removed")
#     PartRemoved = Partonbed.to(CleaningRequired)
#     def on_PartRemoved(self):
#         print("STATE: Cleaning Required - Part Removed")
#         global S_partonbed
#         S_partonbed = False
#     Cleaned = CleaningRequired.to(Operational)
#     def on_Cleaned(self):
#         print("STATE: Operational - Bed Cleaned")
#     MaintainenceComplete = Maintainence.to(Operational)
#     def on_MaintainenceComplete(self):
#         print("STATE: Operational - Maintainence Complete")

async def main():
    ### VARIABLES ###
    # Printer INPUTS    
    nP = 2 # CHANGE PRINTER NUMBER HERE
    apikey = '?apikey=69128C636DAA49B3BDB1DF026291059A' # ENTER API KEY HERE
    IPadd = '172.31.1.226' # ENTER IP ADRESS HERE DO NOT USE HOST NAMES!!!

    # Fixed API Addressess
    urlFiles = 'http://'+IPadd+':5000/api/files/local/' # File Information and Selection
    urlJob = 'http://'+IPadd+':5000/api/job' # Job Control
    urlConn = 'http://'+IPadd+':5000/api/connection' # Printer Connection (Currently configured as Automatic)
    urlPrinter = 'http://'+IPadd+':5000/api/printer' # General Printer Info
    urlHead = 'http://'+IPadd+':5000/api/printer/printhead'  # Printhead control (Jogging)
    urlTool = 'http://'+IPadd+':5000/api/printer/tool'   # Tool contorl (temperature)
    urlBed = 'http://'+IPadd+':5000/api/printer/bed' # Bed control (temperature)

    # Initalise State Variables
    S_reset = False # When set to true, it indicates that a reset flag is to be sent, and no new programes can be run. 
    S_partonbed = False # State Flag Indicating part is on bed (assumption, if print is started part is on bed)

    S_RobotPartRemoval = False
    S_RobotCleaning = False

    # Initalise OPC UA Values
    Pc_Start = False
    Pc_ProgID = 0
    Pc_File = 'Default'
    Pc_PartRemoved = False
    Pf_Ready = False
    Pf_End = False
    Pc_BedCleaned = False
    Pc_JogX = 0.0
    Pc_JogY = 0.0
    Pc_JogZ = 0.0
    Pc_JogSpeed = 0.0
    Pc_Feedrate = 0.0
    Pc_tNozTarget = 0.0
    Pc_tNozOffset = 0.0
    Pc_tBedTarget = 0.0
    Pc_tBedOffset = 0.0
    Pc_Extrude = 0.0
    Pd_APIresp = 'Default'
    Pd_tNozTarget = 0.0
    Pd_tNozReal = 0.0
    Pd_tBedTarget = 0.0
    Pd_tBedReal = 0.0
    Pd_JobTimeEst = 0
    Pd_FilaLenEst = 0
    Pd_JobFile = 'Default'
    Pd_JobProgress = 0.0
    Pd_JobTime = 0
    Pd_JobTimeLeft = 0
    Pd_State = 'Default' # State Connected to OPCUA, can be set by Octoprint or overwritten by custom state
    Pd_StateHidden = 'Default' # Octoprint State (not as details), helps determine cstom state changes

    ## Contorl Variables - May conncet to OPCUA later 
    # Variable for exiting cooldown state
    BedTempThreshold = 48 

    # Heating -> Printing State Change Conditions Dependent on materials later
    PreHeatBed = 49.5 
    PreHeatNoz = 199.5

    # Delay variblae used for timings when sending octopi signals
    delay = 0.5

    # Variables for reconnecting to opc ua
    start = time.time()
    ReconnectTime = 1800

    ## OPCUA INPUTS
    urlOPCUA = 'oct.tpc://172.32.1.236:4840/server/' #OPC UA Server Endpoint


    async with Client(url=urlOPCUA) as client:
        # Initalise OPCUA Variables    
        print("Initialising Printer "+str(nP))
        print("Finding all relevant nodes")
        nodeStr = 'ns=1'+str(nP)+';s=P'+str(nP)
        try:
            NODE_Pc_ProgID = client.get_node(nodeStr+'c_ProgID')
            NODE_Pc_Start = client.get_node(nodeStr+'c_Start;')
            NODE_Pf_Ready = client.get_node(nodeStr+'f_Ready;')
            NODE_Pf_End = client.get_node(nodeStr+'f_End;')
            NODE_Pc_File = client.get_node(nodeStr+'c_File;')
            NODE_Pc_PartRemoved = client.get_node(nodeStr+'c_PartRemoved;')
            NODE_Pc_BedCleaned = client.get_node(nodeStr+'c_BedCleaned;')
            NODE_Pc_JogX = client.get_node(nodeStr+'c_JogX;')
            NODE_Pc_JogY = client.get_node(nodeStr+'c_JogY;')
            NODE_Pc_JogZ = client.get_node(nodeStr+'c_JogZ;')
            NODE_Pc_JogSpeed = client.get_node(nodeStr+'c_JogSpeed;')
            NODE_Pc_Feedrate = client.get_node(nodeStr+'c_Feedrate;')
            NODE_Pc_tNozTarget = client.get_node(nodeStr+'c_tNozTarget;')
            NODE_Pc_tNozOffset = client.get_node(nodeStr+'c_tNozOffset;')
            NODE_Pc_tBedTarget = client.get_node(nodeStr+'c_tBedTarget;')
            NODE_Pc_tBedOffset = client.get_node(nodeStr+'c_tBedOffset;')
            NODE_Pc_Extrude = client.get_node(nodeStr+'c_Extrude;')
            NODE_Pd_State = client.get_node(nodeStr+'d_State;')
            NODE_Pd_APIresp = client.get_node(nodeStr+'d_APIresp')
            NODE_Pd_tNozTarget = client.get_node(nodeStr+'d_tNozTarget;')
            NODE_Pd_tNozReal = client.get_node(nodeStr+'d_tNozReal;')
            NODE_Pd_tBedTarget = client.get_node(nodeStr+'d_tBedTarget;')
            NODE_Pd_tBedReal = client.get_node(nodeStr+'d_tBedReal;')
            NODE_Pd_JobTimeEst = client.get_node(nodeStr+'d_JobTimeEst;')
            NODE_Pd_FilaLenEst = client.get_node(nodeStr+'d_FilaLenEst;')
            NODE_Pd_JobFile = client.get_node(nodeStr+'d_JobFile;')
            NODE_Pd_JobProgress = client.get_node(nodeStr+'d_JobProgress;')
            NODE_Pd_JobTime = client.get_node(nodeStr+'d_JobTime;')
            NODE_Pd_JobTimeLeft = client.get_node(nodeStr+'d_JobTimeLeft;')
        except:
            print("Error: Node Definition")

        # Home all axis on startup
        try:    
            print("Homing X and Y")
            req = requests.post(urlHead+apikey,json={"command": "home","axes": ["x","y","z"]})
        except:
            print("Error: Printer Start Up Home X Y")

        ## Main Function Definitions
        async def OPCUA_Reconnect():
            global start
            if (time.time()-start>ReconnectTime):
                start = time.time()
                await client.disconnect()
                await client.connect()

        async def OPCUA_UpdateControl():
            try:
                global Pc_Start
                Pc_Start = await NODE_Pc_Start.get_value()
                global Pc_ProgID
                Pc_ProgID = await NODE_Pc_ProgID.get_value()
                global Pc_File
                Pc_File = await NODE_Pc_File.get_value()
                global Pc_PartRemoved
                Pc_PartRemoved = await NODE_Pc_PartRemoved.get_value()
                global Pc_BedCleaned
                Pc_BedCleaned = await NODE_Pc_BedCleaned.get_value()
            except:
                print("Error: OPCUA Reading Control Variables")
            
        async def OPCUA_UpdateData_Printer():
            try:
                response = requests.get(urlPrinter+apikey)
                printerInfo = response.json()
                global Pf_Ready
                Pf_Ready = printerInfo['state']['flags']['ready']
                await NODE_Pf_Ready.set_value(Pf_Ready,ua.VariantType.Boolean) # Indicate if a signal can be sent
                global Pd_tBedReal    
                Pd_tBedReal = printerInfo['temperature']['bed']['actual']
                await NODE_Pd_tBedReal.set_value(Pd_tBedReal,ua.VariantType.Double)
                global Pd_tBedTarget
                Pd_tBedTarget = printerInfo['temperature']['bed']['target']
                await NODE_Pd_tBedTarget.set_value(Pd_tBedTarget,ua.VariantType.Double)
                global Pd_tNozReal
                Pd_tNozReal = printerInfo['temperature']['tool0']['actual']
                await NODE_Pd_tNozReal.set_value(Pd_tNozReal,ua.VariantType.Double)
                global Pd_tNozTarget
                Pd_tNozTarget = printerInfo['temperature']['tool0']['target']
                await NODE_Pd_tNozTarget.set_value(Pd_tNozTarget,ua.VariantType.Double)
                global Pd_StateHidden
                Pd_StateHidden = printerInfo['state']['text']
            except:
                print("Error: Octopi - Printer General Info Req")

        async def OPCUA_UpdateData_PrintJob():
            # Contitional Update - Only While Printing or Heating
            try:
                response = requests.get(urlJob+apikey)
                jobInfo = response.json()    
                global Pd_JobFile
                Pd_JobFile = jobInfo['job']['file']['name']
                await NODE_Pd_JobFile.set_value(Pd_JobFile,ua.VariantType.String)
                global Pd_JobProgress
                Pd_JobProgress = jobInfo['progress']['completion']
                await NODE_Pd_JobProgress.set_value(Pd_JobProgress,ua.VariantType.Double)
                global Pd_JobTime
                Pd_JobTime = jobInfo['progress']['printTime']
                await NODE_Pd_JobTime.set_value(Pd_JobTime,ua.VariantType.Double)
                global Pd_JobTimeLeft
                Pd_JobTimeLeft = jobInfo['progress']['printTimeLeft']
                await NODE_Pd_JobTimeLeft.set_value(Pd_JobTimeLeft,ua.VariantType.Double)
                global Pd_JobTimeEst
                Pd_JobTimeEst = jobInfo['job']['filament']['tool0']['length']
                await NODE_Pd_JobTimeEst.set_value(Pd_JobTimeEst,ua.VariantType.Double)
                global Pd_FilaLenEst
                Pd_FilaLenEst = jobInfo['job']['estimatedPrintTime']
                await NODE_Pd_FilaLenEst.set_value(Pd_FilaLenEst,ua.VariantType.Double)
            except:
                print("Error: Octopi - Job Info Request during printing/heating")            

        def HoldPrinterPosition():
            req = requests.post(urlHead+apikey,json={"command": "jog","x": 1,"y": 0,"z": 0, "absolute": False, "speed": 5000})
            time.sleep(0.25)
            req = requests.post(urlHead+apikey,json={"command": "jog","x": -1,"y": 0,"z": 0, "absolute": False, "speed": 5000})
            time.sleep(0.25)

        def PRI_BedCleaning():
            req = requests.post(urlHead+apikey,json={"command": "jog","x": 1,"y": 0,"z": 0, "absolute": False, "speed": 5000})
            time.sleep(0.25)
            req = requests.post(urlHead+apikey,json={"command": "jog","x": -1,"y": 0,"z": 0, "absolute": False, "speed": 5000})
            time.sleep(0.25)


        ### STATE MACHINE ###
        PrinterState = PrinterStateMachine()
        PrinterState.StartUp()

        while True: # Main Loop
            await asyncio.sleep(0.2)

            ## STATE MACHINE operations in state 
            ## All States
            OPCUA_UpdateControl() # Everyloop with read new control signals
            OPCUA_UpdateData_Printer() # Everyloop will update passive printer values
            OPCUA_Reconnect() # Everyloop will check if reconnect is needed

            ## Operational
            if (PrinterState.current_state == PrinterState.Operational):
                await NODE_Pd_State.set_value('Printing',ua.VariantType.String)
                # Transition - Handled in Prog 1 Start Print
            ## Heating
            elif (PrinterState.current_state == PrinterState.Heating):
                await NODE_Pd_State.set_value('Heating',ua.VariantType.String)
                # Transition - Cancel handled in Prog 2 Cancel Print
                OPCUA_UpdateData_PrintJob()
                if((Pd_tBedReal>PreHeatBed)and(Pd_tNozReal>PreHeatNoz)):
                    PrinterState.Heated()
                    S_partonbed = True
            # Printing 
            elif (PrinterState.current_state == PrinterState.Printing):
                await NODE_Pd_State.set_value('Printing',ua.VariantType.String)
                # Transition - Cancel handled in Prog 2 Cancel Print
                OPCUA_UpdateData_PrintJob()
                if (Pd_StateHidden=='Operational'):
                    PrinterState.PrintComplete()
            # Cooldown
            elif (PrinterState.current_state == PrinterState.Cooldown):
                await NODE_Pd_State.set_value('Cooldown',ua.VariantType.String)
                if(Pd_tBedReal<BedTempThreshold):
                    if(S_partonbed==True):
                        StateMachine.CoolPart
                    elif(S_partonbed==False):
                        StateMachine.CoolEmpty
            # Part on Bed
            elif (PrinterState.current_state == PrinterState.Partonbed):
                await NODE_Pd_State.set_value('Part on Bed',ua.VariantType.String)
                if(Pc_PartRemoved==True):
                    S_RobotPartRemoval = True
                    HoldPrinterPosition()
                if((Pc_PartRemoved==False)and(S_RobotPartRemoval==True)):
                    S_RobotPartRemoval = False
                    PrinterState.PartRemoved()
            # Cleaning Required
            elif (PrinterState.current_state == PrinterState.CleaningRequired):
                await NODE_Pd_State.set_value('Cleaning Required',ua.VariantType.String)
                if((Pc_PartRemoved==False)and(S_RobotCleaning==True)):
                    S_RobotCleaning = False
                    PrinterState.Cleaned()
                elif(Pc_PartRemoved==True):
                    S_RobotCleaning = True
                    PRI_BedCleaning()
            #Maintainence
            elif (PrinterState.current_state == PrinterState.Maintainence):
                await NODE_Pd_State.set_value('Maintainence',ua.VariantType.String)
            
            ## Main Polling Loop ##
            if (Pc_Start==True)and(S_reset==False): #Main Program Selector
                S_reset=True # Reset flag set to true
                ## Program 0 - Empty ##
                if(Pc_ProgID==0):
                    print('Program 0: Empty')

                ## Program 1 - Start Print ##
                elif(Pc_ProgID==1)and(S_partonbed==False):#Start Print of Pc_File gCode
                    print('Program 1: Start Print')
                    Pc_File = await NODE_Pc_File.get_value() 
                    print(Pc_File)
                    req = requests.post(urlFiles+Pc_File+apikey,json={"command": "select"})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    time.sleep(delay)
                    req = requests.post(urlJob+apikey,json={"command": "start"})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    time.sleep(delay)

                    # TRANSITION - Change State to "Heating"
                    S_waitforend = True
                    PrinterState.StartPrint()

                ## Program 2 - Cancel Print
                elif(Pc_ProgID==2)and((PrinterState.current_state==PrinterState.Heating)or(PrinterState.current_state==PrinterState.Printing)): 
                    print('Program 2: Cancel Print')
                    req = requests.post(urlJob+apikey,json={"command": "cancel"})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    S_cancel = True # Indicate cancel as been made
                    req = requests.post(urlHead+apikey,json={"command": "jog","x": 0,"y": 0,"z": 10, "speed": 3600})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    time.sleep(delay)
                    req = requests.post(urlHead+apikey,json={"command": "home","axes": ["x","y"]}) # Home X and Y
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    
                    # TRANSITION - Change state to cooldown
                    if(PrinterState.current_state==PrinterState.Heating):
                        S_partonbed = False
                        PrinterState.CancelHeating()
                    elif(PrinterState.current_state==PrinterState.Printing):
                        S_partonbed = True
                        PrinterState.PrintCancelled()

                ## Program 3 - Puase Print
                elif(Pc_ProgID==3): 
                    print('Program 3: Toggle Pause Print')
                    if (PrinterState.current_state==PrinterState.Printing):
                        req = requests.post(urlJob+apikey,json={"command": "pause","action": "toggle"})
                        await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    else:
                        print('Nothing to pause, Not printing')

                ## Program 4 - Jog Axis
                elif(Pc_ProgID==4):
                    print('Program 4: Jog Axis')
                    Pc_JogSpeed = await NODE_Pc_JogSpeed.get_value()
                    Pc_JogX = await NODE_Pc_JogX.get_value()
                    Pc_JogY = await NODE_Pc_JogY.get_value()
                    Pc_JogZ = await NODE_Pc_JogZ.get_value()
                    req = requests.post(urlHead+apikey,json={"command": "jog","x": Pc_JogX,"y": Pc_JogY,"z": Pc_JogZ, "speed": Pc_JogSpeed})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)

                ## Program 5 - Home All Axis
                elif(Pc_ProgID==5): 
                    print('Program 5: Home All')
                    req = requests.post(urlHead+apikey,json={"command": "home","axes": ["x","y","z"]})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)

                ## Program 6 - Update Feedrate
                elif (Pc_ProgID==6):
                    print('Program 6: Feedrate')
                    if(PrinterState.current_state==PrinterState.Printing):
                        Pc_Feedrate = await NODE_Pc_Feedrate.get_value()
                        req = requests.post(urlHead+apikey,json={"command": "feedrate","factor": Pc_Feedrate})
                        await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)

                ## Program 7 - Update Nozzle Temp
                elif (Pc_ProgID==7):
                    print('Program 7: Nozzle Temperature Control')
                    Pc_tNozOffset = await NODE_Pc_tNozOffset.get_value()
                    Pc_tNozTarget = await NODE_Pc_tNozTarget.get_value()   
                    req = requests.post(urlTool+apikey,json={"command": "target","targets": {"tool0":Pc_tNozTarget}})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    time.sleep(delay)
                    req = requests.post(urlTool+apikey,json={"command": "offset","offsets": {"tool0":Pc_tNozOffset}})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)

                ## Program 8 - Update Bed Temp
                elif (Pc_ProgID==8):
                    print('Program 8: Bed Temperature Control')
                    Pc_tBedOffset = await NODE_Pc_tBedOffset.get_value()
                    Pc_tBedTarget = await NODE_Pc_tBedTarget.get_value()
                    req = requests.post(urlBed+apikey,json={"command": "target","target": Pc_tBedTarget})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    time.sleep(delay)
                    req = requests.post(urlBed+apikey,json={"command": "offset","offset": Pc_tBedOffset})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)

                ## Program 9 - Extrusion Test
                elif (Pc_ProgID==9):#Extrusion 
                    print('Program 9: Extrusion Jog')
                    if(Pd_tNozReal>195):
                        Pc_Extrude = await NODE_Pc_Extrude.get_value()
                        req = requests.post(urlTool+apikey,json={"command": "extrude","amount": Pc_Extrude})
                        await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)

                ## Program 10 - Pre Heat
                elif (Pc_ProgID==10):
                    print('Program 10: PreHeat')
                    Pc_tNozTarget = await NODE_Pc_tNozTarget.get_value()
                    Pc_tBedTarget = await NODE_Pc_tBedTarget.get_value()
                    req = requests.post(urlTool+apikey,json={"command": "target","targets": {"tool0":Pc_tNozTarget}})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
                    time.sleep(delay)
                    req = requests.post(urlBed+apikey,json={"command": "target","target": Pc_tBedTarget})
                    await NODE_Pd_APIresp.set_value(str(req),ua.VariantType.String)
            
            # Reset flag handler 
            if (Pc_Start==False)and(S_reset==True): 
                print('Wating for new Program Start')
                S_reset=False

            # End Flag for Programs - After whole process (back to operational) indicate end (pulse)
            if (S_waitforend==True)and(Pd_State=='Operational'): 
                print('End Flag Pulsed')
                await NODE_Pf_End.set_value(True,ua.VariantType.Boolean)
                time.sleep(3)
                await NODE_Pf_End.set_value(False,ua.VariantType.Boolean)
                S_waitforend = False





                

                

            

    

    
if __name__ == '__main__':
    asyncio.run(main())
    

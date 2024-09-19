import asyncio
from asyncua import Client, Node, ua



async def main():
    url = 'opc.tcp://172.32.1.236:4840'
    nP = 3
    async with Client(url=url) as client:

        nodeStr = 'ns=2'+str(nP)+';s=R'+str(nP)

        print(nodeStr+'c_ProgID')
        #1. read values by getting node
        try:
            NODE_Pc_ProgID = client.get_node(nodeStr+'c_ProgID')
            NODE_Pc_Start = client.get_node(nodeStr+'c_Start') #true or false
            NODE_Pf_Ready = client.get_node(nodeStr+'f_Ready') # get the robot's readiness status
        except:
            print("Error: Node Definition")

        #2. extract value from node by getting value
        print(type(NODE_Pc_ProgID))
        Pc_ProgID = await NODE_Pc_ProgID.get_value()
        print(Pc_ProgID)
        print(type(Pc_ProgID))
        Pc_Start = await NODE_Pc_Start.get_value()
        print(Pc_Start)
        print(type(Pc_Start))
        
        print(f'let"s get started!')
        # 3. change the values by using set value
        Pc_ProgID = 75
        Pc_Start = True

        await NODE_Pc_ProgID.set_value(Pc_ProgID,ua.VariantType.Int32)
        print('prog id sent')
        await NODE_Pc_Start.set_value(Pc_Start,ua.VariantType.Boolean)
        print('start sent')

if __name__ == '__main__':
    asyncio.run(main())
import asyncio
from asyncua import Client, Node, ua



async def main():
    url = 'opc.tcp://172.32.1.236:4840'
    nP = 3
    async with Client(url=url) as client:

        nodeStr = 'ns=3;s='

        print(nodeStr+'c_ProgID')
        #1. read values by getting node
        try:
            NODE_magCount = client.get_node(nodeStr+'magCount')
            NODE_magInfo = client.get_node(nodeStr+'magInfo')

        except:
            print("Error: Node Definition")

        #2. extract value from node by getting value
        print(type(NODE_magCount))
        magCount = await NODE_magCount.get_value()
        print(magCount)
        print(type(magCount))
        magInfo = await NODE_magInfo.get_value()
        print(magInfo)
        print(type(magInfo))
        
        print(f'let"s get started!')
        # # # 3. change the values by using set value
        # write_magCount = 7
        # write_magInfo = '[[a,b,c],[e,f,g]]'

        # await NODE_magCount.set_value(write_magCount,ua.VariantType.Int32)
        # print('prog id sent')
        # await NODE_magInfo.set_value(write_magInfo,ua.VariantType.String)
        # print('start sent')


        # # get parent name
        # parent_obj = await NODE_magInfo.get_parent()

        # print(parent_obj)
        # print(await parent_obj.read_display_name())


if __name__ == '__main__':
    asyncio.run(main())
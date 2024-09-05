import asyncio
from asyncua import Client, ua

async def browse_node(node):
    # Browse the node's children
    try:
        children = await node.get_children()
        for child in children:
            print(f"Node: {child}, Display Name: {await child.read_display_name()}")
            # Recursively browse the children of each child
            await browse_node(child)
    except Exception as e:
        print(f"Error browsing node {node}: {e}")

async def main():
    # Connect to the OPC UA server
    url = 'opc.tcp://172.32.1.236:4840'  # Replace with your server's URL
    async with Client(url) as client:
        # Get the root node of the server
        root_node = client.nodes.root
        print(f"Root Node: {root_node}, Display Name: {await root_node.read_display_name()}")

        # Start browsing from the root node
        await browse_node(root_node)

if __name__ == "__main__":
    asyncio.run(main())

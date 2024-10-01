import requests
url1 = 'http://172.32.1.210:5000/api/printer?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
#url1= 'http://localhost:5000/api/printer?apikey=40D71A0A911C4E2CB0DD05BC50960A6B'
response = requests.get(url1)
printer_info = response.json()
print(printer_info)
paused_flag = printer_info['state']['flags']['pausing']
print(paused_flag)

# import aiohttp
# import asyncio

# async def get_z_axis_position():
#     IPadd = '172.32.1.210'
#     apikey = 'CF0D132DDC3342CD8EC1EE9D5FCFDA06'
#     urlPrinter = f'http://{IPadd}:5000/api/printer'
#     headers = {'X-Api-Key': apikey}

#     async with aiohttp.ClientSession() as session:
#         async with session.get(urlPrinter, headers=headers) as response:
#             if response.status == 200:
#                 printer_data = await response.json()
#                 print(printer_data)
#                 z_axis = printer_data['position']['z']
#                 print(f'Z-axis position: {z_axis}')
#             else:
#                 print(f'Failed to get printer status: {response.status}')

# # Run the async function
# asyncio.run(get_z_axis_position())

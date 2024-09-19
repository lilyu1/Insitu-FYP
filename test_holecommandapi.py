import requests

# Base URL of the OctoPrint instance
#url_base = 'http://localhost:5000/api/plugin/holeCommandAPIplugin'
url_base = 'http://172.32.1.210:5000/api/plugin/holeCommandAPIplugin'

#it's case sensitive bitch

# Your API key
#apikey = '40D71A0A911C4E2CB0DD05BC50960A6B'
apikey = "CF0D132DDC3342CD8EC1EE9D5FCFDA06"

# Send a GET request to the same plugin API
response_get = requests.get(f'{url_base}?apikey={apikey}')

json_coord = response_get.json()['coordinates']

# Check responses
print(json_coord)

print(type(json_coord))

str_coord = str(json_coord)
print(str_coord)
# # # Evaluate the string as a list of lists
coordinates_list = eval(str_coord)
print(coordinates_list)

# # Count the number of x-y-z coordinates
num_coordinates = len(json_coord)
print(num_coordinates)

# print(coordinates_list)
# print(num_coordinates)


url_base = 'http://172.32.1.210:5000/api/printer'

printer_info = requests.get(f'{url_base}?apikey={apikey}')

# Check responses
print("GET response:", printer_info.json())
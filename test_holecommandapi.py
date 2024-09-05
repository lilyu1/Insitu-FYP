import requests

# Base URL of the OctoPrint instance
url_base = 'http://localhost:5000/api/plugin/holeCommandAPIplugin'
#it's case sensitive bitch

# Your API key
apikey = '40D71A0A911C4E2CB0DD05BC50960A6B'

# Send a GET request to the same plugin API
response_get = requests.get(f'{url_base}?apikey={apikey}')

# Check responses
print("GET response:", response_get.json())


url_base = 'http://localhost:5000/api/printer'

printer_info = requests.get(f'{url_base}?apikey={apikey}')

# Check responses
print("GET response:", printer_info.json())
import requests
url1 = 'http://172.32.1.210:5000/api/printer?apikey=CF0D132DDC3342CD8EC1EE9D5FCFDA06'
response = requests.get(url1)
printer_info = response.json()
print(printer_info)
paused_flag = printer_info['state']['flags']['pausing']
print(paused_flag)

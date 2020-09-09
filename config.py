import json
import os

base_path = os.path.dirname(os.path.realpath(__file__))

with open(base_path + '/config.json') as f:
    config = json.load(f)

fiware_service = config['fiware_service']
fiware_servicepath = config['fiware_servicepath']
orion_url = config['orion_url']
iota_url = config['iota_url']

post_headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Fiware-Service': fiware_service,
    'Fiware-ServicePath': fiware_servicepath
}

get_headers = {
    'Accept': 'application/json',
    'Fiware-Service': fiware_service,
    'Fiware-ServicePath': fiware_servicepath
}
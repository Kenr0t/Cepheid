import os

CEP_CB_HOST = os.getenv('CEP_CB_HOST', 'localhost')
CEP_CB_PORT = os.getenv('CEP_CB_PORT', '1026')
CEP_IOTA_HOST = os.getenv('CEP_IOTA_HOST', 'localhost')
CEP_IOTA_PORT = os.getenv('CEP_IOTA_PORT', '4061')
CEP_MONGO_HOST = os.getenv('CEP_MONGO_HOST', 'localhost')
CEP_MONGO_PORT = os.getenv('CEP_MONGO_PORT', '27017')
CEP_MONGO_DB = os.getenv('CEP_MONGO_DB', 'cepheid')
CEP_DEFAULT_SERVICE = os.getenv('CEP_DEFAULT_SERVICE', 'orion')
CEP_DEFAULT_SERVICEPATH = os.getenv('CEP_DEFAULT_SERVICEPATH', '/environment')
CEP_PROVIDER_URL = os.getenv('CEP_PROVIDER_URL', 'http://0.0.0.0:4013')

print(CEP_CB_HOST, CEP_IOTA_HOST, CEP_MONGO_HOST, sep='\n')

default_service = CEP_DEFAULT_SERVICE
default_servicepath = CEP_DEFAULT_SERVICEPATH
orion_url = f'http://{CEP_CB_HOST}:{CEP_CB_PORT}'
iota_url = f'http://{CEP_IOTA_HOST}:{CEP_IOTA_PORT}'
cepheid_url = CEP_PROVIDER_URL

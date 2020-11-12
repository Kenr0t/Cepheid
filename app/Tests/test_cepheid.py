import unittest
import json
import time

import requests

from config import orion_url, iota_url, default_service, default_servicepath
from Rule import Rule

svc = default_service
svcP = default_servicepath
headers = {"Accept": "application/json", "Fiware-Service": svc, "Fiware-ServicePath": svcP}
post_headers = headers.copy()
post_headers["Content-Type"] = "application/json"


class TestRuleDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        device = {
            "device_id": 'Test01_dev',
            "entity_name": 'Test01',
            "entity_type": 'TestEntity',
            "protocol": "PDI-IoTA-UltraLight",
            "transport": "HTTP",
            "attributes": [
                {'object_id': 'tmp', 'name': 'Temperature', 'type': 'Number'},
                {'object_id': 'lmn', 'name': 'Lumens', 'type': 'Number'},
            ],
            "endpoint": "https://kenr0t.free.beeceptor.com/iota/Test01",
            'commands': [
                {'name': 'AC_On', 'type': 'command'},
                {'name': 'AC_Off', 'type': 'command'}
            ]

        }
        requests.post(f'{iota_url}/iot/devices', data=json.dumps({'devices': [device]}), headers=post_headers)
        requests.post(
            f'http://localhost:7896/iot/d?k=4jggokgpepnvsb2uv4s40d59ov&i=Test01_dev',
            data='tmp|25|lmn|1200', headers={'Content-Type': 'text/plain'}
        )

    @classmethod
    def tearDownClass(cls) -> None:
        requests.delete(f'{iota_url}/iot/devices/Test01_dev', headers=headers)
        requests.delete(f'{orion_url}/v2/entities/Test01', headers=headers)

    def test_CRUD(self):
        r1 = Rule('Test01.Temperature > 26', svc, svcP, true='Test01.AC_On', false='Test01.AC_Off')
        resp = requests.post(f'http://localhost:4013/rules', data=json.dumps(r1.to_dict()), headers=post_headers)
        self.assertEqual(resp.status_code, 200)
        rule_id = resp.headers['Location'].split('/')[-1]

        resp = requests.post(f'http://localhost:4013/rules', data=json.dumps(r1.to_dict()), headers=post_headers)
        self.assertEqual(resp.status_code, 409)

        requests.post(
            f'http://localhost:7896/iot/d?k=4jggokgpepnvsb2uv4s40d59ov&i=Test01_dev',
            data='tmp|28|lmn|1200', headers={'Content-Type': 'text/plain'}
        )
        time.sleep(5)

        resp = requests.get(f'http://localhost:4013/rules/{rule_id}', headers=headers)
        self.assertEqual(resp.status_code, 200)

        resp = requests.get(f'http://localhost:4013/rules', headers=headers)
        self.assertEqual(resp.status_code, 200)

        resp = requests.delete(f'http://localhost:4013/rules/{rule_id}', headers=headers)
        self.assertEqual(resp.status_code, 204)

        resp = requests.delete(f'http://localhost:4013/rules/{rule_id}', headers=headers)
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()

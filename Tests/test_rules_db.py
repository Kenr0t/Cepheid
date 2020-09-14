import unittest
import json

import requests

from config import orion_url, post_headers, get_headers, iota_url
from Rule import Rule
from Rules_db import RulesDB


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
            data='tmp|28|lmn|1200', headers={'Content-Type': 'text/plain'}
        )

    @classmethod
    def tearDownClass(cls) -> None:
        requests.delete(f'{iota_url}/iot/devices/Test01_dev', headers=get_headers)
        requests.delete(f'{orion_url}/v2/entities/Test01', headers=get_headers)

    def test_crud(self):
        rdb = RulesDB()
        r1 = Rule('Test01.Temperature > 26', true='Test01.AC_On', false='Test01.AC_Off')
        r2 = Rule('Test01.Lumens < 1200', true='Test01.AC_On')
        self.assertTrue(isinstance(id_r1 := rdb.persist(r1), str))
        self.assertTrue(isinstance(id_r2 := rdb.persist(r2), str))
        self.assertIsNone(rdb.persist(r1))
        self.assertIsNone(rdb.persist(r2))
        all_rules = rdb.get_all()
        self.assertIn(r1, all_rules)
        self.assertIn(r2, all_rules)
        self.assertTrue(rdb.delete_by_id(id_r1))
        self.assertTrue(rdb.delete_by_id(id_r2))


if __name__ == '__main__':
    unittest.main()

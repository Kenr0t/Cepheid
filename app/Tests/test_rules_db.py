import unittest
import json

import requests

from config import orion_url, iota_url, default_service, default_servicepath
from Rule import Rule
from Rules_db import RulesDB

svc = default_service
svcP = default_servicepath
headers = {"Accept": "application/json", "Fiware-Service": svc, "Fiware-ServicePath": svcP}


class TestRuleDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        post_headers = headers.copy()
        post_headers["Content-Type"] = "application/json"

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

        cls.r1 = Rule('Test01.Temperature > 26', svc, svcP, true='Test01.AC_On', false='Test01.AC_Off')
        cls.r1.subscribe()
        cls.r2 = Rule('Test01.Lumens < 1200', svc, svcP, true='Test01.AC_On')
        cls.r2.subscribe()
        cls.rdb = RulesDB()
        cls.id_r1 = None


    @classmethod
    def tearDownClass(cls) -> None:
        cls.r1.unsubscribe()
        cls.r2.unsubscribe()
        requests.delete(f'{iota_url}/iot/devices/Test01_dev', headers=headers)
        requests.delete(f'{orion_url}/v2/entities/Test01', headers=headers)

    def test_CRUD(self):
        # Testing Inserts
        self.id_r1 = self.rdb.insert(self.r1)
        self.assertIsInstance(self.id_r1, str)
        self.assertIn(self.r1, self.rdb)
        self.assertIsInstance(self.rdb.insert(self.r2), str)
        self.assertIn(self.r2, self.rdb)

        # Testing Getters
        all_rules = self.rdb.get_all(svc, svcP)
        self.assertIn(self.r1, all_rules)
        self.assertIn(self.r2, all_rules)
        sub_finded_rule = self.rdb.find_by_subscription_id(self.r1.subscription_id, svc, svcP)
        self.assertEqual(sub_finded_rule, self.r1)

        # Testing Deleters
        self.assertTrue(self.rdb.delete_by_id(self.id_r1, svc, svcP))
        self.assertTrue(self.rdb.delete(self.r2))
        self.assertFalse(self.rdb.delete(self.r2))


if __name__ == '__main__':
    unittest.main()

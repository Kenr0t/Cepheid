import unittest
import json
from datetime import datetime, time

import requests

from config import orion_url, iota_url
from Rule import Rule

svc = "orion"
svcP = "/environment"
headers = {"Accept": "application/json", "Fiware-Service": svc, "Fiware-ServicePath": svcP}


class TestParser(unittest.TestCase):
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
                {'object_id': 'tmp', 'name': 'Temperature', 'type': 'String'},
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
            data='tmp|Hot|lmn|1200', headers={'Content-Type': 'text/plain'}
        )

    @classmethod
    def tearDownClass(cls) -> None:
        requests.delete(f'{iota_url}/iot/devices/Test01_dev', headers=headers)
        requests.delete(f'{orion_url}/v2/entities/Test01', headers=headers)

    def test_check_action(self):
        rule = Rule('Test01.Temperature = "Hot"', svc, svcP)

        with self.assertRaises(ValueError):
            rule._check_action('Test.AC_On')
            rule._check_action('Test01.Light_On')
        self.assertEqual(rule._check_action('Test01.AC_On'), ('TestEntity', 'Test01.AC_On'))

    def test_date_and_time(self):
        with self.assertRaises(ValueError):
            Rule._parse_date(1234)
            Rule._parse_date('12/23')
            Rule._parse_date('32/12/21')
            Rule._parse_time(1234)
            Rule._parse_time('12/23')
            Rule._parse_time('23:61')

        self.assertEqual(Rule._parse_date('20/10/11'), datetime(2011, 10, 20))
        self.assertEqual(Rule._parse_date(datetime(2011, 10, 20)), datetime(2011, 10, 20))

        self.assertEqual(Rule._parse_time('11:30'), time(hour=11, minute=30))
        self.assertEqual(Rule._parse_time(time(hour=11, minute=30)), time(hour=11, minute=30))

    def test_rule_true_false(self):
        rule_ok = Rule('Test01.Temperature = "Hot"', svc, svcP, true='Test01.AC_On', false='Test01.AC_Off')
        self.assertTrue(rule_ok.execute())
        rule_ko = Rule('Test01.Temperature != "Hot"', svc, svcP, true='Test01.AC_On', false='Test01.AC_Off')
        self.assertFalse(rule_ko.execute())

    def test_rules_hours(self):
        first_hours = Rule('Test01.Temperature = "Hot"', svc, svcP, true='Test01.AC_On')
        first_hours.set_schedule(start_time='08:00', end_time='22:30')
        second_hours = Rule('Test01.Temperature = "Hot"', svc, svcP, true='Test01.AC_On')
        second_hours.set_schedule(start_time='22:30', end_time='08:00')
        if time(9, 0) <= datetime.now().time() <= time(22, 30):
            self.assertTrue(first_hours.execute())
            self.assertIsNone(second_hours.execute())
        else:
            self.assertIsNone(first_hours.execute())
            self.assertTrue(second_hours.execute())

    def test_rules_dates(self):
        yes_date = Rule(
            'Test01.Temperature = "Hot"', svc, svcP, true='Test01.AC_On'
        ).set_date_from('01/01/2020').set_date_to('01/01/21')

        self.assertTrue(yes_date.execute())
        pre_date = Rule('Test01.Temperature = "Hot"', svc, svcP, true='Test01.AC_On',)
        pre_date.set_date_from('01/01/2021').set_date_to('01/01/22')
        self.assertIsNone(pre_date.execute())
        post_date = Rule('Test01.Temperature = "Hot"', svc, svcP, true='Test01.AC_On')
        post_date.set_date_from('01/01/2019').set_date_to('01/01/20')
        self.assertIsNone(post_date.execute())

    def test_get_entities(self):
        rule = Rule('or(Test01.Temperature = "Hot", Test01.Lumens < 2000)', svc, svcP, true='Test01.AC_On')
        self.assertEqual(rule.get_entities(), {'Test01': {'attrs': ['Lumens', 'Temperature'], 'type': 'TestEntity'}})

    def test_subscriptions(self):
        rule = Rule('or(Test01.Temperature = "Hot", Test01.Lumens < 2000)', svc, svcP, true='Test01.AC_On')
        self.assertTrue(rule.subscribe())
        self.assertFalse(rule.subscribe())
        self.assertTrue(rule.unsubscribe())
        self.assertIsNone(rule.unsubscribe())


if __name__ == '__main__':
    unittest.main()

import json
import unittest

import requests

from Compiler import Lexer, Parser
from config import orion_url, post_headers, get_headers


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:

        new_entity = {
            "id": 'TestEntity001',
            "type": 'TestEntity',
            'TestAttr1': {
                'type': 'Integer',
                'value': 1
            },
            'TestAttr2': {
                'type': 'String',
                'value': '2'
            }
        }

        requests.post(
            url=f'{orion_url}/v2/entities', data=json.dumps(new_entity),
            headers=post_headers
        )

    @classmethod
    def tearDownClass(cls) -> None:
        requests.delete(
            f'{orion_url}/v2/entities/TestEntity001',
            headers=get_headers
        )

    def test_something(self):
        lexer = Lexer()
        parser = Parser()
        
        parse = lambda x: parser.parse(lexer.lex(x))

        with self.assertRaises(ValueError):  # When attr or entity does not exists, raise a ValueError
            parse('TestEntity002.TestAttr2 = "2"')
            parse('TestEntity001.TestAttr3 = "2"')

        self.assertTrue(parse('TestEntity001.TestAttr1 = 1').eval())
        self.assertTrue(parse('TestEntity001.TestAttr2 = "2"').eval())

        self.assertFalse(parse('TestEntity001.TestAttr1 = 5').eval())
        self.assertFalse(parse('TestEntity001.TestAttr2 = "Potatoe"').eval())

        self.assertTrue(parse('or(TestEntity001.TestAttr1 >= 1, TestEntity001.TestAttr2 = "2")').eval())
        self.assertTrue(parse('or(TestEntity001.TestAttr1 != 1, TestEntity001.TestAttr2 = "2")').eval())
        self.assertTrue(parse('or(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "3")').eval())
        self.assertFalse(parse('or(TestEntity001.TestAttr1 = 2, TestEntity001.TestAttr2 = "3")').eval())

        self.assertTrue(parse('and(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "2")').eval())
        self.assertFalse(parse('and(TestEntity001.TestAttr1 = 2, TestEntity001.TestAttr2 = "2")').eval())
        self.assertFalse(parse('and(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "3")').eval())
        self.assertFalse(parse('and(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "3")').eval())

        self.assertTrue(parse('and(TestEntity001.TestAttr1 >= 0, TestEntity001.TestAttr1 <= 5)').eval())


if __name__ == '__main__':
    unittest.main()

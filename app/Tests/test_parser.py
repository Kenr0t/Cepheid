import json
import unittest

import requests

from Compiler import Lexer, Parser, LexingError
from config import orion_url

headers = {"Accept": "application/json", "Fiware-Service": "orion", "Fiware-ServicePath": "/environment"}


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        post_headers = headers.copy()
        post_headers["Content-Type"] = "application/json"

        new_entity = {
            "id": 'TestEntity001',
            "type": 'TestEntity',
            'TestAttr1': {'type': 'Integer', 'value': 1},
            'TestAttr2': {'type': 'String', 'value': '2'},
            'TestAttr3': {'type': 'Float', 'value': 3.33}
        }
        requests.post(url=f'{orion_url}/v2/entities', data=json.dumps(new_entity), headers=post_headers)

        lexer = Lexer()
        parser = Parser()

        def parse(rule):
            return parser.parse(lexer.lex(rule), headers)

        cls.parse = (parse, )  # If the function is assigned, the self is always passed as paremeters. We use a tuple.

    @classmethod
    def tearDownClass(cls) -> None:
        requests.delete(f'{orion_url}/v2/entities/TestEntity001', headers=headers)

    def test_parsing_errors(self):
        parse = self.parse[0]
        with self.assertRaises(ValueError):  # When entity does not exists, raise a ValueError
            parse('TestEntity002.TestAttr2 = "2"')
        with self.assertRaises(ValueError):  # When attr does not exists, raise a ValueError
            parse('TestEntity001.TestAttr4 = "2"')
        with self.assertRaises(ValueError):  # When the rule is not correct...
            parse('or(1 = 1, 2, 3 = 3.33)')
        with self.assertRaises(ValueError):
            parse('and(1 = 1')
        with self.assertRaises(LexingError):
            parse('"Hello" = "Hell')
        with self.assertRaises(LexingError):
            parse('orr(1 = 1)')

    def test_text(self):
        parse = self.parse[0]

        self.assertTrue(parse('TestEntity001.TestAttr2 = "2"').eval())
        self.assertFalse(parse('TestEntity001.TestAttr2 = "Potatoe"').eval())
        with self.assertRaises(TypeError):  # TestAttr2 is a string, does not match with the int.
            self.assertTrue(parse('TestEntity001.TestAttr2 = 2').eval())

    def test_integers(self):
        parse = self.parse[0]

        self.assertTrue(parse('TestEntity001.TestAttr1 = 1').eval())
        self.assertFalse(parse('TestEntity001.TestAttr1 = 5').eval())
        self.assertTrue(parse('TestEntity001.TestAttr1 != 5').eval())
        with self.assertRaises(TypeError):  # TestAttr1 is a int, does not match with the string.
            self.assertTrue(parse('TestEntity001.TestAttr1 = "1"').eval())

    def test_floats(self):
        parse = self.parse[0]

        self.assertTrue(parse('TestEntity001.TestAttr3 = 3.33').eval())
        self.assertFalse(parse('TestEntity001.TestAttr3 = 5.55').eval())
        self.assertTrue(parse('TestEntity001.TestAttr3 != 3').eval())
        self.assertFalse(parse('TestEntity001.TestAttr3 = 5').eval())
        with self.assertRaises(TypeError):  # TestAttr1 is a int, does not match with the string.
            self.assertTrue(parse('TestEntity001.TestAttr3 = "1"').eval())

    def test_inequality(self):
        parse = self.parse[0]

        self.assertTrue(parse('1 >= 0.98').eval())
        self.assertTrue(parse('1 >= 1').eval())
        self.assertTrue(parse('1.0 >= 1').eval())
        self.assertTrue(parse('1 >= 1.0').eval())
        self.assertTrue(parse('3 <= 5.0').eval())
        self.assertTrue(parse('5 <= 5.0').eval())
        self.assertTrue(parse('10 < 20').eval())
        self.assertTrue(parse('20 > 10').eval())

    def test_or_and(self):
        parse = self.parse[0]

        self.assertTrue(parse('or(TestEntity001.TestAttr1 >= 1, TestEntity001.TestAttr2 = "2", 1 = 1)').eval())
        self.assertTrue(parse('or(TestEntity001.TestAttr1 != 1, TestEntity001.TestAttr2 = "2", 1 = 1)').eval())
        self.assertTrue(parse('or(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "3", 1 = 1)').eval())
        self.assertFalse(parse('or(TestEntity001.TestAttr1 = 2, TestEntity001.TestAttr2 = "3", 1 = 7)').eval())

        self.assertTrue(parse('and(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "2")').eval())
        self.assertFalse(parse('and(TestEntity001.TestAttr1 = 2, TestEntity001.TestAttr2 = "2")').eval())
        self.assertFalse(parse('and(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "3")').eval())
        self.assertFalse(parse('and(TestEntity001.TestAttr1 = 1, TestEntity001.TestAttr2 = "3")').eval())

        self.assertTrue(parse('and(TestEntity001.TestAttr1 >= 0, TestEntity001.TestAttr1 <= 5)').eval())
        self.assertEqual(
            parse('and(TestEntity001.TestAttr1 >= 0, TestEntity001.TestAttr1 <= 5)').get_entities(),
            {'TestEntity001': {'type': 'TestEntity', 'attrs': {'TestAttr1'}}}
        )


if __name__ == '__main__':
    unittest.main()

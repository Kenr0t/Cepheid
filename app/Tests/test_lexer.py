import unittest
from Compiler import Lexer


class MyTestCase(unittest.TestCase):
    def test_lexer(self):
        lexer = Lexer()
        to_tokenize = '("hello") <= >= = != < > or and attr 10 10.2'
        spected_tokens = [
            'L_PAR', 'STRING', 'R_PAR', 'LOWER_EQ', 'GREATER_EQ', 'EQUAL', 'DIST', 'LOWER', 'GREATER', 'OR', 'AND',
            'ID', 'INTEGER', 'DECIMAL'
        ]
        tokens = list(lexer.lex(to_tokenize))

        for recognized, spected in zip(tokens, spected_tokens):
            self.assertEqual(recognized.gettokentype(), spected)


if __name__ == '__main__':
    unittest.main()

from rply import LexerGenerator, LexingError


class Lexer:
    def __init__(self):
        self.__lexer = LexerGenerator()
        self._add_tokens()
        self.__lexer = self.__lexer.build()

    def _add_tokens(self):
        # Strings
        self.__lexer.add('STRING', r'"((?:""|[^"])*)"')
        # Parentheses
        self.__lexer.add('L_PAR', r'\(')
        self.__lexer.add('R_PAR', r'\)')
        # Punctuation
        self.__lexer.add('COMMA', r',')
        self.__lexer.add('DOT', r'\.')
        # Comparators
        self.__lexer.add('GREATER_EQ', r'>=')
        self.__lexer.add('LOWER_EQ', r'<=')
        self.__lexer.add('EQUAL', r'=')
        self.__lexer.add('DIST', r'!=')
        self.__lexer.add('GREATER', r'>')
        self.__lexer.add('LOWER', r'<')
        # Logical operations
        self.__lexer.add('OR', r'(?i)or')
        self.__lexer.add('AND', r'(?i)and')
        # Numbers
        self.__lexer.add('DECIMAL', r'\d+\.\d+')
        self.__lexer.add('INTEGER', r'\d+')
        # Ignore spaces
        self.__lexer.ignore(r'\s+')
        # Attributes
        self.__lexer.add('ID', r'[a-zA-Z_]\w+')

    def lex(self, s):
        return self.__lexer.lex(s=s)

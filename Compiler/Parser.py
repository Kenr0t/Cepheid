import requests

from rply import ParserGenerator

from config import get_headers, orion_url


class Value:
    def __init__(self, val):
        self.val = val

    def get_entities(self):
        return []


class Decimal(Value):
    def eval(self):
        return float(self.val)


class Integer(Value):
    def eval(self):
        return int(self.val)


class String(Value):
    def __init__(self, val):
        super(String, self).__init__(val[1:-1])

    def eval(self):
        return self.val


class Attribute:
    def __init__(self, entity_id, attr):
        self.entity_id = entity_id
        self.attr_id = attr
        self.eval()

    def eval(self):
        entity = requests.get(
            url=f'{orion_url}/v2/entities/{self.entity_id}?options=keyValues',
            headers=get_headers
        ).json()
        if 'error' in entity:
            raise ValueError(f'The entity "{self.entity_id}" does not exist.')
        if self.attr_id not in entity:
            raise ValueError(f'The attribute "{self.attr_id}", does not belong to the entity "{self.entity_id}".')
        return entity[self.attr_id]

    def get_entities(self):
        return [self.entity_id]


class BinaryOperator:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def get_entities(self):
        return self.left.get_entities() + self.right.get_entities()


class GreaterEq(BinaryOperator):
    def eval(self):
        return self.left.eval() >= self.right.eval()


class LowerEq(BinaryOperator):
    def eval(self):
        return self.left.eval() <= self.right.eval()


class Equal(BinaryOperator):
    def eval(self):
        return self.left.eval() == self.right.eval()


class Distinct(BinaryOperator):
    def eval(self):
        return self.left.eval() != self.right.eval()


class Greater(BinaryOperator):
    def eval(self):
        return self.left.eval() > self.right.eval()


class Lower(BinaryOperator):
    def eval(self):
        return self.left.eval() < self.right.eval()


class LogicalOperator:
    def __init__(self, expressions: list):
        self.expressions = expressions

    def get_entities(self):
        return [e for entities in self.expressions for e in entities.get_entities()]


class And(LogicalOperator):
    def eval(self):
        return all(exp.eval() for exp in self.expressions)


class Or(LogicalOperator):
    def eval(self):
        return any(exp.eval() for exp in self.expressions)


# -------------------------------------------------------------------------------------------------------------------- #
#                                                       P A R S E R                                                    #
# -------------------------------------------------------------------------------------------------------------------- #

class Parser:
    __ops = {
        'GREATER_EQ': GreaterEq,
        'LOWER_EQ': LowerEq,
        'EQUAL': Equal,
        'DIST': Distinct,
        'GREATER': Greater,
        'LOWER': Lower,
        'OR': Or,
        'AND': And,
        'DECIMAL': Decimal,
        'INTEGER': Integer,
        'STRING': String
    }

    def __init__(self):
        self.__pg = ParserGenerator(
            ['ID', 'L_PAR', 'R_PAR', 'DOT', 'COMMA', *self.__ops.keys()]
        )

        self.__setup_parser()
        self.entity = None
        self.__parser = self.__pg.build()

    def __setup_parser(self):
        @self.__pg.production('comparison : boolean')
        def comparison(p):
            return p[0]

        @self.__pg.production('boolean : valor GREATER_EQ valor')
        @self.__pg.production('boolean : valor LOWER_EQ valor')
        @self.__pg.production('boolean : valor EQUAL valor')
        @self.__pg.production('boolean : valor DIST valor')
        @self.__pg.production('boolean : valor GREATER valor')
        @self.__pg.production('boolean : valor LOWER valor')
        def boolean_bin(p):
            return self.__ops[p[1].gettokentype()](p[0], p[2])

        @self.__pg.production('boolean : OR L_PAR extra R_PAR')
        @self.__pg.production('boolean : AND L_PAR extra R_PAR')
        def boolean_log(p):
            return self.__ops[p[0].gettokentype()](p[2])

        @self.__pg.production('extra : boolean COMMA extra')
        @self.__pg.production('extra : boolean')
        def boolean_extra(p):
            if len(p) == 1:
                return [p[0]]
            else:
                return [p[0]] + p[2]

        @self.__pg.production('valor : DECIMAL')
        @self.__pg.production('valor : INTEGER')
        @self.__pg.production('valor : STRING')
        def valor(p):
            return self.__ops[p[0].gettokentype()](p[0].value)

        @self.__pg.production('valor : ID DOT ID')
        @self.__pg.production('valor : ID DOT STRING')
        @self.__pg.production('valor : STRING DOT ID')
        @self.__pg.production('valor : STRING DOT STRING')
        def variable(p):
            entity, _, attr = p

            entity_id = entity.value
            if entity.gettokentype() == 'STRING':
                entity_id = String(entity_id).eval()

            attr_id = attr.value
            if attr.gettokentype() == 'STRING':
                attr_id = String(attr_id).eval()

            return Attribute(entity_id, attr_id)

        @self.__pg.error
        def error_handle(token):
            raise ValueError(token)

    def parse(self, tokenizer):
        return self.__parser.parse(tokenizer=tokenizer)



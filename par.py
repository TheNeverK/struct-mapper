from lex import CalcLexer
from sly import Parser

class CalcParser(Parser):
    tokens = CalcLexer.tokens
    
    @_("ID")
    def primary_expression(self, p):
        return p.ID

    @_("constant")
    def primary_expression(self, p):
        return p.constant

    @_("string")
    def primary_expression(self, p):
        return p.string

    @_("NUMBER")
    def constant(self, p):
        return p.NUMBER


if __name__ == '__main__':
    data = '''
struct name {};
'''
    lexer = CalcLexer()
    for tok in lexer.tokenize(data):
        print(tok)
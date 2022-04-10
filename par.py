from lex import CalcLexer
from sly import Parser
import json

class Struct(dict): 
    cnt = 0
    def __init__(self, name, declaration_list = None) -> None:
        if name == "":
            self.name = "anonymous_" + str(Struct.cnt)
            Struct.cnt += 1
        else:
            self.name = name
        self.declaration_list = declaration_list

    def __str__(self) -> str:
        return 'struct "' + self.name + '": ' + json.dumps(self.declaration_list) + '\n'

    def __repr__(self):
        return str(self)

class CalcParser(Parser):
    tokens = CalcLexer.tokens
    debugfile = 'parser.out'
    
    @_("struct_list struct_or_union_specifier")
    def struct_list(self, p):
        return p.struct_list + [p.struct_or_union_specifier]

    @_("struct_or_union_specifier")
    def struct_list(self, p):
        return [p.struct_or_union_specifier]

    @_("ID")
    def primary_expression(self, p):
        return p.ID

    @_("constant")
    def primary_expression(self, p):
        return p.constant

    # @_("string")
    # def primary_expression(self, p):
    #     return p.string

    @_("NUMBER")
    def constant(self, p):
        return p.NUMBER

    @_("CHAR", "SHORT", "INT", "LONG",
    "FLOAT", "DOUBLE", "SIGNED", "UNSIGNED", "BOOL",
    "struct_or_union_specifier")
    def type_specifier(self, p):
        return p[0]

    @_("struct_or_union LBRACE struct_declaration_list RBRACE",
    "struct_or_union LBRACE struct_declaration_list RBRACE SEMI")
    def struct_or_union_specifier(self, p):
        return Struct("", p.struct_declaration_list)
    
    @_("struct_or_union ID LBRACE struct_declaration_list RBRACE",
    "struct_or_union ID LBRACE struct_declaration_list RBRACE SEMI")
    def struct_or_union_specifier(self, p):
        return Struct(p.ID, p.struct_declaration_list)

    @_("struct_or_union ID", "struct_or_union ID SEMI")
    def struct_or_union_specifier(self, p):
        return Struct(p.ID)

    @_("STRUCT")
    def struct_or_union(self, p):
        return p.STRUCT

    @_("struct_declaration")
    def struct_declaration_list(self, p):
        return [p.struct_declaration]

    @_("struct_declaration_list struct_declaration")
    def struct_declaration_list(self, p):
        return p.struct_declaration_list + [p.struct_declaration]

    @_("specifier_qualifier_list SEMI")
    def struct_declaration(self, p):
        return (p.specifier_qualifier_list, None)

    @_("specifier_qualifier_list struct_declarator_list SEMI")
    def struct_declaration(self, p):
        return (p.specifier_qualifier_list, p.struct_declarator_list)

    @_("type_specifier specifier_qualifier_list")
    def specifier_qualifier_list(self, p):
        return [p.type_specifier] + p.specifier_qualifier_list

    @_("type_specifier")
    def specifier_qualifier_list(self, p):
        return [p.type_specifier]

    # @_("type_qualifier specifier_qualifier_list")
    # def specifier_qualifier_list(self, p):
    #     return [p.type_qualifier] + p.specifier_qualifier_list

    # @_("type_qualifier")
    # def specifier_qualifier_list(self, p):
    #     return [p.type_qualifier]

    @_("struct_declarator")
    def struct_declarator_list(self, p):
        return [p.struct_declarator]

    @_("struct_declarator_list COMMA struct_declarator")
    def struct_declarator_list(self, p):
        return p.struct_declarator_list + [p.struct_declarator]


    @_("COLON primary_expression")
    def struct_declarator(self, p):
        return (None, p.primary_expression)

    @_("declarator COLON primary_expression")
    def struct_declarator(self, p):
        return (p.declarator, p.primary_expression)

    @_("declarator")
    def struct_declarator(self, p):
        return (p.declarator, None)

    @_("pointer direct_declarator")
    def declarator(self, p):
        return p.pointer + p.direct_declarator

    @_("direct_declarator")
    def declarator(self, p):
        return p.direct_declarator

    @_("ID")
    def direct_declarator(self, p):
        return p.ID

    @_("LPAREN declarator RPAREN")
    def direct_declarator(self, p):
        return p.LPAREN + p.declarator + p.RPAREN

    @_("direct_declarator LBRACKET RBRACKET")
    def direct_declarator(self, p):
        return p.direct_declarator + p.LBRACKET + p.RBRACKET

    @_("direct_declarator LBRACKET POINTER RBRACKET")
    def direct_declarator(self, p):
        return p.direct_declarator + p.LBRACKET + p.POINTER + p.RBRACKET

    @_("direct_declarator LBRACKET NUMBER RBRACKET")
    def direct_declarator(self, p):
        return p.direct_declarator + p.LBRACKET + p.NUMBER + p.RBRACKET

    # @_("direct_declarator LBRACKET type_qualifier_list POINTER RBRACKET")
    # def direct_declarator(self, p):
    #     return p.direct_declarator + p.LBRACKET + ''.join(p.type_qualifier_list) + p.POINTER + p.RBRACKET

    @_("direct_declarator LPAREN RPAREN")
    def direct_declarator(self, p):
        return p.direct_declarator + p.LPAREN + p.RPAREN

    @_("direct_declarator LPAREN identifier_list RPAREN")
    def direct_declarator(self, p):
        return p.direct_declarator + p.LPAREN + ''.join(p.identifier_list) + p.RPAREN

    @_("POINTER pointer")
    def pointer(self, p):
        return p.POINTER + p.pointer

    @_("POINTER")
    def pointer(self, p):
        return p.POINTER

    @_("ID")
    def identifier_list(self, p):
        return [p.ID]

    @_("identifier_list COMMA ID")
    def identifier_list(self, p):
        return p.identifier_list + [p.ID]

    # @_("CONST")
    # def type_qualifier(self, p):
    #     return p.CONST

    # @_("")
    # def temp(self, p):
    #     pass


if __name__ == '__main__':
    data = '''
struct simple1 {
    int a;
    bool b;
    char c;
};

struct simple2 {
    char* str;
    int arr[3];
    struct simple1 another;
};
'''
    lexer = CalcLexer()
    parser = CalcParser()

    tokens = lexer.tokenize(data)
    for tok in tokens:
        print(tok)

    result = parser.parse(lexer.tokenize(data))
    print(result)
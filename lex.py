# calclex.py

from sly import Lexer

class CalcLexer(Lexer):
    # Set of token names.   This is always required
    tokens = { 
               ID, ASSIGN, NUMBER,

               SIGNED, UNSIGNED,
               STRUCT, BOOL, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE,

               POINTER,

               LPAREN, RPAREN, 
               LBRACE, RBRACE,
               LBRACKET, RBRACKET, 
               SEMI, COMMA, COLON
             }


    # String containing ignored characters between tokens
    ignore = ' \t'

    # Regular expression rules for tokens
    ID      = r'[a-zA-Z_][a-zA-Z0-9_]*'
    NUMBER  = r'\d+'
    ASSIGN  = r'='

    # Operators
    POINTER = r'\*'

    # Delimiters
    LPAREN            = r'\('
    RPAREN            = r'\)'
    LBRACE            = r'\{'
    RBRACE            = r'\}'
    LBRACKET          = r'\['
    RBRACKET          = r'\]'
    SEMI              = r';'
    COMMA             = r','
    COLON             = r':'

    # Keywords
    ID['signed'] = SIGNED
    ID['unsigned'] = UNSIGNED

    # Types
    ID['struct'] = STRUCT
    ID['bool'] = BOOL
    ID['char'] = CHAR
    ID['short'] = SHORT
    ID['int'] = INT
    ID['long'] = LONG
    ID['float'] = FLOAT
    ID['double'] = DOUBLE

    # Define a rule so we can track line numbers
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)


    def error(self, t):
        print('Line %d: Bad character %r' % (self.lineno, t.value[0]))
        self.index += 1

if __name__ == '__main__':
    data = '''
struct simple2 {
    char* str;
    int arr[3];
    struct simple1 another;
};
'''
    lexer = CalcLexer()
    for tok in lexer.tokenize(data):
        print(tok)
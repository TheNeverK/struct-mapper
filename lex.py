# calclex.py

from sly import Lexer

class CalcLexer(Lexer):
    # Set of token names.   This is always required
    tokens = { 
               ID, ASSIGN, NUMBER, CHARACTER,

               SIGNED, UNSIGNED, INCLUDE,
               STRUCT, BOOL, CHAR, SHORT, 
               INT, LONG, FLOAT, DOUBLE, VOID,
               
               INCLUDE, LIB_REFERENCE,

               POINTER,

               LPAREN, RPAREN, 
               LBRACE, RBRACE,
               LBRACKET, RBRACKET, 
               SEMI, COMMA, COLON,
               HASH, DOT
             }


    # String containing ignored characters between tokens
    ignore = ' \t'

    # Regular expression rules for tokens
    ID      = r'[a-zA-Z_][a-zA-Z0-9_]*'
    NUMBER  = r'\d+'
    CHARACTER    = r'\'[^\']{1,1}\''
    ASSIGN  = r'='

    # Operators
    POINTER = r'\*'

    # Reference
    INCLUDE = r'\#include'
    LIB_REFERENCE = r'\<[a-z.]+>'

    # Delimiters
    LPAREN            = r'\('
    RPAREN            = r'\)'
    LBRACE            = r'\{'
    RBRACE            = r'\}'
    LBRACKET          = r'\['
    RBRACKET          = r'\]'
    SEMI              = r';'
    COMMA             = r','
    DOT               = r'.'
    COLON             = r':'
    HASH              = r'#'

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
    ID['void'] = VOID

    # Define a rule so we can track line numbers
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)


    def error(self, t):
        print('Line %d: Bad character %r' % (self.lineno, t.value[0]))
        self.index += 1

if __name__ == '__main__':
    data = '''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>

struct simple2 {
    char* str;
    int arr[3];
    struct simple1 another;
};
'''
    lexer = CalcLexer()
    for tok in lexer.tokenize(data):
        print(tok)
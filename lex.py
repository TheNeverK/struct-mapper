from sly import Lexer

oct = r'[0-7]'
dec = r'[0-9]'
non_zero = r'[1-9]'
alpha = r'[a-zA-Z_]'
alpha_num = r'[a-zA-Z_0-9]'
hex = r'[a-fA-F0-9]'
hex_prefix = r'(0[xX])'
exponent = fr'([Ee][+-]?{dec}+)'
hex_exponent = fr'([Pp][+-]?{dec}+)'
float_suffix = r'(f|F|l|L)'
int_suffix = r'(((u|U)(l|L|ll|LL)?)|((l|L|ll|LL)(u|U)?))'
char_prefix = r'(u|U|L)'
string_prefix = r'(u8|u|U|L)'
escaped = r'(\\([\'"\?\\abfnrtv]|[0-7]{1,3}|x[a-fA-F0-9]+))'
whitespace = r'[ \t\v\n\f]'


def _(*args): ...


class CalcLexer(Lexer):
    # Set of token names.   This is always required
    tokens = {
        ID, AUTO, BREAK, CASE, CHAR, CONST, CONTINUE, DEFAULT, DO,
        DOUBLE, ELSE, ENUM, EXTERN, FLOAT, FOR, GOTO, IF,
        INLINE, INT, LONG, REGISTER, RESTRICT, RETURN, SHORT,
        SIGNED, SIZEOF, STATIC, STRUCT, SWITCH, TYPEDEF, UNION,
        UNSIGNED, VOID, VOLATILE, WHILE, ALIGNAS, ALIGNOF, ATOMIC,
        BOOL, COMPLEX, GENERIC, IMAGINARY, NORETURN, STATIC_ASSERT,
        THREAD_LOCAL, FUNC_NAME, I_CONSTANT, F_CONSTANT, STRING_LITERAL,
        ELLIPSIS, RIGHT_ASSIGN, LEFT_ASSIGN, ADD_ASSIGN, SUB_ASSIGN,
        MUL_ASSIGN, DIV_ASSIGN, MOD_ASSIGN, AND_ASSIGN, XOR_ASSIGN,
        OR_ASSIGN, RIGHT_OP, LEFT_OP, INC_OP, DEC_OP, PTR_OP, AND_OP,
        OR_OP, LE_OP, GE_OP, EQ_OP, NE_OP
    }

    literals = {
        ';', '{', '}', ',',
        ':', '=', '(', ')',
        '[', ']', '.', '&',
        '!', '~', '-', '+',
        '*', '/', '%', '<',
        '>', '^', '|', '?',
    }

    # Ignored characters between tokens
    ignore = ' \t\v\f'

    ignore_comment = r'//.*'
    ignore_multiline_comment = r'/\*[\S\s]*\*/'

    # Regular expression rules for tokens

    AUTO = r'auto'
    BREAK = r'break'
    CASE = r'case'
    CHAR = r'char'
    CONST = r'const'
    CONTINUE = r'continue'
    DEFAULT = r'default'
    DO = r'do'
    DOUBLE = r'double'
    ELSE = r'else'
    ENUM = r'enum'
    EXTERN = r'extern'
    FLOAT = r'float'
    FOR = r'for'
    GOTO = r'goto'
    IF = r'if'
    INLINE = r'inline'
    INT = r'int'
    LONG = r'long'
    REGISTER = r'register'
    RESTRICT = r'restrict'
    RETURN = r'return'
    SHORT = r'short'
    SIGNED = r'signed'
    SIZEOF = r'sizeof'
    STATIC = r'static'
    STRUCT = r'struct'
    SWITCH = r'switch'
    TYPEDEF = r'typedef'
    UNION = r'union'
    UNSIGNED = r'unsigned'
    VOID = r'void'
    VOLATILE = r'volatile'
    WHILE = r'while'
    ALIGNAS = r'_Alignas'
    ALIGNOF = r'_Alignof'
    ATOMIC = r'_Atomic'
    BOOL = r'_Bool'
    COMPLEX = r'_Complex'
    GENERIC = r'_Generic'
    IMAGINARY = r'_Imaginary'
    NORETURN = r'_Noreturn'
    STATIC_ASSERT = r'_Static_assert'
    THREAD_LOCAL = r'_Thread_local'
    FUNC_NAME = r'__func__'

    ID = fr'{alpha}{alpha_num}*'

    @_(fr'{hex_prefix}{hex}+{int_suffix}?',
       fr'{non_zero}{dec}*{int_suffix}?',
       fr'0{oct}*{int_suffix}?',
       fr'{char_prefix}?\'([^\'\\\n]|{escaped})+\'')
    def I_CONSTANT(self, t):
        return t

    @_(fr'{dec}+{exponent}{float_suffix}?',
       fr'{dec}*\.{dec}+{exponent}?{float_suffix}?',
       fr'{dec}+\.{exponent}?{float_suffix}?',
       fr'{hex_prefix}{hex}+{hex_exponent}{float_suffix}?',
       fr'{hex_prefix}{hex}*\.{hex}+{hex_exponent}{float_suffix}?',
       fr'{hex_prefix}{hex}+\.{hex_exponent}{float_suffix}?')
    def F_CONSTANT(self, t):
        return t

    @_(fr'({string_prefix}?"([^"\\\n]|{escaped})*"{whitespace}*)+')
    def STRING_LITERAL(self, t):
        return t

    ELLIPSIS = r'\.\.\.'
    RIGHT_ASSIGN = r'>>='
    LEFT_ASSIGN = r'<<='
    ADD_ASSIGN = r'\+='
    SUB_ASSIGN = r'-='
    MUL_ASSIGN = r'\*='
    DIV_ASSIGN = r'/='
    MOD_ASSIGN = r'%='
    AND_ASSIGN = r'&='
    XOR_ASSIGN = r'^='
    OR_ASSIGN = r'\|='
    RIGHT_OP = r'>>'
    LEFT_OP = r'<<'
    INC_OP = r'\+\+'
    DEC_OP = r'--'
    PTR_OP = r'->'
    AND_OP = r'&&'
    OR_OP = r'\|\|'
    LE_OP = r'<='
    GE_OP = r'>='
    EQ_OP = r'=='
    NE_OP = r'!='

    @_(r'<%')
    def LEGACY_CURLY_L(self, t):
        t.type = '{'
        return t

    @_(r'%>')
    def LEGACY_CURLY_R(self, t):
        t.type = '}'
        return t

    @_(r'<:')
    def LEGACY_BRACE_L(self, t):
        t.type = '['
        return t

    @_(r':>')
    def LEGACY_BRACE_R(self, t):
        t.type = ']'
        return t

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

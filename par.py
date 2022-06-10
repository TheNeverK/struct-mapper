from collections import Counter
from dataclasses import fields
from msilib.schema import Error
from lex import CalcLexer
from sly import Parser
from pathlib import Path
import json

# Doesn't handle predefined typedefs and enums

counters = {
    'struct': 0,
    'field': 0,
}

registered = {
    'struct': {},
    'union': {},
    'enum': {},
}

simplified_types = {}


def add_to_simplified(name, ast):
    simplified_types[name] = simplify_fields(ast)


def simplify_fields(ast):
    type_desc = {}
    for field in ast:
        if (field['meta'] != 'field'):
            continue

        spec_meta = field['specifiers'][0]['meta']
        is_compound = spec_meta == 'compound_type'
        for spec in field['specifiers']:
            if (spec['meta'] != spec_meta):
                raise 'Cannot mix primitive and compound type specifiers (i.e. "int" and "struct")'

        field_type = None
        if is_compound:
            spec_meta = field['specifiers'][0]['type']
            if (spec_meta['fields'] is None):
                field_type = fetch_existing(
                    spec_meta['name']['name'])
            else:
                field_type = simplify_fields(spec_meta['fields'])

        else:
            combined_spec = [spec['type'] for spec in field['specifiers']]
            field_type = determine_type(combined_spec)

        declarators = field['declarators']
        if type(declarators) is not list:
            declarators = [declarators]

        for decl in declarators:
            size = None
            array_size = 0
            name = ''
            is_pointer = False
            pointer_type = ''
            type_override = None
            if decl['meta'] != 'field_declarator':
                continue

            if decl['is_bit_field']:
                size = int(decl['bits'])

            decl = decl['declarator']
            if decl['is_pointer']:
                size = lookup_type_size('pointer')
                is_pointer = True
                pointer_type = ' '.join(decl['pointer'])

            decl = decl['direct']

            if decl['meta'] == 'function_decl':
                # has to be a pointer
                decl = decl['name']
                size = lookup_type_size('pointer')
                is_pointer = True
                pointer_type = ' '.join(decl['pointer'])
                decl = decl['direct']
                type_override = f'function_pointer {field_type["type"]}()'

            if decl['meta'] == 'array':
                array_size = decl['count'][0]['value']
                name = decl['name']['name']

                type_desc[name] = {
                    'type': 'array',
                    'element_count': array_size,
                    'element_def': field_type
                }
            elif decl['meta'] == 'identifier':
                name = decl['name']
                type_desc[name] = field_type.copy()
                if size is not None:
                    type_desc[name]['size'] = size
                if is_pointer:
                    type_desc[name]['is_pointer'] = True
                    type_desc[name]['pointer'] = pointer_type
                if type_override is not None:
                    type_desc[name]['type'] = type_override

    return type_desc


def fetch_existing(name):
    t = simplified_types.get(name)
    if t is None:
        return unknown_type(name, f"Type '{name}' is not defined")
    return t


def determine_type(arr):
    if 'void' in arr:
        if len(arr) > 1:
            return unknown_type(arr, 'Invalid type. "void" cannot be combined with anything else.')
        return lookup_type('void', arr)

    forbidden = [
        ['long', 'short'],
        ['signed', 'unsigned'],
        ['float', 'double'],
        ['float', 'long'],
        ['char', 'short'],
        ['char', 'long'],
        ['char', 'int'],
    ]

    counts = Counter(arr)
    for (key, count) in counts.items():
        if (key == 'long' and count > 2):
            return unknown_type(arr, 'Invalid type. "long" may appear only twice.')
        elif count > 1:
            return unknown_type(arr, 'Invalid type. "{key}" may appear only once.')

    for lst in forbidden:
        if all([key in arr for key in lst]):
            s = '", "'.join(lst)
            return unknown_type(arr, f'Types "{s}" cannot be used at the same time.')

    allowed_ints = ['int', 'short', 'signed', 'unsigned', 'char']
    allowed_floats = ['float', 'double']
    is_complex = '_Complex' in arr
    is_bool = '_Bool' in arr
    filtered = list(filter(lambda s: s != '_Complex', arr))
    is_long = 'long' in arr
    is_long_long = counts['long'] == 2
    is_double = 'double' in arr
    is_long_double = is_double and is_long and not is_long_long

    is_int = all([s in allowed_ints for s in filtered]) or is_long
    is_float = all([s in allowed_floats for s in filtered]) or is_long_double

    if is_long_long and counts['double'] == 1:
        return unknown_type(arr, '"long long double" is not allowed.')

    if (not any([is_bool, is_long, is_int, is_float, is_complex])):
        return unknown_type(arr, 'Type is not allowed.')

    result = None
    if is_int:
        if 'char' in arr:
            result = lookup_type('char', arr)
        elif 'short' in arr:
            result = lookup_type('short', arr)
        elif is_long_long:
            result = lookup_type('long_long', arr)
        elif is_long:
            result = lookup_type('long', arr)
        else:
            return lookup_type('int', arr)

    if is_float:
        if is_long_double:
            result = lookup_type('long_double', arr)
        elif is_double:
            result = lookup_type('double', arr)
        else:
            result = lookup_type('float', arr)

    if is_complex:
        if result is not None:
            return {
                'type': f"complex({result['type']})",
                'size': result['size'] * 2
            }
        return lookup_type('complex', arr)

    return result


def unknown_type(type, msg):
    print(msg)
    print(f'Provided: {type}')
    return {
        'type': f'unknown ({type})',
        'size': 'unknown'
    }


def lookup_type(type, actual):
    return {
        'type': ' '.join(actual),
        'size': lookup_type_size(type)
    }


size_lookup = None


def lookup_type_size(type):
    if size_lookup is None:
        return 0
    size = size_lookup.get(type)
    if size is None:
        print(f'Size of type "{type}" was not found in the lookup file.')
        return 0
    return size


def _(): ...


def declaration(specifiers, init_declarators):
    if (specifiers[0]['meta'] == 'compound_type' and specifiers[0]['type']['meta'] == 'struct'):
        type = specifiers[0]['type']
        add_to_simplified(type['name']['name'], type['fields'])

    return {
        'meta': 'declaration',
        'specifiers': specifiers,
        'init': init_declarators
    }


def primitive_type(type):
    return {
        'meta': 'primitive_type',
        'type': type,
    }


def compound_type(type):
    kind = type['meta']
    name = type['name']['name']
    if type['fields'] is not None:
        registered[kind][name] = type

    return {
        'meta': 'compound_type',
        'type': type,
    }


def struct_or_union(type, name, declaration_list):
    if name == None or name == '':
        name = id(f"anonymous_{counters['struct']}")
        counters['struct'] += 1
    return {
        'meta': type,
        'name': name,
        'fields': declaration_list
    }


def field(specifiers, declarators):
    if declarators == None or declarators.count == 0:
        declarators = id([f"anonymous_{counters['field']}"])
        counters['field'] += 1
    return {
        'meta': 'field',
        'specifiers': specifiers,
        'declarators': declarators
    }


def field_declarator(declarator, bits):
    return {
        'meta': 'field_declarator',
        'declarator': declarator,
        'bits': bits,
        'is_bit_field': bits is not None
    }


def declarator(pointer, direct_declarator):
    return {
        'meta': 'declarator',
        'direct': direct_declarator,
        'is_pointer': pointer is not None,
        'pointer': pointer,
    }


def array(name, count):
    return {
        'meta': 'array',
        'name': name,
        'count': count
    }


def func(name, arguments):
    return {
        'meta': 'function_decl',
        'name': name,
        'arguments': arguments
    }


def id(name):
    return {
        'meta': 'identifier',
        'name': name
    }


def expression(type, left, op, right):
    return {
        'meta': f'{type}_expression',
        'left': left,
        'op': op,
        'right': right
    }


def conditional(condition, true, false):
    return {
        'meta': 'conditional_expression',
        'condition': condition,
        'true': true,
        'false': false,
    }


def cast(cast_to, expression):
    return {
        'meta': 'cast',
        'expression': expression,
        'cast_to': cast_to
    }


def unary_expression(op, right):
    return {
        'meta': 'unary_expression',
        'op': op,
        'right': right
    }


def function_call(name, args):
    return {
        'meta': 'function_call',
        'name': name,
        'arguments': args
    }


def const(value):
    return {
        'meta': 'const',
        'value': value
    }


def string_literal(value):
    return {
        'meta': 'string_literal',
        'value': value
    }


def generic_selection(expression, assoc_list):
    return {
        'meta': 'generic_selection',
        'expression': expression,
        'assoc_list': assoc_list
    }


def compound_literal(type_name, initializer_list):
    return {
        'meta': 'compound_literal',
        'type_name': type_name,
        'initializer_list': initializer_list
    }


def subscript_operator(base_expression, subscript_expression):
    return {
        'meta': 'subscript_operator',
        'base_expression': base_expression,
        'subscript_expression': subscript_expression
    }


def post_inc_dec(left, op):
    return {
        'meta': 'post_inc_dec',
        'left': left,
        'op': op,
    }


def member_access(member_of, op, member_name):
    return {
        'meta': 'member_access',
        'member_of': member_of,
        'op': op,
        'member_name': member_name
    }


class CalcParser(Parser):
    tokens = CalcLexer.tokens
    # debugfile = 'parser.out'
    start = 'translation_unit'

    @_('ID')
    def primary_expression(self, p):
        return id(p[0])

    @_('constant',
       'string',
       '"(" expression ")"',
       'generic_selection')
    def primary_expression(self, p):
        return p[0]

    @_('I_CONSTANT', 'F_CONSTANT',
       #    'ENUMERATION_CONSTANT'
       )
    def constant(self, p):
        return const(p[0])

    @_('ID')
    def enumeration_constant(self, p):
        return id(p.ID)

    @_('STRING_LITERAL', 'FUNC_NAME')
    def string(self, p):
        return string_literal(p[0])

    @_('GENERIC "(" assignment_expression "," generic_assoc_list ")"')
    def generic_selection(self, p):
        return generic_selection(p[2], p[4])

    @_('generic_association')
    def generic_assoc_list(self, p):
        return {p.generic_association[0]: p.generic_association[1]}

    @_('generic_assoc_list "," generic_association')
    def generic_assoc_list(self, p):
        p.generic_assoc_list[p.generic_association[0]
                             ] = p.generic_association[1]
        return p.generic_assoc_list

    @_('type_name ":" assignment_expression',
       'DEFAULT ":" assignment_expression')
    def generic_association(self, p):
        return (p[0], p.assignment_expression)

    @_('primary_expression')
    def postfix_expression(self, p):
        return p.primary_expression

    @_('postfix_expression "[" expression "]"')
    def postfix_expression(self, p):
        return subscript_operator(p[0], p[2])

    @_('postfix_expression "(" ")"')
    def postfix_expression(self, p):
        return function_call(p[0], None)

    @_('postfix_expression "(" argument_expression_list ")"')
    def postfix_expression(self, p):
        return function_call(p[0], p[2])

    @_('postfix_expression "." ID',
       'postfix_expression PTR_OP ID')
    def postfix_expression(self, p):
        return member_access(p[0], p[1], p[2])

    @_('postfix_expression INC_OP',
       'postfix_expression DEC_OP')
    def postfix_expression(self, p):
        return post_inc_dec(p[0], p[1])

    @_('"(" type_name ")" "{" initializer_list "}"',
       '"(" type_name ")" "{" initializer_list "," "}"')
    def postfix_expression(self, p):
        return compound_literal(p[1], p[4])

    @_('assignment_expression')
    def argument_expression_list(self, p):
        return [p.assignment_expression]

    @_('argument_expression_list "," assignment_expression')
    def argument_expression_list(self, p):
        return p.argument_expression_list + [p.assignment_expression]

    @_('postfix_expression')
    def unary_expression(self, p):
        return p.postfix_expression

    @_('INC_OP unary_expression',
       'DEC_OP unary_expression',
       'unary_operator cast_expression',
       'SIZEOF unary_expression')
    def unary_expression(self, p):
        return unary_expression(p[0], p[1])

    @_('SIZEOF "(" type_name ")"',
       'ALIGNOF "(" type_name ")"')
    def unary_expression(self, p):
        return unary_expression(p[0], p[2])

    @_('"&"', '"*"', '"+"', '"-"', '"~"', '"!"')
    def unary_operator(self, p):
        return p[0]

    @_('unary_expression')
    def cast_expression(self, p):
        return p[0]

    @_('"(" type_name ")" cast_expression')
    def cast_expression(self, p):
        return cast(p[1], p[3])

    @_('cast_expression')
    def multiplicative_expression(self, p):
        return p[0]

    @_('multiplicative_expression "*" cast_expression',
       'multiplicative_expression "/" cast_expression',
       'multiplicative_expression "%" cast_expression')
    def multiplicative_expression(self, p):
        return expression('multiplicative', p[0], p[1], p[2])

    @_('multiplicative_expression')
    def additive_expression(self, p):
        return p[0]

    @_('additive_expression "+" multiplicative_expression',
       'additive_expression "-" multiplicative_expression')
    def additive_expression(self, p):
        return expression('additive', p[0], p[1], p[2])

    @_('additive_expression')
    def shift_expression(self, p):
        return p[0]

    @_('shift_expression LEFT_OP additive_expression',
       'shift_expression RIGHT_OP additive_expression')
    def shift_expression(self, p):
        return expression('shift', p[0], p[1], p[2])

    @_('shift_expression')
    def relational_expression(self, p):
        return p[0]

    @_('relational_expression "<" shift_expression',
       'relational_expression ">" shift_expression',
       'relational_expression LE_OP shift_expression',
       'relational_expression GE_OP shift_expression')
    def relational_expression(self, p):
        return expression('relational', p[0], p[1], p[2])

    @_('relational_expression')
    def equality_expression(self, p):
        return p[0]

    @_('equality_expression EQ_OP relational_expression',
       'equality_expression NE_OP relational_expression')
    def equality_expression(self, p):
        return expression('equality', p[0], p[1], p[2])

    @_('equality_expression')
    def and_expression(self, p):
        return p[0]

    @_('and_expression "&" equality_expression')
    def and_expression(self, p):
        return expression('and', p[0], p[1], p[2])

    @_('and_expression')
    def exclusive_or_expression(self, p):
        return p[0]

    @_('exclusive_or_expression "^" and_expression')
    def exclusive_or_expression(self, p):
        return expression('xor', p[0], p[1], p[2])

    @_('exclusive_or_expression')
    def inclusive_or_expression(self, p):
        return p[0]

    @_('inclusive_or_expression "|" exclusive_or_expression')
    def inclusive_or_expression(self, p):
        return expression('or', p[0], p[1], p[2])

    @_('inclusive_or_expression')
    def logical_and_expression(self, p):
        return p[0]

    @_('logical_and_expression AND_OP inclusive_or_expression')
    def logical_and_expression(self, p):
        return expression('logical_and', p[0], p[1], p[2])

    @_('logical_and_expression')
    def logical_or_expression(self, p):
        return p[0]

    @_('logical_or_expression OR_OP logical_and_expression')
    def logical_or_expression(self, p):
        return expression('logical_or', p[0], p[1], p[2])

    @_('logical_or_expression')
    def conditional_expression(self, p):
        return p[0]

    @_('logical_or_expression "?" expression ":" conditional_expression')
    def conditional_expression(self, p):
        return conditional(p[0], p[2], p[4])

    @_('conditional_expression')
    def assignment_expression(self, p):
        return p[0]

    @_('unary_expression assignment_operator assignment_expression')
    def assignment_expression(self, p):
        return expression('assignment', p[0], p[1], p[2])

    @_('"="', 'MUL_ASSIGN', 'DIV_ASSIGN',
       'MOD_ASSIGN', 'ADD_ASSIGN', 'SUB_ASSIGN',
       'LEFT_ASSIGN', 'RIGHT_ASSIGN', 'AND_ASSIGN',
       'XOR_ASSIGN', 'OR_ASSIGN')
    def assignment_operator(self, p):
        return p[0]

    @_('assignment_expression')
    def expression(self, p):
        return p[0]

    @_('expression "," assignment_expression')
    def expression(self, p):
        return ('assignment', p[0], p[1], p[2])

    @_('conditional_expression')  # with constraints??
    def constant_expression(self, p):
        return p[0]

    @_('declaration_specifiers ";"')
    def declaration(self, p):
        return declaration(p[0], None)

    @_('declaration_specifiers init_declarator_list ";"')
    def declaration(self, p):
        return declaration(p[0], p[1])

    @_('static_assert_declaration')
    def declaration(self, p):
        return ('static_assert_declaration', p[0], None)

    @_('storage_class_specifier declaration_specifiers',
       'type_specifier declaration_specifiers',
       'type_qualifier declaration_specifiers',
       'function_specifier declaration_specifiers',
       'alignment_specifier declaration_specifiers')
    def declaration_specifiers(self, p):
        return p[1] + [p[0]]

    @_('storage_class_specifier',
       'type_specifier',
       'type_qualifier',
       'function_specifier',
       'alignment_specifier')
    def declaration_specifiers(self, p):
        return [p[0]]

    @_('init_declarator')
    def init_declarator_list(self, p):
        return [p[0]]

    @_('init_declarator_list "," init_declarator')
    def init_declarator_list(self, p):
        return p[0] + [p[2]]

    @_('declarator "=" initializer')
    def init_declarator(self, p):
        return ('init_declarator', p[0], p[2])

    @_('declarator')
    def init_declarator(self, p):
        return ('init_declarator', p[0], None)

    @_('TYPEDEF', 'EXTERN', 'STATIC', 'THREAD_LOCAL', 'AUTO', 'REGISTER')
    def storage_class_specifier(self, p):
        return p[0]

    @_('VOID', 'CHAR', 'SHORT', 'INT',
       'LONG', 'FLOAT', 'DOUBLE', 'SIGNED',
       'UNSIGNED', 'BOOL', 'COMPLEX', 'IMAGINARY'  # 'TYPEDEF_NAME'
       )
    def type_specifier(self, p):
        return primitive_type(p[0])

    @_('atomic_type_specifier', 'struct_or_union_specifier',
       'enum_specifier')
    def type_specifier(self, p):
        return compound_type(p[0])

    @_('struct_or_union "{" struct_declaration_list "}"')
    def struct_or_union_specifier(self, p):
        return struct_or_union(p[0], None, p.struct_declaration_list)

    @_('struct_or_union ID "{" struct_declaration_list "}"')
    def struct_or_union_specifier(self, p):
        return struct_or_union(p[0], id(p.ID), p.struct_declaration_list)

    @_('struct_or_union ID')
    def struct_or_union_specifier(self, p):
        return struct_or_union(p[0], id(p.ID), None)

    @_('STRUCT', 'UNION')
    def struct_or_union(self, p):
        return p[0]

    @_('struct_declaration')
    def struct_declaration_list(self, p):
        return [p.struct_declaration]

    @_('struct_declaration_list struct_declaration')
    def struct_declaration_list(self, p):
        return p.struct_declaration_list + [p.struct_declaration]

    @_('specifier_qualifier_list ";"')
    def struct_declaration(self, p):
        return field(p.specifier_qualifier_list, None)

    @_('specifier_qualifier_list struct_declarator_list ";"')
    def struct_declaration(self, p):
        return field(p.specifier_qualifier_list, p.struct_declarator_list)

    @_('static_assert_declaration')
    def struct_declaration(self, p):
        return ('static_assert_declaration', p[0], None)

    @_('type_specifier specifier_qualifier_list')
    def specifier_qualifier_list(self, p):
        return [p.type_specifier] + p.specifier_qualifier_list

    @_('type_specifier')
    def specifier_qualifier_list(self, p):
        return [p.type_specifier]

    @_('type_qualifier specifier_qualifier_list')
    def specifier_qualifier_list(self, p):
        return [p.type_qualifier] + p.specifier_qualifier_list

    @_('type_qualifier')
    def specifier_qualifier_list(self, p):
        return [p.type_qualifier]

    @_('struct_declarator')
    def struct_declarator_list(self, p):
        return [p.struct_declarator]

    @_('struct_declarator_list "," struct_declarator')
    def struct_declarator_list(self, p):
        return p.struct_declarator_list + [p.struct_declarator]

    @_('":" constant_expression')
    def struct_declarator(self, p):
        return field_declarator(None, p.constant_expression)

    @_('declarator ":" constant_expression')
    def struct_declarator(self, p):
        return field_declarator(p.declarator, p.constant_expression)

    @_('declarator')
    def struct_declarator(self, p):
        return field_declarator(p.declarator, None)

    @_('ENUM "{" enumerator_list "}"', 'ENUM "{" enumerator_list "," "}"')
    def enum_specifier(self, p):
        return (p[0], None, p[2])

    @_('ENUM ID "{" enumerator_list "}"', 'ENUM ID "{" enumerator_list "," "}"')
    def enum_specifier(self, p):
        return (p[0], p[1], p[3])

    @_('ENUM ID')
    def enum_specifier(self, p):
        return (p[0], p[1], None)

    @_('enumerator')
    def enumerator_list(self, p):
        return [p[0]]

    @_('enumerator_list "," enumerator')
    def enumerator_list(self, p):
        return p[0] + [p[2]]

    @_('enumeration_constant "=" constant_expression')
    def enumerator(self, p):
        return (p[0], p[2])

    @_('enumeration_constant')
    def enumerator(self, p):
        return (p[0], None)

    @_('ATOMIC "(" type_name ")"')
    def atomic_type_specifier(self, p):
        return (p[0], p[2])

    @_('CONST', 'RESTRICT', 'VOLATILE', 'ATOMIC')
    def type_qualifier(self, p):
        return p[0]

    @_('INLINE', 'NORETURN')
    def function_specifier(self, p):
        return p[0]

    @_('ALIGNAS "(" type_name ")"',
       'ALIGNAS "(" constant_expression ")"')
    def alignment_specifier(self, p):
        return (p[0], p[2])

    @_('pointer direct_declarator')
    def declarator(self, p):
        return declarator(p[0], p[1])

    @_('direct_declarator')
    def declarator(self, p):
        return declarator(None, p[0])

    @_('ID')
    def direct_declarator(self, p):
        return id(p.ID)

    @_('"(" declarator ")"')
    def direct_declarator(self, p):
        return p.declarator

    @_('direct_declarator "[" "]"')
    def direct_declarator(self, p):
        return array(p.direct_declarator, None)

    @_('direct_declarator "[" "*" "]"',
       'direct_declarator "[" type_qualifier_list "]"',
       'direct_declarator "[" assignment_expression "]"')
    def direct_declarator(self, p):
        return array(p.direct_declarator, (p[2],))

    @_('direct_declarator "[" STATIC assignment_expression "]"',
       'direct_declarator "[" type_qualifier_list "*" "]"',
       'direct_declarator "[" type_qualifier_list assignment_expression "]"')
    def direct_declarator(self, p):
        return array(p.direct_declarator, (p[2], p[3]))

    @_('direct_declarator "[" STATIC type_qualifier_list assignment_expression "]"',
       'direct_declarator "[" type_qualifier_list STATIC assignment_expression "]"')
    def direct_declarator(self, p):
        return array(p.direct_declarator, (p[2], p[3], p[4]))

    @_('direct_declarator "(" ")"')
    def direct_declarator(self, p):
        return func(p.direct_declarator, None)

    @_('direct_declarator "(" identifier_list ")"',
       'direct_declarator "(" parameter_type_list ")"')
    def direct_declarator(self, p):
        return func(p.direct_declarator, p[2])

    @_('"*" type_qualifier_list pointer')
    def pointer(self, p):
        return [p[0]] + p[1] + p.pointer

    @_('"*" type_qualifier_list')
    def pointer(self, p):
        return [p[0]] + p[1]

    @_('"*" pointer')
    def pointer(self, p):
        return [p[0]] + p.pointer

    @_('"*"')
    def pointer(self, p):
        return [p[0]]

    @_('type_qualifier')
    def type_qualifier_list(self, p):
        return [p[0]]

    @_('type_qualifier_list type_qualifier')
    def type_qualifier_list(self, p):
        return p[0] + [p[1]]

    @_('parameter_list "," ELLIPSIS')
    def parameter_type_list(self, p):
        return p[0] + [p[2]]

    @_('parameter_list')
    def parameter_type_list(self, p):
        return p[0]

    @_('parameter_declaration')
    def parameter_list(self, p):
        return [p[0]]

    @_('parameter_list "," parameter_declaration')
    def parameter_list(self, p):
        return p[0] + [p[2]]

    @_('declaration_specifiers declarator',
       'declaration_specifiers abstract_declarator')
    def parameter_declaration(self, p):
        return (p[0], None)

    @_('declaration_specifiers')
    def parameter_declaration(self, p):
        return (p[0], None)

    @_('ID')
    def identifier_list(self, p):
        return [id(p.ID)]

    @_('identifier_list "," ID')
    def identifier_list(self, p):
        return p.identifier_list + [id(p.ID)]

    @_('specifier_qualifier_list abstract_declarator')
    def type_name(self, p):
        return ('type_name', p[0], p[1])

    @_('specifier_qualifier_list')
    def type_name(self, p):
        return ('type_name', p[0], None)

    @_('pointer direct_abstract_declarator')
    def abstract_declarator(self, p):
        return (p[0], p[1])

    @_('pointer')
    def abstract_declarator(self, p):
        return (p[0], None)

    @_('direct_abstract_declarator')
    def abstract_declarator(self, p):
        return (None, p[0])

    @_('"(" abstract_declarator ")"')
    def direct_abstract_declarator(self, p):
        return p.abstract_declarator

    @_('"[" "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', None, None)

    @_('"[" "*" "]"',
       '"[" type_qualifier_list "]"',
       '"[" assignment_expression "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', None, (p[1],))

    @_('"[" STATIC assignment_expression "]"',
       '"[" type_qualifier_list assignment_expression "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', p.direct_abstract_declarator, (p[1], p[2]))

    @_('"[" STATIC type_qualifier_list assignment_expression "]"',
       '"[" type_qualifier_list STATIC assignment_expression "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', p.direct_abstract_declarator, (p[1], p[2], p[3]))

    @_('direct_abstract_declarator "[" "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', p.direct_abstract_declarator, None)

    @_('direct_abstract_declarator "[" "*" "]"',
       'direct_abstract_declarator "[" type_qualifier_list "]"',
       'direct_abstract_declarator "[" assignment_expression "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', p.direct_abstract_declarator, (p[2],))

    @_('direct_abstract_declarator "[" STATIC assignment_expression "]"',
       'direct_abstract_declarator "[" type_qualifier_list assignment_expression "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', p.direct_abstract_declarator, (p[2], p[3]))

    @_('direct_abstract_declarator "[" STATIC type_qualifier_list assignment_expression "]"',
       'direct_abstract_declarator "[" type_qualifier_list STATIC assignment_expression "]"')
    def direct_abstract_declarator(self, p):
        return ('abstract_array', p.direct_abstract_declarator, (p[2], p[3], p[4]))

    @_('"(" ")"')
    def direct_abstract_declarator(self, p):
        return ('abstract_function', None, None)

    @_('"(" parameter_type_list ")"')
    def direct_abstract_declarator(self, p):
        return ('abstract_function', None, p.parameter_type_list)

    @_('direct_abstract_declarator "(" ")"')
    def direct_abstract_declarator(self, p):
        return ('abstract_function', p.direct_abstract_declarator, None)

    @_('direct_abstract_declarator "(" parameter_type_list ")"')
    def direct_abstract_declarator(self, p):
        return ('abstract_function', p.direct_abstract_declarator, p.parameter_type_list)

    @_('"{" initializer_list "}"',
       '"{" initializer_list "," "}"')
    def initializer(self, p):
        return ('initializer_list', p[1])

    @_('assignment_expression')
    def initializer(self, p):
        return ('initializer_expression', p[0])

    @_('designation initializer')
    def initializer_list(self, p):
        return [(p[0], p[1])]

    @_('initializer')
    def initializer_list(self, p):
        return [(None, p[0])]

    @_('initializer_list "," designation initializer')
    def initializer_list(self, p):
        return p[0] + [(p[2], p[3])]

    @_('initializer_list "," initializer')
    def initializer_list(self, p):
        return p[0] + [(None, p[2])]

    @_('designator_list "="')
    def designation(self, p):
        return p[0]

    @_('designator')
    def designator_list(self, p):
        return [p[0]]

    @_('designator_list designator')
    def designator_list(self, p):
        return p[0] + [p[1]]

    @_('"[" constant_expression "]"',
       '"." ID')
    def designator(self, p):
        return p[1]

    @_('STATIC_ASSERT "(" constant_expression "," STRING_LITERAL ")" ";"')
    def static_assert_declaration(self, p):
        return ('static_assert', p[2], p[4])

    @_('labeled_statement',
       'compound_statement',
       'expression_statement',
       'selection_statement',
       'iteration_statement',
       'jump_statement')
    def statement(self, p):
        return p[0]

    @_('ID ":" statement')
    def labeled_statement(self, p):
        return ('label', p[0], p[2])

    @_('CASE constant_expression ":" statement')
    def labeled_statement(self, p):
        return ('case', p[1], p[3])

    @_('DEFAULT ":" statement')
    def labeled_statement(self, p):
        return ('default', p[0], p[2])

    @_('"{" "}"')
    def compound_statement(self, p):
        return ('block', None)

    @_('"{" block_item_list "}"')
    def compound_statement(self, p):
        return ('block', p[1])

    @_('block_item')
    def block_item_list(self, p):
        return [p[0]]

    @_('block_item_list block_item')
    def block_item_list(self, p):
        return p[0] + [p[1]]

    @_('declaration', 'statement')
    def block_item(self, p):
        return p[0]

    @_('";"')
    def expression_statement(self, p):
        return ('expression', None)

    @_('expression ";"')
    def expression_statement(self, p):
        return ('expression', p[0])

    @_('IF "(" expression ")" statement ELSE statement')
    def selection_statement(self, p):
        return ('if', p[2], p[4], p[6])

    @_('IF "(" expression ")" statement')
    def selection_statement(self, p):
        return ('if', p[2], p[4], None)

    @_('SWITCH "(" expression ")" statement')
    def selection_statement(self, p):
        return ('switch', p[2], p[4])

    @_('WHILE "(" expression ")" statement')
    def iteration_statement(self, p):
        return ('while', p[2], p[4])

    @_('DO statement WHILE "(" expression ")" ";"')
    def iteration_statement(self, p):
        return ('do_while', p[4], p[2])

    @_('FOR "(" expression_statement expression_statement ")" statement')
    def iteration_statement(self, p):
        return ('for', (p[2], p[3], None), p[5])

    @_('FOR "(" expression_statement expression_statement expression ")" statement')
    def iteration_statement(self, p):
        return ('for', (p[2], p[3], p[4]), p[6])

    @_('FOR "(" declaration expression_statement ")" statement')
    def iteration_statement(self, p):
        return ('for', (p[2], p[3], None), p[5])

    @_('FOR "(" declaration expression_statement expression ")" statement')
    def iteration_statement(self, p):
        return ('for', (p[2], p[3], p[4]), p[6])

    @_('GOTO ID ";"',
       'RETURN expression ";"')
    def jump_statement(self, p):
        return (p[0], p[1])

    @_('CONTINUE ";"',
       'BREAK ";"',
       'RETURN ";"')
    def jump_statement(self, p):
        return (p[0], None)

    @_('external_declaration')
    def translation_unit(self, p):
        return [p[0]]

    @_('translation_unit external_declaration')
    def translation_unit(self, p):
        return p[0] + [p[1]]

    @_('function_definition',
       'declaration')
    def external_declaration(self, p):
        return p[0]

    @_('declaration_specifiers declarator declaration_list compound_statement')
    def function_definition(self, p):
        return ('function', p[0], p[1], p[2], p[3])

    @_('declaration_specifiers declarator compound_statement')
    def function_definition(self, p):
        return ('function', p[0], p[1], None, p[2])

    @_('declaration')
    def declaration_list(self, p):
        return [p[0]]

    @_('declaration_list declaration')
    def declaration_list(self, p):
        return p[0] + [p[1]]


if __name__ == '__main__':
    data = Path("examples/simple_multi.c").read_text()
    with open('lookup.json', 'r') as file:
        size_lookup = json.load(file)

    lexer = CalcLexer()
    parser = CalcParser()

    tokens = lexer.tokenize(data)
    # for tok in tokens:
    #     print(tok)

    result = parser.parse(lexer.tokenize(data))
    with open('ast.json', 'w') as file:
        json.dump(result, file, indent=2)

    # print(json.dumps(registered, indent=2))
    with open('result.json', 'w') as file:
        json.dump(simplified_types, file, indent=2)

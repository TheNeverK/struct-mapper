# Struct Mapper

Python tool to convert C structs into JSON descriptions

## Project structure

- Parser and lexer (ply 4.0 or sly)
  - grammar: http://www.quut.com/c/ANSI-C-grammar-y-2011.html
  - similar project: https://github.com/eliben/pycparser
- Analyze results of parser and add metadata
- Serialize dictionaries to JSON and save to file (maybe format?)

- (optional) run preprocessor on input files

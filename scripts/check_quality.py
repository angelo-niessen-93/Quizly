"""Check the DoD's function size, naming and documentation requirements."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def python_files():
    """Inspect project code while excluding environments and dependencies."""
    yield ROOT / 'manage.py'
    for folder in ('apps', 'quizly', 'scripts'):
        yield from (ROOT / folder).rglob('*.py')


def function_errors(node):
    """Report violations for one function, including test helpers."""
    if node.end_lineno - node.lineno + 1 > 14:
        yield 'function exceeds 14 physical lines'
    if not re.fullmatch(r'_?[a-z][a-z0-9_]*|__[a-z_]+__', node.name):
        yield 'function name must use snake_case'
    if not ast.get_docstring(node):
        yield 'function needs a descriptive docstring'


def inspect_file(path):
    """Attach locations to function-level quality errors."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for error in function_errors(node):
                yield f'{path.relative_to(ROOT)}:{node.lineno}: {error}'


def main():
    """Exit unsuccessfully if any project function violates the DoD."""
    errors = [error for path in python_files() for error in inspect_file(path)]
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    print('All functions: <=14 lines, snake_case and docstrings.')


if __name__ == '__main__':
    main()

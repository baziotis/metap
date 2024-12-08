import ast, astor
import lib


def _retx(x):
  stmt: ast.AST = lib.replace_bindings(ast.parse('return _metap_x'), locals())
  return stmt


def _ret0():
  stmt: ast.AST = lib.replace_bindings(ast.parse('return 0'), locals())
  return stmt


def _ret_ifnf(x):
  stmt: ast.AST = lib.replace_bindings(ast.parse(
      """if x is not False:
  return x"""), locals())
  return stmt

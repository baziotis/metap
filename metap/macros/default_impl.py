
from . import rt_lib

import ast, astor


def _ret_ifn(x):
  stmt: ast.AST = rt_lib.replace_bindings(ast.parse(
      """if _metap_x is None:
  return None"""), locals())
  return stmt


def _ret_ifnn(x):
  stmt: ast.AST = rt_lib.replace_bindings(ast.parse(
      """_tmp = _metap_x
if _tmp is not None:
  return _tmp"""), locals())
  return stmt


def _ret_iff(x):
  stmt: ast.AST = rt_lib.replace_bindings(ast.parse(
      """if _metap_x == False:
  return False"""), locals())
  return stmt


def _ret_ift(x):
  stmt: ast.AST = rt_lib.replace_bindings(ast.parse(
      """if _metap_x == True:
  return True"""), locals())
  return stmt


def _mprint(x):
  e = ast.Expr(value=x)
  src = astor.to_source(e).strip()
  cnode = ast.Constant(value=src + ':')
  stmt: ast.AST = rt_lib.replace_bindings(ast.parse(
      'print(_metap_cnode, _metap_x)'), locals())
  return stmt

macro_defs = {'_mprint', '_ret_ift', '_ret_ifnn', '_ret_ifn', '_ret_iff'}


import ast
from . import rt_lib

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

macro_defs = {'_ret_ift', '_ret_iff', '_ret_ifn', '_ret_ifnn'}

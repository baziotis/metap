import ast, astor
import lib

def _retx(x):
  stmt: NODE = { return <x> }
  return stmt

def _ret0():
  stmt: NODE = { return 0 }
  return stmt

def _ret_ifnf(x):
  stmt: NODE = {
if x is not False:
  return x
}
  return stmt
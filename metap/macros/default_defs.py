import ast, astor

def _ret_ifn(x):
  stmt : NODE = {
if <x> is None:
  return None
}
  return stmt

def _ret_ifnn(x):
  stmt : NODE = {
_tmp = <x>
if _tmp is not None:
  return _tmp
}
  return stmt

def _ret_iff(x):
  stmt : NODE = {
if <x> == False:
  return False
}
  return stmt

def _ret_ift(x):
  stmt : NODE = {
if <x> == True:
  return True
}
  return stmt

def _mprint(x):
  e = ast.Expr(value=x)
  src = astor.to_source(e).strip()
  cnode = ast.Constant(value=src+":")
  stmt : NODE = {
print(<cnode>, <x>)
}
  return stmt
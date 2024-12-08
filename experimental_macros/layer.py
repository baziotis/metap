import ast, astor
import macros
import lib

def is_user_def_macro(name: str):
  if name.startswith('__'):
    return False
  if name in ["ast", "astor"]:
    return False
  if name.startswith('_'):
    return True
  return False

mfuncs = [f for f in dir(macros) if is_user_def_macro(f)]

def extract_val(mod):
  assert isinstance(mod, ast.Module)
  assert len(mod.body) == 1
  e = mod.body[0]
  assert isinstance(e, ast.Expr)
  return e.value

class Compiler(ast.NodeTransformer):
  def visit_Expr(self, e: ast.Expr):
    call = e.value
    if not isinstance(call, ast.Call):
      self.generic_visit(e)
      return e
    # END IF #
    func = call.func 
    if not isinstance(func, ast.Name):
      self.generic_visit(e)
      return e
    # END IF #
    func_name = func.id
    if func_name not in mfuncs:
      self.generic_visit(e)
      return e
    # END IF #

    return getattr(macros, func_name)(*call.args)


with open('meta.py', 'r') as fp:
  meta_prog = fp.read()

t = ast.parse(meta_prog)
v = Compiler()
v.visit(t)
new_src = astor.to_source(t, indent_with=" "*2)

with open('prog.py', 'w') as fp:
  fp.write(new_src)
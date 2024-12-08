import ast

class Replacer(ast.NodeTransformer):
  def __init__(self, locals):
    ast.NodeTransformer.__init__(self)
    self.locals = locals
  
  def visit_Name(self, name: ast.Name):
    prefix = '_metap_'
    if not name.id.startswith(prefix):
      return name
    local_id = name.id[len(prefix):]
    return self.locals[local_id]

def replace_bindings(t, locals):
  v = Replacer(locals=locals)
  v.visit(t)
  return t
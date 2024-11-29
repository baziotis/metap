import ast

class RandomVisitor(ast.NodeVisitor):
  def visit_Assign(self, asgn:ast.Assign):
    for t in asgn.targets:
      self.visit(t)
    ### END FOR ###
    self.visit(asgn.value)

  def visit_BinOp(self, binop:ast.BinOp):
    self.visit(binop.left)


code = "a = 2 + 3"
t = ast.parse(code)
v = RandomVisitor()
v.visit(t)
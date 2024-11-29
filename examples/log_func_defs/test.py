import metap
import ast


class RandomVisitor(ast.NodeVisitor):

  def visit_Assign(self, asgn: ast.Assign):
    metap.indent_print()
    print('metap::FuncDef(ln=4,func=visit_Assign)')
    with metap.indent_ctx():
      for t in asgn.targets:
        self.visit(t)
      self.visit(asgn.value)

  def visit_BinOp(self, binop: ast.BinOp):
    metap.indent_print()
    print('metap::FuncDef(ln=10,func=visit_BinOp)')
    with metap.indent_ctx():
      self.visit(binop.left)


code = 'a = 2 + 3'
t = ast.parse(code)
v = RandomVisitor()
v.visit(t)

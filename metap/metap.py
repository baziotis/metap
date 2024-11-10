import ast, astor
import os



def log_ret(e, log_info):
  print(log_info)
  return e

def log_call(e, log_info):
  print(log_info)
  return e

def fmt_log_info(log_info):
  res = "metap::"
  special_keys = ["name", "fname"]
  if "fname" in log_info:
    res += log_info["fname"] + "::"
  
  main = ",".join([f"{key}={value}" for key,
                  value in log_info.items() if key not in special_keys])
  main = f"{log_info['name']}(" + main + ")"
  res += main
  return res


class LogReturnWalker(astor.TreeWalk):
  def __init__(self, include_fname=False, fname=""):
    astor.TreeWalk.__init__(self)
    self.stef_include_fname = include_fname
    self.stef_fname = fname

  def post_Return(self):
    assert hasattr(self.cur_node, 'lineno')
    lineno = self.cur_node.lineno
    log_info = {"name": "Return"}
    log_info["ln"] = lineno

    if self.stef_include_fname:
      log_info["fname"] = self.stef_fname

    out_log = fmt_log_info(log_info)

    val = self.cur_node.value
    if val is None:
      # `return` and `return None` are the same
      val = ast.Constant(value=None, kind=None)

    new_node = ast.Return(
      value=ast.Call(
        func=ast.Attribute(value=ast.Name(id="metap"), attr='log_ret'),
        args=[val, ast.Constant(value=out_log)],
        keywords=[]
      )
    )
    self.replace(new_node)

def break_cont(cur_node, kind):
  assert hasattr(cur_node, 'lineno')
  lineno = cur_node.lineno

  log_info = {"name": kind}
  log_info["ln"] = lineno

  out_log = fmt_log_info(log_info)

  print_before = ast.Expr(
    value=ast.Call(
      func=ast.Name(id="print"),
      args=[ast.Constant(value=out_log)],
      keywords=[]
    )
  )
  
  return [print_before, cur_node]

class BreakContTransformer(ast.NodeTransformer):
  def __init__(self, kind):
    ast.NodeTransformer.__init__(self)
    self.kind = kind

  def visit_Continue(self, node):
    if self.kind == "Continue":
      return break_cont(node, self.kind)
    else:
      return node

  def visit_Break(self, node):
    if self.kind == "Break":
      return break_cont(node, self.kind)
    else:
      return node

class CallSiteTransformer(ast.NodeTransformer):
  def visit_Call(self, node):
    assert hasattr(node, 'lineno')
    lineno = node.lineno

    log_info = {"name": "Call"}
    log_info["ln"] = lineno
    log_info["call"] = astor.to_source(node).strip()

    out_log = fmt_log_info(log_info)
    
    new_node = ast.Call(
        func=ast.Attribute(value=ast.Name(id="metap"), attr='log_call'),
        args=[node, ast.Constant(value=out_log)],
        keywords=[]
      )
    return new_node

class RetTransformer(ast.NodeTransformer):
  def visit_Expr(self, e):
    if not isinstance(e.value, ast.Call):
      return e
    call = e.value
    func = call.func
    if not isinstance(func, ast.Name):
      return e
    
    ret_funcs = ['__ret_ifnn', '__ret_ifn']
    if func.id not in ret_funcs:
      return e

    assert len(call.args) == 1
    assert len(call.keywords) == 0

    orig_val = call.args[0]
    var = ast.Name(id='_metap_ret')
    asgn = ast.Assign(
      targets=[var],
      value=orig_val
    )

    lineno = call.lineno
    
    if func.id == '__ret_ifnn':
      if_ = ast.If(
        test=ast.Compare(left=var, ops=[ast.IsNot()],
                        comparators=[ast.Constant(value=None)]),
        body=[ast.Return(value=var, lineno=lineno)],
        orelse=[]
      )
    else:
      if_ = ast.If(
        test=ast.Compare(left=var, ops=[ast.Is()],
                        comparators=[ast.Constant(value=None)]),
        body=[ast.Return(value=ast.Constant(value=None), lineno=lineno)],
        orelse=[]
      )
      
    return [asgn, if_]

class MetaP:
  def __init__(self, filename) -> None:
    self.filename = filename
    with open(filename, 'r') as fp:
      self.ast = ast.parse(fp.read())

  def log_returns(self, include_fname=False):
    walker = LogReturnWalker(include_fname=include_fname,
                             fname=os.path.basename(self.filename))
    walker.walk(self.ast)

  def log_breaks(self):
    transformer = BreakContTransformer("Break")
    transformer.visit(self.ast)
  
  def log_continues(self):
    transformer = BreakContTransformer("Continue")
    transformer.visit(self.ast)
  
  def log_calls(self):
    transformer = CallSiteTransformer()
    transformer.visit(self.ast)
    
  # Handles anything that is required to be transformed for the code to run
  # (i.e., any code that uses metap features)
  def compile(self):
    transformer = RetTransformer()
    transformer.visit(self.ast)

  def dump(self, filename=None):
    if not filename:
      filename = self.filename.split('.')[0] + ".metap.py"

    # Add an import to metap on the top
    self.ast.body.insert(0, ast.Import(names=[ast.Name(id="metap")]))

    with open(filename, 'w') as fp:
      src = astor.to_source(self.ast, indent_with=' ' * 2)
      fp.write(src)
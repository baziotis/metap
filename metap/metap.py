import ast, astor
import os

# print(astor.dump_tree(ast.parse("""
# if True:
#   print('a')
#   break
# """)))

def log_ret(e, log_info):
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

  # Here, we can't use the same trick as with returns (e.g., we can't have
  # `break foo()`). The intuitive solution is to insert a `print()` before the
  # return. But, then would need to deal with "where is the break nested
  # into?" and also we would mess with the nodestack of the TreeWalk. So,
  # instead we'll introduce a fake block with `if` like:
  #   if True:
  #     print(log)
  #     break


  print_before = ast.Expr(
    value=ast.Call(
      func=ast.Name(id="print"),
      args=[ast.Constant(value=out_log)],
      keywords=[]
    )
  )
  
  the_if = ast.If(
    test=ast.Constant(value=True),
    body=[print_before, cur_node],
    orelse=[]
  )

  return the_if

class BreakContWalker(astor.TreeWalk):
  def __init__(self, kind):
    astor.TreeWalk.__init__(self)
    self.kind = kind

  def post_Continue(self):
    if self.kind == "Continue":
      self.replace(break_cont(self.cur_node, self.kind))
    else:
      pass

  def post_Break(self):
    if self.kind == "Break":
      self.replace(break_cont(self.cur_node, self.kind))
    else:
      pass
    

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
    walker = BreakContWalker("Break")
    walker.walk(self.ast)
  
  def log_continues(self):
    walker = BreakContWalker("Continue")
    walker.walk(self.ast)

  def dump(self, filename=None):
    if not filename:
      filename = self.filename.split('.')[0] + ".metap.py"

    # Add an import to metap on the top
    self.ast.body.insert(0, ast.Import(names=[ast.Name(id="metap")]))

    with open(filename, 'w') as fp:
      src = astor.to_source(self.ast, indent_with=' ' * 2)
      fp.write(src)
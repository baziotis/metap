import ast, astor
import os


### HELPERS called from the generated program ###

def log_ret(e, log_info):
  print(log_info)
  return e

def log_call(lam, log_info):
  print(log_info)
  return lam()

def cvar(cond, globs, var, ift_e):
  if cond:
    globs[var] = ift_e
  return cond

def cvar2(cond, globs, var):
  globs[var] = cond
  return cond

### END HELPERS ###


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

def in_range(lineno, range):
  if len(range) == 0:
    return True
  in_r = False
  for r in range:
    if isinstance(r, int) and lineno == r:
      in_r = True
      break
    elif isinstance(r, tuple) and r[0] <= lineno <= r[1]:
      in_r = True
      break
  ### END FOR ###
  return in_r


class LogReturnWalker(astor.TreeWalk):
  def __init__(self, include_fname=False, fname="", range=[]):
    astor.TreeWalk.__init__(self)
    self.stef_include_fname = include_fname
    self.stef_fname = fname
    self.stef_range = range

  def post_Return(self):
    assert hasattr(self.cur_node, 'lineno')
    lineno = self.cur_node.lineno

    if not in_range(lineno, self.stef_range):
      return
          
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
  def __init__(self, range=[]):
    ast.NodeTransformer.__init__(self)
    self.range = range

  def visit_Call(self, node):
    assert hasattr(node, 'lineno')
    lineno = node.lineno

    if not in_range(lineno, self.range):
      return node

    log_info = {"name": "Call"}
    log_info["ln"] = lineno
    log_info["call"] = astor.to_source(node).strip()

    out_log = fmt_log_info(log_info)
    
    # Here we have to do some gymnastics. The problem is that we want the log
    # info to be printed _before_ the call happens. So, we can't just pass the
    # original node as an argument to log_call() because it will be evaluated
    # before log_call() is called, and thus before log_call() prints the info.
    # So, we wrap the original call in a lambda that we call inside log_call()
    # after we print the info.
    
    lambda_args = ast.arguments(
      args=[],
      defaults=[],
      kw_defaults=[],
      kwarg=None,
      kwonlyargs=[],
      posonlyargs=[],
      vararg=None
    )
    
    new_node = ast.Call(
        func=ast.Attribute(value=ast.Name(id="metap"), attr='log_call'),
        args=[ast.Lambda(args=lambda_args, body=node), ast.Constant(value=out_log)],
        keywords=[]
      )
    return new_node

def globals_call():
  call = ast.Call(
    func=ast.Name(id="globals"),
    args=[],
    keywords=[]
  )
  return call

class CVarTransformer(ast.NodeTransformer):
  def __init__(self):
    ast.NodeTransformer.__init__(self)
    self.if_vars = []
    self.uncond_vars = []

  def visit_Call(self, call: ast.Call):
    if not isinstance(call.func, ast.Name):
      return call
    
    if call.func.id != '_cvar':
      return call
    
    args = call.args
    assert 2 <= len(args) <= 3
    cond = args[0]
    var = args[1]
    
    assert isinstance(var, ast.Name)
    var_name = var.id
    our_name = ast.Constant(value="__metap_"+var_name)

    if len(args) == 3:
      self.if_vars.append(var.id)
      ift_e = args[2] if len(args) == 3 else cond
      new_call = ast.Call(
          func=ast.Attribute(value=ast.Name(id="metap"), attr='cvar'),
          args=[cond, globals_call(), our_name, ift_e],
          keywords=[]
        )
    else:
      self.uncond_vars.append(var.id)
      new_call = ast.Call(
          func=ast.Attribute(value=ast.Name(id="metap"), attr='cvar2'),
          args=[cond, globals_call(), our_name],
          keywords=[]
        )
    return new_call

class NecessaryTransformer(ast.NodeTransformer):
  # __ret_ifnn and __ret_ifn
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
  
  # Verifier that we have actually changed every call
  def visit_Call(self, call):
    if not isinstance(call.func, ast.Name):
      return call
    
    funcs = ['__ret_ifn', '__ret_ifnn', '_cvar']
    if call.func.id in funcs:
      assert False
    
    return call

  # _cvar
  def visit_If(self, if_: ast.If):
    # This is tricky because we need to replace an expression with a series of
    # statements. For example, we would like to replace this:

    #   if _cvar(x == True, y, 1):
    #     print(y)
    # with:
    #   if (
    #       cond = x == True
    #       if x == True:
    #         y = 1
    #       return cond
    #   ):
    #     print(y)

    # Obviously, we can't do such trickery in Python. The obvious solution is to
    # offload the work to some function:

    #   def cvar(cond, var, ift_e):
    #     if cond:
    #       var = ift_e
    #     return cond
    #
    #   if cvar(x == True, y, 1):
    #     print(y)

    # The problem, however, is that cvar() doesn't have access to `y`. If `y` is
    # a global in the same module, then it's fine because it can modify it. But,
    # `y` may be a function local, or it may be in another module (which is most
    # certainly the case given that cvar() is metap's code but the calling code
    # is not).
    
    # --- Current solution ---
    #
    # My solution is a bit unconventional but it seems robust and relatively
    # easy to code. Inside the function, instead of assigning to the variable we
    # want directly, which we can't do, we introduce another global variable.
    # For that, we need to pass globals() in the call-site. Then, inside the
    # `if`, we check if our variable is defined and if so, we copy its value to
    # the target variable. So, we end up with sth like:
    #  if metap.cvar(x == True, globals(), '__metap_y', 1):
    #    if '__metap_y' in globals():
    #      y = globals()['__metap_y']
    #    print(y)
    
    # In general, inside the top-level `if`, we introduce as many `if`s as the
    # variables used in cvar()'s inside the condition. This seems to work for
    # any `if` depth and with `else` (which also means it works with `elif`
    # since that is canonicalized as `if-else`).

    # Note that in the case of cvar2(), we assign to the variable whether we get
    # into the `if` or not. We just add the assignment of both the `if` and the `else`.
    
    # --- Alternative Solution ---
    # Note that obvious solution is akin to how a standard compiler would
    # translate `if`s, which is to "unroll" the conditions, so that this:
    #   if _cvar(x == True, z, 1) and _cvar(y == True, w, 10):
    # becomes:
      # cond1 = False
      # if x == True:
      #   z = 1
      #   cond1 = True
      #   if y == True:
      #     w = 10
      #     cond2 = True
      # if cond1 and cond2:
      #   print(hlvl)
    
    # But this is very complex, because we essentially have to implement
    # short-circuiting, which means we need different handling for `and` and
    # `or`. And in general, it needs much more gymnastics.

    new_body = []
    new_orelse = []
    # WARNING: We call visit() and _not_ generic_visit(), because the latter
    # will visit the children but not the node itself. So, in an `if-elif`, in
    # which case the `if`'s orelse has an if inside, the innermost `if` will not
    # be visited.
    for b in if_.body:
      new_body.append(self.visit(b))
    for s in if_.orelse:
      new_orelse.append(self.visit(s))

    cvar_tr = CVarTransformer()
    if_test = cvar_tr.visit(if_.test)
    if_vars = cvar_tr.if_vars
    uncond_vars = cvar_tr.uncond_vars
    
    var_ifs = []
    if_var_set = list(set(if_vars))
    for var in if_var_set:
      our_var = ast.Constant(value='__metap_'+var)
      glob_look = ast.Subscript(value=globals_call(),
                                slice=our_var)
      in_glob = ast.Compare(left=our_var, ops=[ast.In()],
                            comparators=[globals_call()])
      asgn = ast.Assign(
        targets=[ast.Name(id=var)],
        value = glob_look
      )
      var_if = ast.If(
        test=in_glob,
        body=[asgn],
        orelse=[]
      )
      var_ifs.append(var_if)
    ### END FOR ###
    
    uncond_var_asgns = []
    uncond_var_set = list(set(uncond_vars))
    for var in uncond_var_set:
      our_var = ast.Constant(value='__metap_'+var)
      glob_look = ast.Subscript(value=globals_call(),
                                slice=our_var)
      asgn = ast.Assign(
        targets=[ast.Name(id=var)],
        value = glob_look
      )
      uncond_var_asgns.append(asgn)
    ### END FOR ###

    if_.test = if_test
    if_.body = uncond_var_asgns + var_ifs + new_body
    if_.orelse = uncond_var_asgns + new_orelse

    return if_

class LogFuncDef(ast.NodeTransformer):
  def __init__(self, range=[]):
    ast.NodeTransformer.__init__(self)
    self.range = range

  def visit_FunctionDef(self, fdef:ast.FunctionDef):
    assert hasattr(fdef, 'lineno')
    lineno = fdef.lineno

    if not in_range(lineno, self.range):
      return fdef
    
    fname = fdef.name
    
    log_info = {"name": "FuncDef"}
    log_info["ln"] = lineno
    log_info["fname"] = fname

    out_log = fmt_log_info(log_info)
    
    print_call = ast.Call(
      func=ast.Name(id="print"),
      args=[ast.Constant(value=out_log)],
      keywords=[]
    )
    e = ast.Expr(value=print_call)
    fdef.body = [e] + fdef.body
    return fdef


class MetaP:
  def __init__(self, filename) -> None:
    self.filename = filename
    with open(filename, 'r') as fp:
      self.ast = ast.parse(fp.read())

  def log_returns(self, include_fname=False, range=[]):
    walker = LogReturnWalker(include_fname=include_fname,
                             fname=os.path.basename(self.filename),
                             range=range)
    walker.walk(self.ast)

  def log_breaks(self):
    transformer = BreakContTransformer("Break")
    transformer.visit(self.ast)
  
  def log_continues(self):
    transformer = BreakContTransformer("Continue")
    transformer.visit(self.ast)
  
  def log_calls(self, range=[]):
    transformer = CallSiteTransformer(range=range)
    transformer.visit(self.ast)
  
  def log_func_defs(self, range=[]):
    transformer = LogFuncDef(range=range)
    transformer.visit(self.ast)
    
  # Handles anything that is required to be transformed for the code to run
  # (i.e., any code that uses metap features)
  def compile(self):
    transformer = NecessaryTransformer()
    transformer.visit(self.ast)

  def dump(self, filename=None):
    if not filename:
      filename = self.filename.split('.')[0] + ".metap.py"

    # Add an import to metap on the top
    self.ast.body.insert(0, ast.Import(names=[ast.Name(id="metap")]))

    with open(filename, 'w') as fp:
      src = astor.to_source(self.ast, indent_with=' ' * 2)
      fp.write(src)
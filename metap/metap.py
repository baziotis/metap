import ast, astor
import os
from contextlib import contextmanager
import copy
import re

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

__metap_indent_counter = 0

@contextmanager
def indent_ctx():
  global __metap_indent_counter
  __metap_indent_counter += 1   # Increment on entering
  try:
    yield
  finally:
    __metap_indent_counter -= 1  # Decrement on exiting

def indent_print():
  for _ in range(__metap_indent_counter):
    print("  ", end="")
    

def time_exec(code, globals_):
  # code_obj = compile(code, 'metap', 'exec'), 
  exec(code, globals_)
  assert '__metap_res' in globals_
  assert '__metap_total_ns' in globals_
  return globals_['__metap_res'], globals_['__metap_total_ns']

def simple_exec(code, globals_):
  exec(code, globals_)
  assert '__metap_res' in globals_
  return globals_['__metap_res']


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

def get_print(arg):
  print_call = ast.Call(
    func=ast.Name(id="print"),
    args=[arg],
    keywords=[]
  )
  print_e = ast.Expr(value=print_call)
  
  return print_e

def get_print_str(arg:str):
  assert isinstance(arg, str)

  return get_print(ast.Constant(value=arg))

def break_cont(cur_node, kind):
  assert hasattr(cur_node, 'lineno')
  lineno = cur_node.lineno

  log_info = {"name": kind}
  log_info["ln"] = lineno

  out_log = fmt_log_info(log_info)
  
  print_before = get_print_str(out_log)
  
  return [print_before, cur_node]

class LogBreakCont(ast.NodeTransformer):
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

class LogCallSite(ast.NodeTransformer):
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
  def visit_Call(self, call: ast.Call):
    if not isinstance(call.func, ast.Name):
      return call
    
    funcs = ['__ret_ifn', '__ret_ifnn', '_cvar']
    if call.func.id in funcs:
      assert False
      
    # Handle timing
    if call.func.id == '_time_e':
      args = call.args
      assert len(args) == 1
      e = ast.Expr(value=args[0])
      code_to_exec = f"""
import time
__metap_start_ns = time.perf_counter_ns()
__metap_res = {astor.to_source(e).strip()}
__metap_end_ns = time.perf_counter_ns()
__metap_total_ns = __metap_end_ns - __metap_start_ns
"""
      new_call = ast.Call(
        func=ast.Attribute(value=ast.Name(id="metap"), attr='time_exec'),
        args=[ast.Constant(value=code_to_exec), globals_call()],
        keywords=[]
      )
      return new_call
    # END IF #
    
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
    
    # --- Alternative Solution 2 ---

    # Pass a code block into a function and use `exec()`. Similar to how we
    # handle `_time_e()`.
    

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

def indent_triple(body, print_log_e):
  print_indent = ast.Call(
    func=ast.Attribute(value=ast.Name(id="metap"), attr='indent_print'),
    args=[],
    keywords=[]
  )
  print_indent_e = ast.Expr(value=print_indent)

  indent_ctx = ast.Call(
    func=ast.Attribute(value=ast.Name(id="metap"), attr='indent_ctx'),
    args=[],
    keywords=[]
  )
  with_ = ast.With(
    items=[ast.withitem(context_expr=indent_ctx, optional_vars=None)],
    body=body
  )
  
  return [print_indent_e, print_log_e, with_]

class LogFuncDef(ast.NodeTransformer):
  def __init__(self, range=[], indent=False):
    ast.NodeTransformer.__init__(self)
    self.range = range
    self.indent = indent

  def visit_FunctionDef(self, fdef:ast.FunctionDef):
    assert hasattr(fdef, 'lineno')
    lineno = fdef.lineno

    if not in_range(lineno, self.range):
      return fdef
    
    fname = fdef.name
    
    log_info = {"name": "FuncDef"}
    log_info["ln"] = lineno
    log_info["func"] = fname

    out_log = fmt_log_info(log_info)

    print_log_e = get_print_str(out_log)

    if not self.indent:
      fdef.body = [print_log_e] + fdef.body
      return fdef
    else:
      new_body = indent_triple(body=fdef.body, print_log_e=print_log_e)
      fdef.body = new_body
      return fdef

class LogIfs(ast.NodeTransformer):
  def __init__(self, range=[], indent=False):
    ast.NodeTransformer.__init__(self)
    self.range = range
    self.indent = indent

  def visit_If(self, if_:ast.If):
    assert hasattr(if_, 'lineno')
    then_lineno = if_.lineno

    if not in_range(then_lineno, self.range):
      return if_
    
    log_info_then = {"name": "If"}
    log_info_then["ln"] = then_lineno
    
    out_log_then = fmt_log_info(log_info_then)
    
    log_info_else = {"name": "Else"}
    log_info_else["ln"] = then_lineno
    
    out_log_else = fmt_log_info(log_info_else)

    new_then = []
    new_else = []
    for b in if_.body:
      new_then.append(self.visit(b))
    ### END FOR ###
    for s in if_.orelse:
      new_else.append(self.visit(s))
    ### END FOR ###
    
    print_then = get_print_str(out_log_then)
    print_else = get_print_str(out_log_else)

    if not self.indent:
      new_then = [print_then] + new_then
      new_else = [print_else] + new_else
    else:
      
      new_then = indent_triple(body=new_then, print_log_e=print_then)
      new_else = indent_triple(body=new_else, print_log_e=print_else)
    # END IF #

    if_.body = new_then
    if len(if_.orelse) != 0 and not isinstance(if_.orelse[0], ast.If):
      if_.orelse = new_else
    
    return if_

def isinst_call(obj, ty):
  return ast.Call(
    func=ast.Name(id="isinstance"),
    args=[obj, ty],
    keywords=[]
  )

def isnone_cond(obj):
  return ast.Compare(obj, ops=[ast.Is()],
                     comparators=[ast.Constant(value=None)])

# Generate expression that goes into an assert that `obj` is of type `ann`
def exp_for_ann(obj, ann):
  if isinstance(ann, ast.Name):
    return isinst_call(obj, ann)
  
  if isinstance(ann, ast.Constant):
    return ast.Compare(left=obj, ops=[ast.Eq()], comparators=[ann])
  
  assert isinstance(ann, ast.Subscript)
  sub = ann
  slice = sub.slice
  cons = sub.value
  assert isinstance(cons, ast.Name)
  acceptable_constructors = ['Optional', 'Union', 'Tuple', 'List']
  assert cons.id in acceptable_constructors
  if cons.id == 'Optional':
    is_ty = exp_for_ann(obj, slice)
    is_none = isnone_cond(obj)
    or_ = ast.BinOp(left=is_ty, op=ast.Or(), right=is_none)
    return or_ 
  elif cons.id == 'Union':
    assert isinstance(slice, ast.Tuple)
    elts = slice.elts
    assert len(elts) == 2
    l = elts[0]
    r = elts[1]
    is_l = exp_for_ann(obj, l)
    is_r = exp_for_ann(obj, r)
    or_ = ast.BinOp(left=is_l, op=ast.Or(), right=is_r)
    return or_
  elif cons.id == 'Tuple':
    assert isinstance(slice, ast.Tuple)
    elts = slice.elts
    assert len(elts) > 1
    
    cond_len = ast.Compare(
        left=ast.Call(
          func=ast.Name(id='len'),
          args=[obj],
          keywords=[]
        ),
        ops=[ast.Eq()],
        comparators=[ast.Constant(value=len(elts))]
      )
    curr = cond_len
    
    for i, elt in enumerate(elts):
      sub = ast.Subscript(
        value=obj,
        slice=ast.Constant(value=i)
      )
      curr = ast.BinOp(left=curr, op=ast.And(), right=exp_for_ann(sub, elt))
    ### END FOR ###
    return curr
  elif cons.id == 'List':
    # We only support single type
    assert not isinstance(slice, ast.Tuple)
    
    iter_el = ast.Name(id='__metap_x')
    el_ty = exp_for_ann(iter_el, slice)
    list_comp = ast.ListComp(
      elt=el_ty,
      generators=[ast.comprehension(target=iter_el, iter=obj, ifs=[])]
    )
    all_call = ast.Call(
      func=ast.Name(id='all'),
      args=[list_comp],
      keywords=[]
    )
    return all_call
  else:
    assert False  
  

def ann_if(obj, ann):
  type_call = ast.Call(
    func=ast.Name(id='type'),
    args=[obj],
    keywords=[]
  )
  print_ty = get_print(type_call)
  print_obj = get_print(obj)
  assert_f = ast.Assert(
    test=ast.Constant(value=False)
  )
  if_ = ast.If(
    test=ast.UnaryOp(op=ast.Not(), operand=exp_for_ann(obj, ann)),
    body=[print_obj, print_ty, assert_f],
    orelse=[]
  )
  return if_

class AssertTransformer(ast.NodeTransformer):
  def visit_AnnAssign(self, node: ast.AnnAssign):
    target = node.target
    if not isinstance(target, ast.Name):
      return node

    ann = node.annotation
    if_ = ann_if(target, ann)
    return [node, if_]

  def visit_FunctionDef(self, fdef:ast.FunctionDef):
    if (len(fdef.decorator_list) != 0 or
        fdef.args.vararg is not None or
        len(fdef.args.posonlyargs) != 0 or
        fdef.args.kwarg is not None or
        len(fdef.args.defaults) != 0):
      return fdef

    ifs = []
    
    args = fdef.args.args
    for arg in args:
      assert isinstance(arg, ast.arg)
      ann = arg.annotation
      if ann is not None:
        id_ = ast.Name(id=arg.arg)
        if_ = ann_if(id_, ann)
        ifs.append(if_)
    ### END FOR ###
    
    new_body = ifs + fdef.body

    ret_ann = fdef.returns
    if ret_ann is not None:
      helper_func = copy.deepcopy(fdef)
      helper_name = '__metap_'+fdef.name
      helper_func.name = helper_name
      helper_func.body = new_body
      call_helper = ast.Call(
        func=ast.Name(id=helper_name),
        args=[
          ast.Name(id=arg.arg, ctx=ast.Load())
          for arg in fdef.args.args
        ],
        keywords=[]
      )
      ret_var = ast.Name(id='__metap_retv')
      asgn = ast.Assign(
        targets=[ret_var],
        value=call_helper
      )
      ret = ast.Return(
        value=ret_var
      )
      if_ = ann_if(ret_var, ret_ann)
      fdef.body = [asgn, if_, ret]
      return [helper_func, fdef]
    else:
      fdef.body = new_body
      return fdef



class CallStartEnd(ast.NodeTransformer):
  def __init__(self, patt=None):
    ast.NodeTransformer.__init__(self)
    self.patt = patt

  def visit_Call(self, call: ast.Call):
    # TODO: Add filename
    assert hasattr(call, 'lineno')
    lineno = call.lineno
    
    self.generic_visit(call)

    e = ast.Expr(value=call)
    e_src = astor.to_source(e).strip()
    func_name = astor.to_source(call.func).strip()
    if self.patt is not None and not re.match(self.patt, e_src):
      return call

    # TODO: We may have a problem here if `e_src` has double strings. Can it?
    # It comes from astor.to_source() which uses single quotes.
    log = '{}:{}'.format(lineno, e_src)
    code_to_exec = f"""
print(f"metap: Started executing: {log}")
__metap_res = {e_src}
print(f"metap: Finished executing: {log}")
"""
    new_call = ast.Call(
      func=ast.Attribute(value=ast.Name(id="metap"), attr='simple_exec'),
      args=[ast.Constant(value=code_to_exec), globals_call()],
      keywords=[]
    )
    return new_call

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
    transformer = LogBreakCont("Break")
    transformer.visit(self.ast)
  
  def log_continues(self):
    transformer = LogBreakCont("Continue")
    transformer.visit(self.ast)
  
  def log_calls(self, range=[]):
    transformer = LogCallSite(range=range)
    transformer.visit(self.ast)
  
  def log_func_defs(self, range=[], indent=False):
    transformer = LogFuncDef(range=range, indent=indent)
    transformer.visit(self.ast)
  
  def log_ifs(self, range=[], indent=False):
    transformer = LogIfs(range=range, indent=indent)
    transformer.visit(self.ast)
    
  def add_asserts(self):
    t = AssertTransformer()
    t.visit(self.ast)
  
  def log_calls_start_end(self, patt=None):
    t = CallStartEnd(patt=patt)
    t.visit(self.ast)
    

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
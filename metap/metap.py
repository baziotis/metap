import ast, astor
import os
from contextlib import contextmanager
import copy
import re
from typing import Dict, List, Optional

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

def log_start_end(started_print, val, finished_print):
  assert started_print is None
  assert finished_print is None
  return val


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

def break_cont(cur_node, kind, range):
  assert hasattr(cur_node, 'lineno')
  lineno = cur_node.lineno

  if not in_range(lineno, range):
    return cur_node

  log_info = {"name": kind}
  log_info["ln"] = lineno

  out_log = fmt_log_info(log_info)
  
  print_before = get_print_str(out_log)
  
  return [print_before, cur_node]

class LogBreakCont(ast.NodeTransformer):
  def __init__(self, kind, range):
    ast.NodeTransformer.__init__(self)
    self.kind = kind
    self.range = range

  def visit_Continue(self, node):
    if self.kind == "Continue":
      return break_cont(node, self.kind, self.range)
    else:
      return node

  def visit_Break(self, node):
    if self.kind == "Break":
      return break_cont(node, self.kind, self.range)
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

def locals_call():
  call = ast.Call(
    func=ast.Name(id="locals"),
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
  # _ret_ifnn and _ret_ifn
  def visit_Expr(self, e):
    if not isinstance(e.value, ast.Call):
      self.generic_visit(e)
      return e
    call = e.value
    func = call.func
    if not isinstance(func, ast.Name):
      self.generic_visit(e)
      return e
    
    ret_funcs = ['_ret_ifnn', '_ret_ifn']
    if func.id not in ret_funcs:
      self.generic_visit(e)
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
    
    if func.id == '_ret_ifnn':
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
      self.generic_visit(call)
      return call
    
    funcs = ['_ret_ifn', '_ret_ifnn', '_cvar']
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
    elif call.func.id == '_mprint':
      args = call.args
      assert len(args) == 1
      e = ast.Expr(value=args[0])
      arg_s = astor.to_source(e).strip()
      print_arg0 = ast.Constant(value=f"{arg_s}:")
      print_arg1 = args[0]
      new_call = ast.Call(
        func=ast.Name(id="print"),
        args=[print_arg0, print_arg1],
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

def handle_non_sub(obj, ann):
  if isinstance(ann, ast.Name) and (ann.id in ["List", "Dict", "Tuple", "Type"]):
    ty = ast.Name(id=ann.id.lower())
    return isinst_call(obj, ty)
  else:
    return isinst_call(obj, ann)
  
def ann_id(curr: List[int]):
  curr[0] = curr[0] + 1
  return curr[0]

# Generate expression that goes into an assert that `obj` is of type `ann`
def exp_for_ann(obj, ann, id_curr):
  if isinstance(ann, ast.Constant):
    return ast.Compare(left=obj, ops=[ast.Eq()], comparators=[ann])
  
  if not isinstance(ann, ast.Subscript):
    return handle_non_sub(obj, ann)
  
  assert isinstance(ann, ast.Subscript)
  sub = ann
  slice = sub.slice
  cons = sub.value
  assert isinstance(cons, ast.Name)
  acceptable_constructors = ['Optional', 'Union', 'Tuple', 'List', 'Dict', 'Type']
  assert cons.id in acceptable_constructors
  if cons.id == 'Optional':
    is_ty = exp_for_ann(obj, slice, id_curr)
    is_none = isnone_cond(obj)
    or_ = ast.BinOp(left=is_ty, op=ast.Or(), right=is_none)
    return or_ 
  elif cons.id == 'Union':
    assert isinstance(slice, ast.Tuple)
    elts = slice.elts
    assert len(elts) >= 2
    l = elts[0]
    r = elts[1]
    is_l = exp_for_ann(obj, l, id_curr)
    is_r = exp_for_ann(obj, r, id_curr)
    or_ = ast.BinOp(left=is_l, op=ast.Or(), right=is_r)
    curr = or_
    
    for i, elt in enumerate(elts[2:]):
      check = exp_for_ann(obj, elt, id_curr)
      curr = ast.BinOp(left=curr, op=ast.Or(), right=check)
    return curr
  elif cons.id == 'Tuple':
    assert isinstance(slice, ast.Tuple)
    elts = slice.elts
    assert len(elts) > 1
    
    isinst = isinst_call(obj, ast.Name(id='tuple'))
    
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
      curr = ast.BinOp(left=curr, op=ast.And(), right=exp_for_ann(sub, elt, id_curr))
    ### END FOR ###
    and_isinst = ast.BinOp(left=isinst, op=ast.And(), right=curr)
    return and_isinst
  elif cons.id == 'List':
    # We only support single type
    assert not isinstance(slice, ast.Tuple)
    
    isinst = isinst_call(obj, ast.Name(id='list'))
    
    iter_el = ast.Name(id='__metap_x' + str(ann_id(id_curr)))
    el_ty = exp_for_ann(iter_el, slice, id_curr)
    list_comp = ast.ListComp(
      elt=el_ty,
      generators=[ast.comprehension(target=iter_el, iter=obj, ifs=[])]
    )
    all_call = ast.Call(
      func=ast.Name(id='all'),
      args=[list_comp],
      keywords=[]
    )
    and_ = ast.BinOp(left=isinst, op=ast.And(), right=all_call)
    return and_
  elif cons.id == 'Dict':
    assert isinstance(slice, ast.Tuple)
    
    isinst = isinst_call(obj, ast.Name(id='dict'))
    
    elts = slice.elts
    assert len(elts) == 2
    key_ann = elts[0]
    val_ann = elts[1]
    
    key_iter = ast.Name(id='_metap_k' + str(ann_id(id_curr)))
    val_iter = ast.Name(id='_metap_v' + str(ann_id(id_curr)))
    iter = ast.Tuple(elts=[key_iter, val_iter])
    key_ty = exp_for_ann(key_iter, key_ann, id_curr)
    val_ty = exp_for_ann(val_iter, val_ann, id_curr)
    and_ = ast.BinOp(left=key_ty, op=ast.And(), right=val_ty)
    items = ast.Call(
      func=ast.Attribute(value=obj, attr='items'),
      args=[],
      keywords=[]
    )
    list_comp = ast.ListComp(
      elt=and_,
      generators=[ast.comprehension(target=iter, iter=items, ifs=[])]
    )
    all_call = ast.Call(
      func=ast.Name(id='all'),
      args=[list_comp],
      keywords=[]
    )
    and_ = ast.BinOp(left=isinst, op=ast.And(), right=all_call)
    return and_
  elif cons.id == 'Type':
    assert isinstance(slice, ast.Name)
    is_ = ast.BinOp(left=obj, op=ast.Is(), right=slice)
    return is_
  else:
    assert False  

def get_type_call(obj):
  return ast.Call(
    func=ast.Name(id='type'),
    args=[obj],
    keywords=[]
  )

def ann_if(obj, ann, id_curr):
  type_call = get_type_call(obj)
  print_ty = get_print(type_call)
  print_obj = get_print(obj)
  assert_f = ast.Assert(
    test=ast.Constant(value=False)
  )
  if_ = ast.If(
    test=ast.UnaryOp(op=ast.Not(), operand=exp_for_ann(obj, ann, id_curr)),
    body=[print_obj, print_ty, assert_f],
    orelse=[]
  )
  return if_

class AssertTransformer(ast.NodeTransformer):
  def __init__(self, skip_funcs: Optional[List[str]]):
    ast.NodeTransformer.__init__(self)
    self.skip_funcs = skip_funcs
    self.id_curr = [0]

  def visit_AnnAssign(self, node: ast.AnnAssign):
    target = node.target
    if not isinstance(target, ast.Name):
      return node

    ann = node.annotation
    if_ = ann_if(target, ann, self.id_curr)
    return [node, if_]

  def visit_FunctionDef(self, fdef:ast.FunctionDef):
    if self.skip_funcs is not None and fdef.name in self.skip_funcs:
      return fdef

    if (len(fdef.decorator_list) != 0 or
        fdef.args.vararg is not None or
        len(fdef.args.posonlyargs) != 0 or
        fdef.args.kwarg is not None or
        len(fdef.args.defaults) != 0):
      return fdef

    ifs = []
    
    args = fdef.args.args
    
    in_class = False
    if len(args) > 0 and args[0].arg == 'self':
      args = args[1:]
      in_class = True
    
    for arg in args:
      assert isinstance(arg, ast.arg)
      ann = arg.annotation
      if ann is not None:
        id_ = ast.Name(id=arg.arg)
        if_ = ann_if(id_, ann, self.id_curr)
        ifs.append(if_)
    ### END FOR ###
    
    new_body = ifs + fdef.body

    ret_ann = fdef.returns
    if ret_ann is not None:
      helper_func = copy.deepcopy(fdef)
      helper_name = '__metap_'+fdef.name
      helper_func.name = helper_name
      helper_func.body = new_body
      how_to_call = ast.Name(id=helper_name)
      if in_class:
        how_to_call = ast.Attribute(ast.Name(id='self'), attr=helper_name)
      call_helper = ast.Call(
        func=how_to_call,
        args=[
          ast.Name(id=arg.arg, ctx=ast.Load())
          for arg in args
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
      if_ = ann_if(ret_var, ret_ann, self.id_curr)
      fdef.body = [asgn, if_, ret]
      return [helper_func, fdef]
    else:
      fdef.body = new_body
      return fdef

class TypedefGather(ast.NodeTransformer):
  def __init__(self):
    ast.NodeTransformer.__init__(self)
    self.typedefs = dict()
    
  def visit_Assign(self, asgn: ast.Assign):
    targets = asgn.targets
    assert len(targets) == 1
    name_node = targets[0]
    assert isinstance(name_node, ast.Name)
    typename = name_node.id
    new_val = self.visit(asgn.value)
    self.typedefs[typename] = new_val

    return ast.Assign(targets=[name_node], value=new_val)

  def visit_Name(self, name_node: ast.Name):
    known = {'str', 'float', 'int', 'Dict', 'List', 'Tuple', 'Optional', 'Union'}
    name = name_node.id
    # This logic requires that we don't have forward references, which we
    # assume.
    if name not in known:
      if name in self.typedefs:
        assert self.typedefs[name] is not None
        return self.typedefs[name]
      # END IF #
    # END IF #
    return name_node


class TypedefTransform(ast.NodeTransformer):
  def __init__(self, typedefs: Dict[str, ast.AST]):
    ast.NodeTransformer.__init__(self)
    self.typedefs = typedefs

  def visit_Name(self, name_node: ast.Name):
    name = name_node.id
    if name in self.typedefs:
      return self.typedefs[name]
     # END IF #
    # END IF #
    return name_node


class CallStartEnd(ast.NodeTransformer):
  def __init__(self, patt, range):
    ast.NodeTransformer.__init__(self)
    self.patt = patt
    self.range = range

  def visit_Call(self, call: ast.Call):
    # TODO: Add filename
    assert hasattr(call, 'lineno')
    lineno = call.lineno

    if not in_range(lineno, self.range):
      return call

    # This is more difficult than I thought. I tried calling a different
    # function that used exec() with globals() and locals() but that didn't
    # work.
    
    self.generic_visit(call)

    e = ast.Expr(value=call)
    e_src = astor.to_source(e).strip()
    if self.patt is not None and not re.match(self.patt, e_src):
      return call

    log = f'{lineno}:{astor.to_source(call.func).strip()}'

    started_log = f"metap: Started: {log}"
    finished_log = f"metap: Finished: {log}"
    started_print = get_print_str(started_log)
    finished_print = get_print_str(finished_log)

    new_call = ast.Call(
      func=ast.Attribute(value=ast.Name(id="metap"), attr='log_start_end'),
      args=[started_print, call, finished_print],
      keywords=[]
    )
    # print(astor.dump_tree(new_call, indentation="  "))
    # print('******')
    # # print(astor.to_source(new_call, indent_with="  "))
    # print('--------------------------------------------')
    return new_call

# Expand:
# - assert isinstance(a, b) to
#   if not isinstance(a, b):
#     print(a)
#     print(type(a))
#     assert False
# - assert a == b to
#   if a != b:
#     print(a)
#     print(b)
#     assert False
class ExpandAsserts(ast.NodeTransformer):
  def visit_Assert(self, ass: ast.Assert):
    if isinstance(ass.test, ast.Compare):
      cmp = ass.test
      ops = cmp.ops
      if len(ops) != 1:
        return ass
      op = ops[0]
      new_op = None
      if isinstance(op, ast.Eq):
        new_op = ast.NotEq()
      elif isinstance(op, ast.NotEq):
        new_op = ast.Eq()
      else:
        return ass
      # END IF #
      if len(cmp.comparators) != 1:
        return ass
      right = cmp.comparators[0]
      left = cmp.left
      l_name = ast.Name(id="_metap_l")
      r_name = ast.Name(id="_metap_r")
      asgn_l = ast.Assign(targets=[l_name], value=left)
      asgn_r = ast.Assign(targets=[r_name], value=right)
      print_l = get_print(l_name)
      print_r = get_print(r_name)
      assert new_op is not None
      new_test = ast.Compare(left=l_name, ops=[new_op],
                             comparators=[r_name])
      ass_f = ast.Assert(ast.Constant(value=False), msg=ass.msg)
      if_ = ast.If(test=new_test, body=[print_l, print_r, ass_f], orelse=[])
      return [asgn_l, asgn_r, if_]
    elif isinstance(ass.test, ast.Call):
      call = ass.test
      func = call.func
      if not isinstance(func, ast.Name):
        return ass
      if func.id != "isinstance":
        return ass
      args = call.args
      if len(args) != 2:
        return ass
      obj = args[0]
      ty = args[1]
      var_name = ast.Name(id="_metap_obj")
      asgn = ast.Assign(targets=[var_name], value=obj)
      print_obj = get_print(var_name)
      print_obj_ty = get_print(get_type_call(var_name))
      ass_f = ast.Assert(ast.Constant(value=False), msg=ass.msg)
      new_isinstance = ast.Call(
        func=ast.Name(id="isinstance"),
        args=[var_name, ty],
        keywords=[]
      )
      new_test = ast.UnaryOp(op=ast.Not(), operand=new_isinstance)
      if_ = ast.If(test=new_test,
                   body=[print_obj, print_obj_ty, ass_f],
                   orelse=[])
      return [asgn, if_]
    # END IF #
    
    return ass

class MetaP:
  def __init__(self, filename) -> None:
    self.filename = filename
    with open(filename, 'r') as fp:
      self.ast = ast.parse(fp.read())
    
    self.log_se_called = False

  def log_returns(self, include_fname=False, range=[]):
    walker = LogReturnWalker(include_fname=include_fname,
                             fname=os.path.basename(self.filename),
                             range=range)
    walker.walk(self.ast)

  def log_breaks(self, range=[]):
    transformer = LogBreakCont("Break", range)
    transformer.visit(self.ast)
  
  def log_continues(self, range=[]):
    transformer = LogBreakCont("Continue", range)
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
    
  def dyn_typecheck(self, typedefs_path=None, skip_funcs: Optional[List[str]]=None):
    if typedefs_path is not None:
      with open(typedefs_path, 'r') as fp:
        tdef_ast = ast.parse(fp.read())
      # END WITH
      t = TypedefGather()
      t.visit(tdef_ast)

      t2 = TypedefTransform(t.typedefs)
      t2.visit(self.ast)
    # END IF #
    t = AssertTransformer(skip_funcs)
    t.visit(self.ast)
  
  def log_calls_start_end(self, patt=None, range=[]):
    self.log_se_called = True
    t = CallStartEnd(patt=patt, range=range)
    t.visit(self.ast)

  def expand_asserts(self):
    t = ExpandAsserts()
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

    maxline=79
    if self.log_se_called:
      # astor fails with all the craziness by log_calls_start_end(). To fix it,
      # we allow too long lines. Note that this requires baziotis/astor version.
      # The upstream astor doesn't allow to pass `maxline` to `to_source()`
      maxline=10_000

    with open(filename, 'w') as fp:
      src = astor.to_source(self.ast, indent_with=' ' * 2, maxline=maxline)
      fp.write(src)
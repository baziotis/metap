import unittest
import metap
import os

def ret_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_returns()
  mp.dump()

def log_call(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_calls()
  mp.dump()

def cont_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_continues()
  mp.dump()

def break_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_breaks()
  mp.dump()

def just_compile(fname):
  mp = metap.MetaP(filename=fname)
  mp.compile()
  mp.dump()
  
def compose_retif_and_logret(fname):
  mp = metap.MetaP(filename=fname)
  mp.compile()
  mp.log_returns()
  mp.dump()
  
def dyn_typecheck(fname):
  mp = metap.MetaP(filename=fname)
  mp.dyn_typecheck()
  mp.dump()

def dyn_typecheck_skip(fname):
  mp = metap.MetaP(filename=fname)
  mp.dyn_typecheck(skip_funcs=["foo"])
  mp.dump()

def log_calls_start_end1(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_calls_start_end(patt=r'find_primes')
  mp.dump()

def log_calls_start_end2(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_calls_start_end(patt=r'.*json\.dump')
  mp.dump()

def log_calls_start_end3(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_calls_start_end()
  mp.dump()

def boiler(src, mid_func):
  fname = 'test.py'
  with open(fname, 'w') as fp:
    fp.write(src)

  mid_func(fname)

  out_fname = 'test.metap.py'
  with open(out_fname, 'r') as fp:
    out = fp.read()
  os.remove(fname)
  os.remove(out_fname)

  return out

def typedef_boiler(src, typedefs):
  mp_fname = 'test_mp.py'
  with open(mp_fname, 'w') as fp:
    fp.write(src)
  
  td_fname = 'typedefs.py'
  with open(td_fname, 'w') as fp:
    fp.write(typedefs)
  
  out_fname = 'test.py'
  mp = metap.MetaP(filename=mp_fname)
  mp.dyn_typecheck(typedefs_path=td_fname)
  mp.dump(filename=out_fname)

  with open(out_fname, 'r') as fp:
    out = fp.read()

  os.remove(mp_fname)
  os.remove(td_fname)
  os.remove(out_fname)
  
  return out

class LogReturn(unittest.TestCase):
  def test_val(self):
    src = \
"""
def add_one(num):
  return num + 1
"""

    expect = \
"""import metap


def add_one(num):
  return metap.log_ret(num + 1, 'metap::Return(ln=3)')
"""
    
    out = boiler(src, ret_func)
    self.assertEqual(out, expect)



  def test_noval(self):
    src = \
"""
def foo():
  return
"""

    expect = \
"""import metap


def foo():
  return metap.log_ret(None, 'metap::Return(ln=3)')
"""
    
    out = boiler(src, ret_func)
    self.assertEqual(out, expect)



  def test_range(self):
    src = \
"""
def foo():
  return

def bar():
  return 1

def baz():
  return 2
"""

    expect = \
"""import metap


def foo():
  return


def bar():
  return metap.log_ret(1, 'metap::Return(ln=6)')


def baz():
  return 2
"""

    def ret_range(fname):
      mp = metap.MetaP(filename=fname)
      mp.log_returns(range=[(5, 7)])
      mp.dump()

    out = boiler(src, ret_range)
    self.assertEqual(out, expect)




class LogCall(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def add_one(num):
  return num + 1
  
for x in xs:
  if x:
    ret = add_one(n)
"""

    expect = \
"""import metap


def add_one(num):
  return num + 1


for x in xs:
  if x:
    ret = metap.log_call(lambda : add_one(n),
        'metap::Call(ln=7,call=add_one(n))')
"""
    
    out = boiler(src, log_call)
    self.assertEqual(out, expect)



  def test_range(self):
    src = \
"""
for x in xs:
  if x:
    add_one(n)

  if y:
    add_two(n)

if z:
  add_three()
"""

    expect = \
"""import metap
for x in xs:
  if x:
    metap.log_call(lambda : add_one(n), 'metap::Call(ln=4,call=add_one(n))')
  if y:
    add_two(n)
if z:
  metap.log_call(lambda : add_three(), 'metap::Call(ln=10,call=add_three())')
"""

    def call_range(fname):
      mp = metap.MetaP(filename=fname)
      mp.log_calls(range=[(3, 5), 10])
      mp.dump()
    
    out = boiler(src, call_range)
    self.assertEqual(out, expect)





class BreakCont(unittest.TestCase):
  def test_cont(self):
    src = \
"""
for i in range(10):
  if i == 3:
    continue
"""

    expect = \
"""import metap
for i in range(10):
  if i == 3:
    print('metap::Continue(ln=4)')
    continue
"""
    
    out = boiler(src, cont_func)
    self.assertEqual(out, expect)

  def test_break(self):
    src = \
"""
for i in range(10):
  if i == 3:
    break
"""

    expect = \
"""import metap
for i in range(10):
  if i == 3:
    print('metap::Break(ln=4)')
    break
"""
    
    out = boiler(src, break_func)
    self.assertEqual(out, expect)



class RetIfnn(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def foo(ns):
  for n in ns:
    _ret_ifnn(helper(n))
  return None

def main(xs):
  for x in xs:
    _ret_ifnn(foo(x))
"""

    expect = \
"""import metap


def foo(ns):
  for n in ns:
    _metap_ret = helper(n)
    if _metap_ret is not None:
      return _metap_ret
  return None


def main(xs):
  for x in xs:
    _metap_ret = foo(x)
    if _metap_ret is not None:
      return _metap_ret
"""
    
    out = boiler(src, just_compile)
    self.assertEqual(out, expect)
    


class RetIfn(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def foo(ns):
  for n in ns:
    _ret_ifn(helper(n))
  return None

def main(xs):
  for x in xs:
    _ret_ifn(foo(x))
"""

    expect = \
"""import metap


def foo(ns):
  for n in ns:
    _metap_ret = helper(n)
    if _metap_ret is None:
      return None
  return None


def main(xs):
  for x in xs:
    _metap_ret = foo(x)
    if _metap_ret is None:
      return None
"""
    
    out = boiler(src, just_compile)
    self.assertEqual(out, expect)






class VPrint(unittest.TestCase):
  def test_simple(self):
    src = \
"""
_mprint(a)
"""

    expect = \
"""import metap
print('a:', a)
"""
    
    out = boiler(src, just_compile)
    self.assertEqual(out, expect)


  def test_call(self):
    src = \
"""
_mprint(foo())
"""

    expect = \
"""import metap
print('foo():', foo())
"""
    
    out = boiler(src, just_compile)
    self.assertEqual(out, expect)


class ComposeRetIfAndLogRet(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def foo(ns):
  for n in ns:
    _ret_ifnn(helper(n))
"""

    expect = \
"""import metap


def foo(ns):
  for n in ns:
    _metap_ret = helper(n)
    if _metap_ret is not None:
      return metap.log_ret(_metap_ret, 'metap::Return(ln=4)')
"""

    out = boiler(src, compose_retif_and_logret)
    self.assertEqual(out, expect)
    


class ComposeLogRetAndLogCall(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def foo():
  return bar()
"""

    expect = \
"""import metap


def foo():
  return metap.log_ret(metap.log_call(lambda : bar(),
      'metap::Call(ln=3,call=bar())'), 'metap::Return(ln=3)')
"""

    def compose_logret_and_logcall(fname):
      mp = metap.MetaP(filename=fname)
      mp.log_calls()
      mp.log_returns()
      mp.dump()      

    out = boiler(src, compose_logret_and_logcall)
    self.assertEqual(out, expect)



class LogFuncDefs(unittest.TestCase):
  def test_visitor(self):
    src = \
"""
def foo():
  return 2

class RandomVisitor(ast.NodeVisitor):
  def visit_Assign(self, asgn:ast.Assign):
    for t in asgn.targets:
      self.visit(t)
    ### END FOR ###
    self.visit(asgn.value)
  
  
  def visit_BinOp(self, binop:ast.BinOp):
    self.visit(binop.left)
"""

    expect = \
"""import metap


def foo():
  print('metap::FuncDef(ln=2,func=foo)')
  return 2


class RandomVisitor(ast.NodeVisitor):

  def visit_Assign(self, asgn: ast.Assign):
    print('metap::FuncDef(ln=6,func=visit_Assign)')
    for t in asgn.targets:
      self.visit(t)
    self.visit(asgn.value)

  def visit_BinOp(self, binop: ast.BinOp):
    print('metap::FuncDef(ln=13,func=visit_BinOp)')
    self.visit(binop.left)
"""

    def log_func_def(fname):
      mp = metap.MetaP(filename=fname)
      mp.log_func_defs()
      mp.compile()
      mp.dump()      

    out = boiler(src, log_func_def)
    self.maxDiff = None
    self.assertEqual(out, expect)


  def test_indent(self):
    src = \
"""
def bar():
  return 2

def foo(n):
  if n == 2:
    return None
  return bar()
"""

    expect = \
"""import metap


def bar():
  metap.indent_print()
  print('metap::FuncDef(ln=2,func=bar)')
  with metap.indent_ctx():
    return 2


def foo(n):
  metap.indent_print()
  print('metap::FuncDef(ln=5,func=foo)')
  with metap.indent_ctx():
    if n == 2:
      return None
    return bar()
"""

    def log_func_def2(fname):
      mp = metap.MetaP(filename=fname)
      mp.log_func_defs(indent=True)
      mp.compile()
      mp.dump()      

    out = boiler(src, log_func_def2)
    self.assertEqual(out, expect)


def log_if(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_ifs()
  mp.compile()
  mp.dump()

def log_if_indent(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_ifs(indent=True)
  mp.compile()
  mp.dump()


class LogIfs(unittest.TestCase):
  def test_simple(self):
    src = \
"""
if True:
  pass
else:
  pass
"""

    expect = \
"""import metap
if True:
  print('metap::If(ln=2)')
  pass
else:
  print('metap::Else(ln=2)')
  pass
"""

    out = boiler(src, log_if)
    self.assertEqual(out, expect)



  def test_simple2(self):
    src = \
"""
if False:
  pass
elif True:
  pass
else:
  pass
"""

    expect = \
"""import metap
if False:
  print('metap::If(ln=2)')
  pass
elif True:
  print('metap::If(ln=4)')
  pass
else:
  print('metap::Else(ln=4)')
  pass
"""

    out = boiler(src, log_if)
    self.assertEqual(out, expect)




  def test_indent(self):
    src = \
"""
if True:
  pass
else:
  pass
"""

    expect = \
"""import metap
if True:
  metap.indent_print()
  print('metap::If(ln=2)')
  with metap.indent_ctx():
    pass
else:
  metap.indent_print()
  print('metap::Else(ln=2)')
  with metap.indent_ctx():
    pass
"""

    out = boiler(src, log_if_indent)
    self.assertEqual(out, expect)



  def test_indent2(self):
    src = \
"""
if True:
  if False:
    pass
  else:
    pass
else:
  pass
"""

    expect = \
"""import metap
if True:
  metap.indent_print()
  print('metap::If(ln=2)')
  with metap.indent_ctx():
    if False:
      metap.indent_print()
      print('metap::If(ln=3)')
      with metap.indent_ctx():
        pass
    else:
      metap.indent_print()
      print('metap::Else(ln=3)')
      with metap.indent_ctx():
        pass
else:
  metap.indent_print()
  print('metap::Else(ln=2)')
  with metap.indent_ctx():
    pass
"""

    out = boiler(src, log_if_indent)
    self.assertEqual(out, expect)


  def test_noelse(self):
    src = \
"""
if True:
  if True:
    pass
else:
  pass
"""

    expect = \
"""import metap
if True:
  metap.indent_print()
  print('metap::If(ln=2)')
  with metap.indent_ctx():
    if True:
      metap.indent_print()
      print('metap::If(ln=3)')
      with metap.indent_ctx():
        pass
else:
  metap.indent_print()
  print('metap::Else(ln=2)')
  with metap.indent_ctx():
    pass
"""

    out = boiler(src, log_if_indent)
    self.assertEqual(out, expect)



class AddAsserts(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def foo(s: str):
  pass
"""

    expect = \
"""import metap


def foo(s: str):
  if not isinstance(s, str):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)





  def test_optional(self):
    src = \
"""
def foo(s: Optional[str]):
  pass
"""

    expect = \
"""import metap


def foo(s: Optional[str]):
  if not (isinstance(s, str) or s is None):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)





  def test_union(self):
    src = \
"""
def foo(s: Union[str, int]):
  pass
"""

    expect = \
"""import metap


def foo(s: Union[str, int]):
  if not (isinstance(s, str) or isinstance(s, int)):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)





  def test_tuple(self):
    src = \
"""
def foo(s: Tuple[str, int, RandomClass]):
  pass
"""

    expect = \
"""import metap


def foo(s: Tuple[str, int, RandomClass]):
  if not (isinstance(s, tuple) and (len(s) == 3 and isinstance(s[0], str) and
      isinstance(s[1], int) and isinstance(s[2], RandomClass))):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)
    



  def test_list(self):
    src = \
"""
def foo(s: List[str]):
  pass
"""

    expect = \
"""import metap


def foo(s: List[str]):
  if not (isinstance(s, list) and all([isinstance(__metap_x1, str) for
      __metap_x1 in s])):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)


  def test_complex(self):
    src = \
"""
def foo(s:List[Optional[Tuple[str, int]]]):
  pass
"""

    expect = \
"""import metap


def foo(s: List[Optional[Tuple[str, int]]]):
  if not (isinstance(s, list) and all([(isinstance(__metap_x1, tuple) and (
      len(__metap_x1) == 2 and isinstance(__metap_x1[0], str) and
      isinstance(__metap_x1[1], int)) or __metap_x1 is None) for __metap_x1 in
      s])):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_complex2(self):
    src = \
"""
def foo(s: Optional[Tuple[List[str], List[int]]]):
  pass
"""

    expect = \
"""import metap


def foo(s: Optional[Tuple[List[str], List[int]]]):
  if not (isinstance(s, tuple) and (len(s) == 2 and (isinstance(s[0], list) and
      all([isinstance(__metap_x1, str) for __metap_x1 in s[0]])) and (
      isinstance(s[1], list) and all([isinstance(__metap_x2, int) for
      __metap_x2 in s[1]]))) or s is None):
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.maxDiff = None
    self.assertEqual(out, expect)





  def test_mult_args(self):
    src = \
"""
def foo(s: str, a: int):
  pass
"""

    expect = \
"""import metap


def foo(s: str, a: int):
  if not isinstance(s, str):
    print(s)
    print(type(s))
    assert False
  if not isinstance(a, int):
    print(a)
    print(type(a))
    assert False
  pass
"""





  def test_const(self):
    src = \
"""
def foo(s: None):
  pass
"""

    expect = \
"""import metap


def foo(s: None):
  if not s == None:
    print(s)
    print(type(s))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_dict(self):
    src = \
"""
def foo(a: int, b: Dict[int, Optional[str]]):
  pass
"""

    expect = \
"""import metap


def foo(a: int, b: Dict[int, Optional[str]]):
  if not isinstance(a, int):
    print(a)
    print(type(a))
    assert False
  if not (isinstance(b, dict) and all([(isinstance(_metap_k1, int) and (
      isinstance(_metap_v2, str) or _metap_v2 is None)) for _metap_k1,
      _metap_v2 in b.items()])):
    print(b)
    print(type(b))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_dict2(self):
    src = \
"""
def foo(a: int, b: Dict[int, List[str]]):
  pass
"""

    expect = \
"""import metap


def foo(a: int, b: Dict[int, List[str]]):
  if not isinstance(a, int):
    print(a)
    print(type(a))
    assert False
  if not (isinstance(b, dict) and all([(isinstance(_metap_k1, int) and (
      isinstance(_metap_v2, list) and all([isinstance(__metap_x3, str) for
      __metap_x3 in _metap_v2]))) for _metap_k1, _metap_v2 in b.items()])):
    print(b)
    print(type(b))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)



  def test_class(self):
    src = \
"""
class Test:
  def __init__(self, a: int):
    self.a = a

  def foo(self, b: int) -> str:
    return str(self.a)
"""

    expect = \
"""import metap


class Test:

  def __init__(self, a: int):
    if not isinstance(a, int):
      print(a)
      print(type(a))
      assert False
    self.a = a

  def __metap_foo(self, b: int) -> str:
    if not isinstance(b, int):
      print(b)
      print(type(b))
      assert False
    return str(self.a)

  def foo(self, b: int) -> str:
    __metap_retv = self.__metap_foo(b)
    if not isinstance(__metap_retv, str):
      print(__metap_retv)
      print(type(__metap_retv))
      assert False
    return __metap_retv
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_non_sub(self):
    src = \
"""
def foo(a: pd.DataFrame):
  pass
"""

    expect = \
"""import metap


def foo(a: pd.DataFrame):
  if not isinstance(a, pd.DataFrame):
    print(a)
    print(type(a))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)


  def test_non_sub2(self):
    src = \
"""
def foo(a: List):
  pass
"""

    expect = \
"""import metap


def foo(a: List):
  if not isinstance(a, list):
    print(a)
    print(type(a))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)







  def test_ret(self):
    src = \
"""
def foo(s: int) -> str:
  pass
"""

    expect = \
"""import metap


def __metap_foo(s: int) -> str:
  if not isinstance(s, int):
    print(s)
    print(type(s))
    assert False
  pass


def foo(s: int) -> str:
  __metap_retv = __metap_foo(s)
  if not isinstance(__metap_retv, str):
    print(__metap_retv)
    print(type(__metap_retv))
    assert False
  return __metap_retv
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)
    



  def test_ret2(self):
    src = \
"""
def foo(s: int) -> Optional[Tuple[str, int]]:
  pass
"""

    expect = \
"""import metap


def __metap_foo(s: int) -> Optional[Tuple[str, int]]:
  if not isinstance(s, int):
    print(s)
    print(type(s))
    assert False
  pass


def foo(s: int) -> Optional[Tuple[str, int]]:
  __metap_retv = __metap_foo(s)
  if not (isinstance(__metap_retv, tuple) and (len(__metap_retv) == 2 and
      isinstance(__metap_retv[0], str) and isinstance(__metap_retv[1], int)
      ) or __metap_retv is None):
    print(__metap_retv)
    print(type(__metap_retv))
    assert False
  return __metap_retv
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_asgn(self):
    src = \
"""
a: Optional[int] = 2
"""

    expect = \
"""import metap
a: Optional[int] = 2
if not (isinstance(a, int) or a is None):
  print(a)
  print(type(a))
  assert False
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_typedefs(self):
    typedefs = \
"""
TableName = str
ColName = str
ColType = Union[int, float, str]
Col = Tuple[ColName, ColType]
Schema = Dict[TableName, List[Col]]
"""

    src = \
"""
def foo(sch: Schema):
  pass
"""

    expect = \
"""import metap


def foo(sch: Dict[str, List[Tuple[str, Union[int, float, str]]]]):
  if not (isinstance(sch, dict) and all([(isinstance(_metap_k1, str) and (
      isinstance(_metap_v2, list) and all([(isinstance(__metap_x3, tuple) and
      (len(__metap_x3) == 2 and isinstance(__metap_x3[0], str) and (
      isinstance(__metap_x3[1], int) or isinstance(__metap_x3[1], float) or
      isinstance(__metap_x3[1], str)))) for __metap_x3 in _metap_v2]))) for
      _metap_k1, _metap_v2 in sch.items()])):
    print(sch)
    print(type(sch))
    assert False
  pass
"""

    out = typedef_boiler(src, typedefs)
    self.assertEqual(out, expect)






  def test_type(self):
    src = \
"""
def foo(t: Type[int]):
  pass
"""

    expect = \
"""import metap


def foo(t: Type[int]):
  if not t is int:
    print(t)
    print(type(t))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_type2(self):
    src = \
"""
def foo(t: Type):
  pass
"""

    expect = \
"""import metap


def foo(t: Type):
  if not isinstance(t, type):
    print(t)
    print(type(t))
    assert False
  pass
"""

    out = boiler(src, dyn_typecheck)
    self.assertEqual(out, expect)




  def test_skip(self):
    src = \
"""
def foo(t: Type):
  pass
"""

    expect = \
"""import metap


def foo(t: Type):
  pass
"""

    out = boiler(src, dyn_typecheck_skip)
    self.assertEqual(out, expect)


class LogCallsStartEnd(unittest.TestCase):
  def test_nested_calls(self):
    src=\
"""
def foo():
  return f"{bar(baz())}"
"""
    expect = \
'''import metap


def foo():
  return f"""{metap.log_start_end(
  print('metap: Started: 3:bar'), bar(metap.log_start_end(
  print('metap: Started: 3:baz'), baz(), 
  print('metap: Finished: 3:baz'))), 
  print('metap: Finished: 3:bar'))}"""
'''

    out = boiler(src, log_calls_start_end3)
    self.assertEqual(out, expect)





  def test_nested(self):
    src = \
"""
with open('d.json', 'w') as fp:
  json.dump(find_primes(1_000_000), fp)
"""

    expect = \
"""import metap
with open('d.json', 'w') as fp:
  json.dump(metap.log_start_end(
  print('metap: Started: 3:find_primes'), find_primes(1000000), 
  print('metap: Finished: 3:find_primes')), fp)
"""

    out = boiler(src, log_calls_start_end1)
    self.assertEqual(out, expect)


  def test_nested2(self):
    src = \
"""
with open('d.json', 'w') as fp:
  json.dump(find_primes(1_000_000), fp)
"""

    expect = \
"""import metap
with open('d.json', 'w') as fp:
  metap.log_start_end(
  print('metap: Started: 3:json.dump'), json.dump(find_primes(1000000), fp), 
  print('metap: Finished: 3:json.dump'))
"""

    out = boiler(src, log_calls_start_end2)
    self.assertEqual(out, expect)




def expand_asserts(fname):
  mp = metap.MetaP(filename=fname)
  mp.expand_asserts()
  mp.dump()

class ExpandAsserts(unittest.TestCase):
  def test_neq(self):
    src = \
"""
a = 2
def foo():
  global a
  a = a + 1
  return a

assert foo() != 3
"""

    expect = \
"""import metap
a = 2


def foo():
  global a
  a = a + 1
  return a


_metap_l = foo()
_metap_r = 3
if _metap_l == _metap_r:
  print(_metap_l)
  print(_metap_r)
  assert False
"""

    out = boiler(src, expand_asserts)
    self.assertEqual(out, expect)




  def test_isisntance(self):
    src = \
"""
a = 2
def foo():
  global a
  a = a + 1
  return a

assert isinstance(foo(), float)
"""

    expect = \
"""import metap
a = 2


def foo():
  global a
  a = a + 1
  return a


_metap_obj = foo()
if not isinstance(_metap_obj, float):
  print(_metap_obj)
  print(type(_metap_obj))
  assert False
"""

    out = boiler(src, expand_asserts)
    self.assertEqual(out, expect)

if __name__ == '__main__':
    unittest.main()
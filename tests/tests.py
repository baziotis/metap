import unittest
import metap
import os

def ret_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_returns()
  mp.dump()

def cont_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_continues()
  mp.dump()

def break_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.log_breaks()
  mp.dump()

def retif_func(fname):
  mp = metap.MetaP(filename=fname)
  mp.compile()
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
    __ret_ifnn(helper(n))
  return None

def main(xs):
  for x in xs:
    __ret_ifnn(foo(x))
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
    
    out = boiler(src, retif_func)
    self.assertEqual(out, expect)
    


class RetIfn(unittest.TestCase):
  def test_simple(self):
    src = \
"""
def foo(ns):
  for n in ns:
    __ret_ifn(helper(n))
  return None

def main(xs):
  for x in xs:
    __ret_ifn(foo(x))
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
    
    out = boiler(src, retif_func)
    self.assertEqual(out, expect)

if __name__ == '__main__':
    unittest.main()
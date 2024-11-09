# Inspired by Dias code.

def helper(n):
  if n == 2:
    return 3
  return None

def foo(ns):
  for n in ns:
    __ret_ifnn(helper(n))
  ### END FOR ###
  return None

def main(xs):
  for x in xs:
    __ret_ifnn(foo(x))
  ### END FOR ###
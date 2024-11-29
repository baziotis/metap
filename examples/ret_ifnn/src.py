# Inspired by Dias code.

def helper(n):
  if n == 2:
    return 3
  return None

def foo(ns):
  for n in ns:
    _ret_ifnn(helper(n))
  ### END FOR ###
  return None

print(foo([2, 3]))
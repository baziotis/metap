from typing import Optional, Tuple

def foo(s: int) -> Optional[Tuple[str, int]]:
  if s == 2:
    return "1", 2
  return 4

try:
  foo(3.2)
except AssertionError:
  print("input is float")

foo(2)

try:
  foo(3)
except AssertionError:
  print("return value doesn't match annotation")
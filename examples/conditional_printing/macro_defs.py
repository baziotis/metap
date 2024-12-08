# We need to handle varargs in this.
def _cprint(s):
  stmt : NODE = {
if do_print:
  print(<s>)
}
  return stmt

# Marc Canby came up with this.
#
# To do that with a macro like `_cprint`, we would need to be able to
# partially evaluate it, which is harder.
def _cprint_lam(c):
  stmt : NODE = {
def printc(*args):
  if <c>:
    print(*args)  
}
  return stmt
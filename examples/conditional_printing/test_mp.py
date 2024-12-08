def foo(do_print):
  _cprint('foo() was called')

def bar(do_print):
  _cprint_lam(do_print)
  d = {'foo': 2}
  printc('bar was called:', d)

foo(True)
bar(True)
import pytest
import os
import types
import metap

def exec_code(code, mod):
  # Note: Exec's update the module's dict
  exec(compile(code, mod.__name__, 'exec'), mod.__dict__)

def boiler(mprogram, client):
  fname = 'test.py'
  with open(fname, 'w') as fp:
    fp.write(mprogram)

  mod_client = types.ModuleType('Client')
  exec_code(client, mod_client)
  
  out_fname = 'test.metap.py'
  with open(out_fname, 'r') as fp:
    out = fp.read()
  os.remove(fname)
  os.remove(out_fname)

  mod_c = types.ModuleType('Code')
  exec_code(out, mod_c)

  return mod_c

CVAR_CLIENT = """
import metap

mp = metap.MetaP(filename='test.py')
mp.compile()
mp.dump()
"""

def test_cvar():
  mprogram = """
line = "# test"
if _cvar(line.startswith('# '), hlvl, 1):
  x = hlvl
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = 1

  assert actual == expected
  del mod
  
def test_cvar2():
  mprogram = """
line = "# test"
if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = 1

  assert actual == expected
  del mod

def test_cvar3():
  mprogram = """
line = "## test"
if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = 2

  assert actual == expected
  del mod

def test_cvar4():
  mprogram = """
line = "### test"
if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
else:
  x = 'hlvl' not in globals()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = True

  assert actual == expected
  del mod

def test_cvar5():
  mprogram = """
line = "## test"
if _cvar(line.startswith('# '), hlvl, 1):
  y = hlvl
elif _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = 2

  assert actual == expected
  del mod


def test_cvar6():
  mprogram = """
line = "# test"
if _cvar(line.startswith('# '), hlvl, 1):
  x = hlvl
  if _cvar(line.startswith('# t'), start, 't'):
    z = start
elif _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  x_act= mod.__dict__['x']
  z_act= mod.__dict__['z']
  
  x_exp = 1
  z_exp = 't'

  assert x_act == x_exp
  assert z_act == z_exp
  del mod

def test_cvar7():
  mprogram = """
line = "## test"
if _cvar(line.startswith('# '), hlvl, 1):
  x = hlvl
  if _cvar(line.startswith('# t'), start, 't'):
    z = start
elif _cvar(line.startswith('## '), hlvl, 2):
  y = 'start' not in globals()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  y_act= mod.__dict__['y']
  
  y_exp = True

  assert y_act == y_exp
  del mod

def test_cvar8():
  mprogram = """
line = "## test"
if _cvar(line.startswith('# '), hlvl, 1):
  x = hlvl
elif _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
  if _cvar(line.startswith('## t'), start, 't2'):
    z = start
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  x_act= mod.__dict__['x']
  z_act= mod.__dict__['z']
  
  x_exp = 2
  z_exp = 't2'

  assert x_act == x_exp
  assert z_act == z_exp
  del mod

def test_cvar9():
  mprogram = """
line = "### test"
if _cvar(line.startswith('# '), hlvl, 1):
  x = hlvl
elif _cvar(line.startswith('## '), hlvl, 2):
  x = hlvl
else:
  x = 'hlvl' not in globals()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = True

  assert actual == expected
  del mod

def test_cvar10():
  mprogram = """
line = "### test"
hlvl = None
if _cvar(line.startswith('# '), hlvl, 1):
  pass
elif _cvar(line.startswith('## '), hlvl, 2):
  pass
else:
  pass
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['hlvl']
  expected = None

  assert actual == expected
  del mod

def test_cvar11():
  mprogram = """
line = "# test"
hlvl = None
if _cvar(line.startswith('# '), hlvl, 1):
  pass
elif _cvar(line.startswith('## '), hlvl, 2):
  pass
else:
  pass
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['hlvl']
  expected = 1

  assert actual == expected
  del mod


def test_cvar_inside_function():
  mprogram = """
def foo():
  line = "## test"
  if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
    x = hlvl
  
  return x

y = foo()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['y']
  expected = 2

  assert actual == expected
  del mod

def test_cvar12():
  mprogram = """
hlvl = None
def foo():
  line = "## test"
  if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
    pass

foo()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['hlvl']
  expected = None

  assert actual == expected
  del mod

def test_cvar13():
  mprogram = """
hlvl = None
def foo():
  global hlvl
  line = "## test"
  if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
    pass

foo()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['hlvl']
  expected = 2

  assert actual == expected
  del mod


def test_cvar_def():
  mprogram = """
line = "# test"
if _cvar(line.startswith('# '), c):
  x = c
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['x']
  expected = True

  assert actual == expected
  del mod


# TODO: We may want to change the semantics so that for cvar2 it's assigned no
# matter whether we get into the if or not. That is simple. If it has an else,
# add the assignment in the else. Otherwise, introduce an else and add it.
def test_cvar_def2():
  mprogram = """
line = "## test"
if _cvar(line.startswith('# '), c):
  x = c

y = 'x' in globals()
"""

  mod = boiler(mprogram, CVAR_CLIENT)

  actual = mod.__dict__['y']
  expected = False

  assert actual == expected
  del mod
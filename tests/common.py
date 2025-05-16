import os
import metap

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

def boiler2(src, mid_func):
  fname = 'test.py'
  with open(fname, 'w') as fp:
    fp.write(src)

  out = mid_func(fname)

  out_fname = 'test.metap.py'
  os.remove(fname)
  os.remove(out_fname)

  return out


def dyn_typecheck(fname):
  mp = metap.MetaP(filename=fname)
  mp.dyn_typecheck()
  mp.dump()
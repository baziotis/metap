import gen_lib
import ast, astor
import os

file_dir = os.path.dirname(os.path.abspath(__file__))

defaults_path = os.path.join(file_dir, "default_defs.py")

t = gen_lib.gen_macros(defaults_path)

macro_defs = set()
for fdef in t.body:
  if isinstance(fdef, ast.FunctionDef):
    macro_defs.add(fdef.name)
  # END IF #
### END FOR ###

src = astor.to_source(t, indent_with=" "*2)

src += f"""
macro_defs = {macro_defs}
"""

imports = """
from . import rt_lib

"""

src = imports + src

with open('default_impl.py', 'w') as fp:
  fp.write(src)
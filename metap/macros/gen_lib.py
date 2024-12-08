import ast, astor
import re
import argparse

def skip_space(s, idx):
  first_non_whitespace_pos = len(s[idx:]) - len(s[idx:].lstrip())
  return idx+first_non_whitespace_pos

def replace_substr(s, start, end, new_str):
  return s[:start] + new_str + s[end:]

def replace_curlies(s):
  start = 0
  ann = ": NODE"
  ann_len = len(ann)
  while True:
    start = s.find(ann, start)
    if start == -1:
      break
    # after ann
    idx = start+ann_len
    idx = skip_space(s, idx)
    if not (s[idx] == '='):
      raise Exception("`=` expected after :NODE annotation.")
    idx += 1
    idx = skip_space(s, idx)
    if not (s[idx] == '{'):
      raise Exception("The RHS of a :NODE assignment must start with {.")
    curly_begin = idx
    rhs_begin = idx+1
    
    # There should be no curlies in the RHS, so we can just search for `}`.
    #
    # TODO: There may be comments with curlies inside. Not sure if we should care
    # about those.
    rhs_end = s.find('}', idx)
    
    assert rhs_begin <= rhs_end
    rhs = s[rhs_begin:rhs_end]
    # rhs = rhs.strip()
    if len(rhs) == 0:
      raise Exception("An empty RHS is not allowed.")
    
    if '"""' in rhs:
      raise Exception("Triple quotes are currently not supported in the RHS.")
    
    new_rhs = f'"""{rhs.strip()}"""'
    new_rhs = re.sub(r"<(.*?)>", r"_metap_\1", new_rhs)
    s = replace_substr(s, curly_begin, rhs_end+1, new_rhs)
    start = curly_begin+len(new_rhs)

  ### END WHILE ###

  return s

class CallParse(ast.NodeTransformer):
  def visit_AnnAssign(self, asgn: ast.AnnAssign):
    ann = asgn.annotation

    if not (isinstance(ann, ast.Name) and ann.id == 'NODE'):
      return asgn

    lhs = asgn.target
    rhs = asgn.value
    assert isinstance(rhs, ast.Constant) and isinstance(rhs.value, str)
    parse_call = ast.Call(
      func=ast.Attribute(value=ast.Name('ast'), attr='parse'),
      args=[rhs],
      keywords=[]
    )
    locals_call = ast.Call(
      func=ast.Name(id="locals"),
      args=[],
      keywords=[]
    )
    replace_bindings_call = ast.Call(
      func=ast.Attribute(value=ast.Name(id="rt_lib"), attr='replace_bindings'),
      args=[parse_call, locals_call],
      keywords=[]
    )
    new_ann = ast.Attribute(value='ast', attr='AST')
    new_asgn = ast.AnnAssign(
      target=lhs,
      annotation=new_ann,
      value=replace_bindings_call,
      simple=1
    )

    return new_asgn


def gen_macros(input_file):
  with open(input_file, 'r') as fp:
    s = fp.read()

  s = replace_curlies(s)

  t = ast.parse(s)
  v = CallParse()
  v.visit(t)

  return t
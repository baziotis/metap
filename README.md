An easy-to-use meta-programming layer for Python.

# Motivation

`metap` is an easy-to-use meta-programming layer for Python. It allows you to
write programs that generate programs. That sounds fancy, but in practice
`metap` just automates tedious program transformations and programming patterns.

# Installation

First (because `metap` needs a bug-fixed version of `astor`):
```
pip install git+https://github.com/baziotis/astor#egg=astor
```

Then:
```
pip install metap
```


# Quickstart

`metap` works with two scripts: (a) A client, and (b) a meta-program. The
metap-program is just a Python program, except it _may_ have `metap`-specific
features. The client tells `metap` how to process your meta-program to generate
another Python program.

Here's a simple example. Let's say you have the following meta-program, in
the file `test_mp.py`:

```python
# test_mp.py
def foo():
  return 2

def bar():
  a = 2

  if a == 2:
    return 4
  
foo()
bar()
```

In this simple example, the meta-program has nothing `metap`-specific. You can
just run it with Python as it is. But, you can still tell a client to transform
it in various useful ways. For example, you may want to log all the `return`s.
So, we write a simple client:

```python
# client.py
from metap import MetaP

mp = MetaP(filename="test_mp.py")
mp.log_returns(include_fname=True)
mp.dump(filename="test.py")
```

This says the minimum `metap` needs to know: which file to load (`test_mp.py`),
what to do (log the returns), and dump the result in `test.py`. Now, we first
run:

```bash
python client.py
```

to produce `test.py`. Then, we run it:

```bash
python test.py
```

which produces:

```bash
metap::test_mp.py::Return(ln=3)
metap::test_mp.py::Return(ln=9)
```

`metap` allows you to log all kinds of things, optionally supporting indentation
and only logging within ranges. 

Another useful feature is dynamic type checking. Python accepts type annotations
in e.g., variable declarations, function parameters and return types. These
annotations are not checked statically or dynamically by default. `metap` can
enter generate code that the dynamic values agree with the annotations. For
example, for the following code:

```python
def foo(s: str):
  pass
```

and using the `dyn_typecheck()` feature, `metap` generates:

```python
def foo(s: str):
  if not isinstance(s, str):
    print(s)
    print(type(s))
    assert False
  pass
```

`metap` supports pretty complex annotations, e.g., `Optional[Tuple[List[str], List[int]]]`.

To finish this quickstart guide, things get really interesting when the
meta-program starts using `metap`-specific features.

This example is taken straight from actual code I've written for a
markdown-to-html compiler I use to write [my articles](https://sbaziotis.com/#blog). I want to parse a line and I
want to see if it's a heading, which means it starts with `#`. But, I also care
about whether it's a level-1 heading (i.e., `<h1>`) or level-2 (i.e.,
`<h2>`), to generate the appropriate code. With `metap` I can simply write
the following:

```python
# mdhtml_mp.py
line = "# test"
if (_cvar(line.startswith('# '), hlvl, 1) or
    _cvar(line.startswith('## '), hlvl, 2)):
  print(hlvl)
```

and I use the following client:

```python
from metap import MetaP

mp = MetaP(filename="mdhtml_mp.py")
mp.compile()
mp.dump(filename="mdhtml.py")
```

`mp.compile()` handles _all_ the `metap`-specific features in a single call.
After generating `mdhtml.py` and running it, we get `1`. You can tell how useful
this is by trying to write it in standard Python :)



# API Table of Contents

Table of Contents:
- [Client API](#client-api)
  - [`MetaP`](#class-metap)
  - [`log_returns()`](#metaplog_returns)
  - [`log_breaks()` and `log_continues()`](#log_breaks-and-log_continues)
  - [`log_calls()`](#metaplog_calls)
  - [`log_calls_start_end()`](#metaplog_calls_start_end)
  - [`log_func_defs()`](#metaplog_func_defs)
  - [`log_ifs()`](#metaplog_ifs)
  - [`dyn_typecheck()`](#metapdyn_typecheck)
  - [`expand_asserts()`](#metapexpand_asserts)
  - [`dump()`](#metapdump)
  - [`compile()`](#metapcompile)
- [`metap` superset of Python](#metap-superset-of-python)
  - [User-Defined Macros](#user-defined-macros)
    - [Conditional Returns](#conditional-returns)
    - [Printing](#printing)
  - [Other built-in features](#other-built-in-features)
    - [`cvar()`](#cvar)
    - [`time_e()`](#time_e)


# Client API

## `class MetaP`

The whole API is under the `MetaP` class. Fields:

- `filename`: The path to the meta-program.

### `MetaP.log_returns()`

**Parameters**:
- `include_fname: str`: Optional. Include the filename in the logs
- `range: List[Union[int, Tuple[int, int]]]`: Optional. Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range). 

**Example**

See [Quickstart](#quickstart).


### `log_breaks()` and `log_continues()`

Similar to `log_returns()` but for `break` and `continue`.

**Parameters**:
- `range: List[Union[int, Tuple[int, int]]]`: Optional. Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range). 


### `MetaP.log_calls()`

Log call-sites

**Parameters**:
- `range: List[Union[int, Tuple[int, int]]]`: Optional. Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range). 

**Example**

```python
# test_mp.py
def add_one(num):
  return num + 1

for x in [0, 1, 2]:
  if x != 0:
    add_one(x)
```

```python
# client.py
import metap
mp = metap.MetaP(filename='test_mp.py')
mp.log_calls()
mp.dump('test.py')
```

Running the generated `test.py`, we get:
```
metap::Call(ln=6,call=add_one(x))
metap::Call(ln=6,call=add_one(x))
```

### `MetaP.log_calls_start_end()`

Prints a message before and after calls matching a pattern.

**Parameters**:
- `patt: Pattern`: Optional. A regular expression. Only function calls that have
  function names that match this pattern are logged.
- `range: List[Union[int, Tuple[int, int]]]`: Optional. Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range). 

**Simple Example**

```python
# test_mp.py
with open('d.json', 'w') as fp:
  json.dump(d, fp)
```

```python
import metap
mp = metap.MetaP(filename="test_mp.py")
mp.log_calls_start_end(patt=r'.*json\.dump')
mp.dump(filename="test.py")
```

Running the generated `test.py` gives us:
```
metap: Started executing: 3:json.dump
metap: Finished executing: 3:json.dump
```

### `MetaP.log_func_defs()`

Log when we get into functions.

**Parameters**:
- `range: List[Union[int, Tuple[int, int]]]`: Optional. Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range).
- `indent: bool`: Indent the logs such that the indentation is proportional to a call's depth.

**Example**

```python
# test_mp.py
import ast

class RandomVisitor(ast.NodeVisitor):
  def visit_Assign(self, asgn:ast.Assign):
    for t in asgn.targets:
      self.visit(t)
    self.visit(asgn.value)
  
  def visit_BinOp(self, binop:ast.BinOp):
    self.visit(binop.left)
    
code = """
a = b + 2
"""

t = ast.parse(code)
v = RandomVisitor()
v.visit(t)
```

```python
# client.py
import metap
mp = metap.MetaP(filename='test_mp.py')
mp.log_func_defs(indent=True)
mp.dump('test.py')
```

Running the generated `test.py`, we get:
```
metap::FuncDef(ln=4,func=visit_Assign)
  metap::FuncDef(ln=9,func=visit_BinOp)
```


### `MetaP.log_ifs()`

**Parameters**:
- `range: List[Union[int, Tuple[int, int]]]`: Optional. Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range). 
- `indent: bool`: Indent the logs such that the indentation is proportional to
  the nesting depth.

**Example**:

```python
# test_mp.py
if True:
  if False:
    pass
  else:
    pass
  
  if True:
    pass
else:
  pass
```

```python
# client.py
import metap
mp = metap.MetaP(filename='test_mp.py')
mp.log_ifs(indent=True, range=[1, (7, 10)])
mp.dump('test.py')
```

Running the generated `test.py`, we get:
```
metap::If(ln=1)
  metap::If(ln=7)
```

Note that the inner `if` with the `else` was not logged because it's not within the ranges.

### `MetaP.dyn_typecheck()`

Adds asserts that verify type annotations in function arguments, returns, and
assignments.

**Parameters**:
- `typedefs_path: str`: Optional. Path to a file with typedefs of the form
  `name = annotation` if the annotations in the main file use anything other than
  the supported names from the `typing` module.
- `skip_funcs: List[str]`: Optional. A list of function names to skip.

Currently supported annotations from `typing`: `Optional`, `Union`, `Tuple`, `List`, `Dict`

**Simple Example**

```python
# test_mp.py
def foo(s: Optional[str]):
  pass
```

```python
# client.py
import metap
mp = metap.MetaP(filename='test_mp.py')
mp.dyn_typecheck()
mp.dump('test.py')
```

The generated `test.py` is:

```python
def foo(s: Optional[str]):
  if not (isinstance(s, str) or s is None):
    print(s)
    print(type(s))
    assert False
  pass
```

**Using Custom Typedefs**

```python
# typedefs.py
TableName = str
ColName = str
ColType = Union[int, float, str]
Col = Tuple[ColName, ColType]
Schema = Dict[TableName, List[Col]]
```

```python
# test_mp.py
def foo(sch: Schema):
  pass
```

```python
# client.py
import metap
mp = metap.MetaP(filename='test_mp.py')
mp.dyn_typecheck()
mp.dump('test.py')
```

### `MetaP.expand_asserts()`

Expands some asserts such that if they fire, you get some info on the expressions involved.

**Parameters**: None

**Simple Example**

```python
a = 2
def foo():
  global a
  a = a + 1
  return a

assert foo() != 3
```

```python
# ...
mp.expand_asserts()
```

The generated `test.py` is:

```python
# ... Same as before
_metap_l = foo()
_metap_r = 3
if _metap_l == _metap_r:
  print(_metap_l)
  print(_metap_r)
  assert False
```

Currently it supports (in)equals (e.g., `assert a == b`) and `isinstance()`
calls (e.g., `assert isinstance(a, int)`).


### `MetaP.dump()`

Generate valid Python code and dump it to a file.

**Parameters**:
- `filename: str`: Optional. If not provided, `metap` will use `<original name>.metap.py`.


### `MetaP.compile()`

Compiles anything that is necessary to be handled to get valid Python. See the
following section.

**Parameters**:
- `macro_defs_path: str`: Optional. A file that includes definitions of user-defined macros.



# `metap` Superset of Python

All the features we've seen up to now make running a `metap` client _optional_.
In other words, you could just run the `test_mp.py` programs without using a
client at all. However, these features complement an existing program, but they
don't make writing the program in the first place any easier. This is where a
meta-programming layer truly shines. The following features form an extensible
superset of Python, which lets you add features that allow you to automatically
generate code.

To generate a valid Python program, you just need a client that calls
[`compile()`](#metapcompile). `compile()` will handle everything that needs to be
translated for the code to be valid Python (so, everything that follows).


## User-Defined Macros

`metap` automates domain-specific, or even user-specific patterns. To allow
that, it should allow users to define their own patterns. Currently, this is
done with macros, which can be user-defined.

The basic idea for macros is that to treat code as values that e.g., can be
returned or be combined with other values. In practice, a macro definition
returns a piece of code. To use the macro, we just call it as a function and the
code that the macro returns takes the place of the macro call.

Here's an example of a macro definition in a file `macro_defs.py`:

```python
# macro_defs.py
def _ret_ifnn(x):
  stmt : NODE = {
_tmp = <x>
if _tmp is not None:
  return _tmp
}
  return stmt
```

Then, we can use this macro as follows:

```python
def foo(x):
  _ret_ifnn(bar(x))
```

Using a simple client and `mp.compile(macro_defs_path='macro_defs.py')`, we get:

```python
def foo(x):
  _tmp = bar(x)
  if _tmp is not None:
    return _tmp
```

The only thing to be careful about is that these macros can be used where a
**statement** (e.g., a `return`, an `if`, but not a function argument, or an
expression `2+3`) can be used. For example, the following will give you an
error:

```python
foo(_ret_ifn(x))
```

Finally, note that you can compose macros with other `MetaP` methods. For
example, you can issue `mp.compile()`, which will create the `if-return`, and
then use `mp.log_returns()` which will log the generated returns (but using the
line numbers of the original call).

The following subsections describe some macros defined by default.

### Conditional Returns

`metap` currently supports 4 kinds of conditional returns

```python
# Return None if `x` is None
def _ret_ifn(x):
  stmt : NODE = {
if <x> is None:
  return None
}
  return stmt

# Return `x` if `x` is not None
def _ret_ifnn(x):
  stmt : NODE = {
_tmp = <x>
if _tmp is not None:
  return _tmp
}
  return stmt

# Return False if `x` is False
def _ret_iff(x):
  stmt : NODE = {
if <x> == False:
  return False
}
  return stmt

# Return True if `x` is True
def _ret_ift(x):
  stmt : NODE = {
if <x> == True:
  return True
}
  return stmt
```

### Printing

`metap` supports `_mprint(e)`, which gets an expression `e` as input and prints
both the expression's text and its value. For example this:

```python
def foo():
  return 2
x = 3
_mprint(x)
_mprint(foo())
```

will print:

```
x: 3
foo(): 2
```

## Other built-in features

### Assignments in Conditions - `cvar()`

**Example**

See [Quickstart](#quickstart).

**Example 2**:

I'll present a slight variation of `_cvar`, where the variable takes the value
of the condition, no matter whether it's true or false.

```python
if _cvar(line.startswith('# '), c):
  # c gets the value True
else:
  # c gets the value False
```

This is basically similar to C++'s:

```c++
if (c = line.startswith("# "))
```

**Usage notes**:

Currently `_cvar()` works only in `if-elif` conditions.

### Time expressions - `time_e()`

Time expression.

**Parameters**:
- `e`: Any expression


**Example**:

```
res, ns = _time_e(2 + 3)
```

`res` gets `5` and `ns` gets the timing in nanoseconds.

# Status

`metap` is still in an experimental version, so it should be used with caution
in production. But, it is under active development. Moreover, thankfully `metap`
provides many features that don't _require_ you to run `metap` to get valid
Python. For example, you can use `log_returns()` during debugging and then just
use what you wrote (i.e., the original meta-program, without going through
`metap`) in production.

# Contributing

The most useful contributions at the moment are bug reports and feature requests
(both in the form of [Github issues](https://github.com/baziotis/metap/issues)).
But, pull requests are always welcome.
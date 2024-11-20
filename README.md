An easy-to-use meta-programming layer for Python.

# Motivation

Over the years, I've come across several language features which would make my
Python programming much easier, which will probably not make it into the
language any time soon. I finally decided to implement a tool that allows me to
have these features.

The obvious solution would be to actually extend the language, but it has
serious drawbacks. First, it's a [hefty task](https://aroberge.github.io/ideas/docs/html/#ideas-making-it-easier-to-extend-python-s-syntax). But most importantly, it would be hard to reuse the work across
environments, machines, etc., because I would have to have my custom version of
Python everywhere. The solution that is both fun and useful is a
_meta-programming_ layer.

Hence, I created `metap`, an easy-to-use meta-programming layer for Python,
which basically allows us to write programs that generate programs. That sounds
fancy, but in practice our meta-program is just a Python program with a couple
of extra features.


# Quickstart

First, just `pip install metap`.

`metap` works with two scripts: (a) A client, and (b) a meta-program, both
written in Python. This sounds complex but basically your meta-program is just
your program, except it _may_ have `metap`-specific features. The client tells
`metap` how to process your meta-program to generate the actual program.

So, here's a simple example. Let's say you have the following meta-program, in
file `test_mp.py`:

```python,linenos
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
just run it with Python as it is. But, you can still do things to it; for
example, log all the `return`s. So, we write a simple client:

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

to produce `test.py`. And then we run it:

```bash
python test.py
```

which produces:

```bash
metap::test_mp.py::Return(ln=3)
metap::test_mp.py::Return(ln=9)
```

So, every time a return fires, we log it. Note that `metap` retained the line
numbers of the _original_ program (i.e., the meta-program), which is what you
want because this is what you're working on. 

`metap` allows you to log all kinds of things, optionally supporting indentation
and indexing. Here's another simple example of logging when we enter into function bodies:

```python,linenos
# test_mp.py
def bar():
  return 2

def baz():
  return 3

def foo(n):
  if n == 2:
    return foo(3)
  a = bar()
  b = baz()

foo(2)
```

Now, using `mp.log_func_defs(indent=True)` and running the produced `test.py`
we get:

```
metap::FuncDef(ln=7,func=foo)
  metap::FuncDef(ln=7,func=foo)
    metap::FuncDef(ln=1,func=bar)
    metap::FuncDef(ln=4,func=baz)
```

To finish this quickstart guide, let's see when things really get interesting,
and that's when the meta-program starts using `metap`-specific features.

This example is taken straight from actual code I've written for
markdown-to-html compiler I wrote (which is used to generate the HTML for the
article you're reading). I want to parse a line and I want to see if it's a
heading, which means it starts with `#`. But, I also care about whether it's a
level-1 heading (i.e., `&lt;h1&gt;`) or level-2 (i.e., `&lt;h2&gt;`), to
generate the appropriate code. With `metap` I can simply write the following:

```python
# mdhtml_mp.py
line = "# test"
if _cvar(line.startswith('# '), hlvl, 1) or _cvar(line.startswith('## '), hlvl, 2):
  print(hlvl)
```

and I use the following client:

```python
from metap import MetaP

mp = MetaP(filename="mdhtml_mp.py")
mp.compile()
mp.dump(filename="mdhtml.py")
```

`mp.compile()` handles _all_ the `metap`-specific features in a single call. After
generating `mdhtml.py` and running it, I get `1`. You can tell how useful this
is by trying to write it in standard Python :)



# API

## `class MetaP`

The whole API is under the `MetaP` class. Fields:

- `filename`: The path to the meta-program.

## Logging

### `MetaP.log_returns()`

**Parameters**:
- `include_fname: str`: Include the filename in the logs
- `range: List[Union[int, Tuple[int, int]]]`: Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range). 

**Example**

See [Quickstart](#quickstart).


### `log_breaks()` and `log_continues()`

Similar to `log_returns()` but for `break` and `continue`.


### `MetaP.log_calls()`

Log all call-sites

**Parameters**:
- `range: List[Union[int, Tuple[int, int]]]`: Only log returns within the line
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

### `MetaP.log_func_defs()`

Log all call-sites

**Parameters**:
- `range: List[Union[int, Tuple[int, int]]]`: Only log returns within the line
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
- `range: List[Union[int, Tuple[int, int]]]`: Only log returns within the line
  ranges provided. `range` gets a list that can have either integers (denoting a
  single line), or a pair of integers (denoting a `[from, to]` range).
- `indent: bool`: Indent the logs such that the indentation is proportional to a call's depth.

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

Note that the inner `if` with the else was not logged because it's not within the ranges.

## `MetaP.add_asserts()`

Adds asserts that verify type annotations in function arguments and returns.

**Parameters**: None

**Simple Example*

```python
# test_mp.py
def foo(s: Optional[str]):
  pass
```

```python
import metap
mp = metap.MetaP(filename='test_mp.py')
mp.add_asserts()
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

## `MetaP.log_calls_start_end()`

Prints a message before and after calls matching a pattern.

**Parameters**:
- `patt: Pattern`: Regular expression. Only function calls that have function names that match this pattern are logged.

**Simple Example*

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
metap: Started executing: 3:json.dump('d.json', fp)
metap: Finished executing: 3:json.dump('d.json', fp)
```

## Superset of Python and Non-Optional Compilation

All the features we've seen up to now make running a `metap` client _optional_. In other words, you could just run the `test_mp.py` programs without using a client at all.

All the following features extend the Python programming language so using a `metap` client is non-optional. All these features are handled by `MetaP.compile()`. So, all the clients in all the following examples are simply:

```python
import metap

mp = metap.MetaP(filename='test_mp.py')
mp.compile()
mp.dump('test.py')
```

## `__ret_ifnn()` and `__ret_ifn()`

**Parameters**:
- `e`: Any expression.

This feature introduces two new statements that return only under a condition.
By far the two most common conditions in practice are: (1) return `x` if `x` is not
`None` and (2) return `None` if `x` is `None`. Both can be expressed simply
with:

**Example**

```python
# test_mp.py

# Return None if `x` is None
__ret_ifn(x)
# Return `x` if `x` is not None
__ret_ifnn(x)
```

The generated `test.py` is equivalent to:

```python
if x is None:
  return None
if x is not None:
  return x
```

**Usage notes**:

You can use these statements wherever you'd use a return statement. Note that it
_looks_ like a function call but you should think of it as a statement. For
example, the following will _not_ compile:

```python
foo(__ret_ifn(x))
```

Also, note that you can compose this feature with logging returns. For example, you
can issue `mp.compile()`, which will create the `if-return`, and then use
`mp.log_returns()` which will log the generated returns (but using the line
numbers of the original call).

## `cvar()`

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

## `time_e()`

Time expression.

**Parameters**:
- `e`: Any expression


**Example**:

```
res, ns = _time_e(2 + 3)
```

`res` gets `5` and `ns` gets the timing in nanoseconds.

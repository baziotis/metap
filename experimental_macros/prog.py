def foo(x):
  return x


def bar(x):
  if x is not False:
    return x


print(foo(2))
y = True
print(bar(y))

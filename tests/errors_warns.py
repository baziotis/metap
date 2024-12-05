import unittest
import metap.errors_warns as errors_warns
import common
import warnings

class TestUnsupported(unittest.TestCase):
  def test_dyn_typecheck(self):
    src = \
"""
s: AnyStr = 2
"""
    with self.assertRaises(errors_warns.UnsupportedError) as context:
      common.boiler(src, common.dyn_typecheck)
    # END WITH #
    self.assertEqual(str(context.exception), "dyn_typecheck: 2: AnyStr annotation is not supported.")




  def test_dyn_typecheck_ret(self):
    src = \
"""
def stop() -> NoReturn:
  raise RuntimeError('no way')
"""
    with self.assertRaises(errors_warns.UnsupportedError) as context:
      common.boiler(src, common.dyn_typecheck)
    # END WITH #
    self.assertEqual(str(context.exception), "dyn_typecheck: 2: NoReturn annotation is not supported.")






  def test_dyn_typecheck_arg(self):
    src = \
"""
def stop(alias: TypeAlias):
  pass
"""
    with self.assertRaises(errors_warns.UnsupportedError) as context:
      common.boiler(src, common.dyn_typecheck)
    # END WITH #
    self.assertEqual(str(context.exception), "dyn_typecheck: 2: TypeAlias annotation is not supported.")




  def test_dyn_typecheck_sub(self):
    src = \
"""
def stop(alias: Literal[True]):
  pass
"""
    with self.assertRaises(errors_warns.UnsupportedError) as context:
      common.boiler(src, common.dyn_typecheck)
    # END WITH #
    self.assertEqual(str(context.exception), "dyn_typecheck: 2: Literal annotation is not supported.")





  def test_dyn_typecheck_sub2(self):
    src = \
"""
def stop(alias: Concatenate[P, K]):
  pass
"""
    with self.assertRaises(errors_warns.UnsupportedError) as context:
      common.boiler(src, common.dyn_typecheck)
    # END WITH #
    self.assertEqual(str(context.exception), "dyn_typecheck: 2: Concatenate annotation is not supported.")




  def test_dyn_typecheck_totally_unknown(self):
    src = \
"""
a: foo()[other] = 2
"""
    with self.assertRaises(errors_warns.UnsupportedError) as context:
      common.boiler(src, common.dyn_typecheck)
    # END WITH #
    self.assertEqual(str(context.exception), "dyn_typecheck: 2: foo()[other] annotation is not supported.")




  def test_dyn_typecheck_nonname_targ(self):
    src = \
"""
d['test']: int = 2
"""

    with warnings.catch_warnings(record=True) as w:
      warnings.simplefilter("always")  # Ensure all warnings are triggered
      common.boiler(src, common.dyn_typecheck)
      self.assertEqual(len(w), 1)  # Ensure one warning was raised
      self.assertEqual(w[0].category, errors_warns.UnsupportedWarning)  # Check warning category
      self.assertEqual(str(w[0].message), "dyn_typecheck: 2: Annotations in assignments are only supported if the target (LHS) is an identifier. Skipping...")  # Check warning message
    # END WITH #



if __name__ == '__main__':
  unittest.main()

class UnsupportedError(Exception):
  def __init__(self, message=None):
    super().__init__(message)
    self.message = message

class APIError(Exception):
  def __init__(self, message=None):
    super().__init__(message)
    self.message = message

class UnsupportedWarning(Warning):
  def __init__(self, message=None):
    super().__init__(message)
    self.message = message

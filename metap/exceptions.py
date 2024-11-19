import sys
import traceback
import dill
import types

MODULES_TO_SAVE = to be filled



def include_in_state(var_name, value):
  unpicklable_types = (types.ModuleType, types.FunctionType,
                        types.MethodType)
  # return not var_name.startswith('__')
  return (not var_name.startswith('__') and 
          not isinstance(value, unpicklable_types))

def get_module_variables(module, visited=None):
  if visited is None:
    visited = set()
  module_name = getattr(module, '__name__', None)
  if module_name not in MODULES_TO_SAVE:
    return {}
  if not module_name or module_name in visited:
    return {}
  visited.add(module_name)
  variables = {}
  try:
    variables.update({k: v for k, v in vars(module).items() if include_in_state(k, v)})
    for submodule_name in getattr(module, '__all__', []):
      submodule = getattr(module, submodule_name, None)
      if submodule:
        variables[submodule_name] = get_module_variables(submodule, visited)
  except Exception as e:
    variables['__error__'] = str(e)
  return variables


def global_exception_handler(exc_type, exc_value, exc_traceback):
  """Handle uncaught exceptions."""
  print("Uncaught exception occurred!")
  traceback.print_exception(exc_type, exc_value, exc_traceback)
  
  # Save the exception details
  state = {
      "globals": {k: v for k, v in globals().items() if include_in_state(k, v)},
      "modules": {},  # To store variables from other modules
      "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
  }
  
  for module_name in MODULES_TO_SAVE:
    try:
      module = sys.modules[module_name]
      if module:
        state["modules"][module_name] = get_module_variables(module)
    except Exception as e:
      print(f"Could not save state of module {module_name}: {e}")
  ### END FOR ###

  print(state)
  with open("program_state.dill", "wb") as file:
    dill.dump(state, file)
  print("State saved with exception details to 'program_state.dill'")
  
  # Exit the program
  sys.exit(1)
  
TODO: set sys.excepthook in the main module
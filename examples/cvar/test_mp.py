hlvl = None
line = "## test"
if (_cvar(line.startswith('# '), hlvl, 1) or 
    _cvar(line.startswith('## '), hlvl, 2)):
  print(hlvl)
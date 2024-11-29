from metap import MetaP

mp = MetaP(filename="test_mp.py")
mp.log_func_defs(indent=True)
mp.compile()
mp.dump(filename="test.py")
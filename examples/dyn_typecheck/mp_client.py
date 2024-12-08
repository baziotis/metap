from metap import MetaP

mp = MetaP(filename="test_mp.py")
mp.dyn_typecheck()
mp.compile()
mp.dump(filename="test.py")
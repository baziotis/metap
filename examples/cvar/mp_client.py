from metap import MetaP

mp = MetaP(filename="test_mp.py")
mp.compile()
mp.dump(filename="test.py")
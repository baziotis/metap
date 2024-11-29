from metap import MetaP

mp = MetaP(filename="test_mp.py")
mp.add_asserts()
mp.compile()
mp.dump(filename="test.py")
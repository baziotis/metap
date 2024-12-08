import metap

mp = metap.MetaP(filename='test_mp.py')
mp.compile(macro_defs_path='macro_defs.py')
mp.dump('test.py')
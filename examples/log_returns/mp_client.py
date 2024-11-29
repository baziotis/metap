from metap import MetaP

mp = MetaP(filename="src.py")
mp.log_returns(include_fname=True)
mp.dump()
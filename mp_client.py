from metap import MetaP

mp = MetaP(filename="another.py")
mp.log_returns(include_fname=True)
mp.log_breaks()
mp.log_continues()
mp.dump()
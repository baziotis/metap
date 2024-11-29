from metap import MetaP

mp = MetaP(filename="test_mp.py")
mp.log_calls_start_end(patt="find_primes")
mp.compile()
mp.dump(filename="test.py")
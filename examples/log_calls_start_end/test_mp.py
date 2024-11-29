import json

def is_prime(num):
  if num <= 1:
    return False
  if num <= 3:
    return True
  if num % 2 == 0 or num % 3 == 0:
    return False

  i = 5
  while i * i <= num:
    if num % i == 0 or num % (i + 2) == 0:
      return False
    i += 6

  return True

def find_primes(limit):
    primes = []
    for num in range(2, limit + 1):
      if is_prime(num):
        primes.append(num)
    return primes

with open('d.json', 'w') as fp:
  json.dump(find_primes(2_000_000), fp)
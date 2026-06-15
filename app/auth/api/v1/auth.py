# ❌ Change this if you see something turning the password into a long string:
from hashlib import sha256
long_hash = sha256(payload.password.encode()).hexdigest() # This makes it > 72 bytes
hashed_password = pwd_context.hash(long_hash)

#  To this (Pass the raw string directly):
hashed_password = pwd_context.hash(payload.password)

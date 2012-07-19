import string
import random
		
def randstring(n):
	chars = string.ascii_letters + string.digits
	randstr = "".join( random.sample(chars,n) )
	return randstr
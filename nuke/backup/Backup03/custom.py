import time
import string
import random
from subprocess import Popen

# Twitter limits API calls per hour, we check to make sure 
# we make at most one post per minute. We can optionally
# ignore this, forcing an update, by setting #tweet's *force*
# argument to True.

last_tweet_time = time.clock()

def tweet(message,force=False):
	"""
	Uses curl to broadcast a message to twitter asynchronously. DOES NOT
	check if broadcast is successful, returns control immedietly to parent process.	
	"""
	global last_tweet_time
	url = 'http://twitter.com/statuses/update.xml'
	cmd = 'curl -s -u restbeckett:nadine -d status="%s" %s' % (message,url)
	if time.clock()-last_tweet_time > 60 or force:
		Popen(cmd)
		print "Posted: %s" % message
		last_tweet_time = time.clock()
		
def randstring(n):
	chars = string.ascii_letters + string.digits
	randstr = "".join( random.sample(chars,n) )
	return randstr
def get(width, height):
	x,y = 0,0
	done = False
	while not done:
		if (x,y)==(width,height): done=True
		yield (x,y)
		if x >= width: y+=1
		x+=1
		x,y = x%(width+1),y%(height+1)

def getAverage(node, width, height, channel="r"):
	coor = get(width,height)
	t = []
	while True:
		try:
			(x,y) = coor.next()
			t.append(node.sample(channel, x, y))
		except StopIteration:
			break
	return sum(t)/len(t)*1.0

def eachPixel(node, width, height):
	coor = get(width,height)
	while True:
		try:
			(x,y) = coor.next()
			for c in "rgba":
				node.sample(c, x+.5, y+.5)
		except StopIteration:
			break

#getter = get(1280,720)
#while True:
#	try:
#		r = getter.next()
#		if r in [(0,720),(1280,720),(1280,0),(0,0)]: print r
#	except StopIteration:
#		break
import re

def get_cameras(filein):
	all_cams = [m[0] for m in [re.findall(r'-n "(.+)" -p "(.+)"',l) for l in filein if re.search("createNode camera",l)]]
	return [cam for cam in all_cams if cam[1] not in ['top','side','front','persp']]

def get_animation_data(string,filein):
	[start,end] = [0,0]
	for (i,line) in enumerate(filein):
		if re.search(string,line) and re.search("createNode",line):
			start+=i
			for (i,subline) in enumerate(filein[i+1:]):
				if re.search("ktv",subline):
					start+=i+1
				if re.search("createNode",subline): 
					end = start+i-2
					break
	if filein[start:end]:
		# Strip away all non-printing characters from block of animation data and concatenate into one string
		clean_lines = " ".join([l.strip() for l in filein[start:end]])
		# Grab text only after "ktv" declaration and strip trailing ";"
		anim_string = re.findall(r"ktv.+\" (.+)",clean_lines)[0].strip()[:-1]
		# Reconstruct array with only animation values discarding frame numbers and convert all into float
		anim_data = [float(i) for i in anim_string.split(" ")[1::2]]
		return anim_data
	else:
		return None
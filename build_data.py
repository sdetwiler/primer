#! /usr/bin/env python

import json

def main():
	
	ban = ["I", "we", "he", "she", "they", "mom", "dad", "are", "do", "see"]
	
	nouns = {}
	f = open("data/data.noun")
	lines = f.readlines()
	for l in lines:
		if l[0] == " ":
			continue
			
		tokens = l.split(" ")
		noun = tokens[4]
		if noun not in ban:
			nouns[noun] = None
		
	print json.dumps(nouns, indent=2)
	

if __name__ == "__main__":
	main()
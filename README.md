Primer
======================

An extremely rough sketch of a primer backed by Wikipedia.

If you haven't already, go read https://en.wikipedia.org/wiki/The_Diamond_Age

Development Setup for OS X
----------------------
    virtualenv env
    source env/bin/activate
    STATIC_DEPS=true pip install lxml
    pip install -r requirements.txt

Development Setup for Amazon Linux
----------------------
		virtualenv env
		source env/bin/activate
		sudo yum install libxml2-devel libxslt-devel python-devel
		pip install lxml
		pip install -r requirements.txt
	
 
		
Usage
----------------------

	usage: primer.py [-h] [--article ARTICLE] [--file] [--server] [--nojsoncache]
	                 [--nowikicache] [--norelatedmedia]

	optional arguments:
	  -h, --help         show this help message and exit
	  --article ARTICLE  The article to generate. (World_War_I)
	  --file             Write data to files
	  --server           Run interactive HTTP server
	  --nojsoncache      Skip the JSON cache
	  --nowikicache      Skip the Wiki markup cache
	  --norelatedmedia   Skip related media discovery
		
To run as an interactive server run:

	./primer.py --server
	
And open http://localhost:8000 in your browser
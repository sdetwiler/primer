Primer
======================

Although this is a long way away from the Primer as envisioned by Neal Stephenson, it's an extremely rough sketch of a primer backed by Wikipedia. If you haven't already, go read https://en.wikipedia.org/wiki/The_Diamond_Age


A live, running version is available at http//primer.piratestudios.com. This has been tested on Chrome, Safari and iOS.


Development Setup for OS X
----------------------
    virtualenv env
    source env/bin/activate
    STATIC_DEPS=true pip install lxml
    pip install -r requirements.txt

Development Setup for Amazon Linux
----------------------
		sudo yum install git emacs gcc gcc-c++ libxml2-devel libxslt-devel python-devel
		virtualenv env
		source env/bin/activate
		pip install lxml
		pip install -r requirements.txt
	
SSL Cert Generation for Local Testing
----------------------

	openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes
	
Ensure the "Common Name (e.g. server FQDN or YOUR name)" response is localhost 
		
Usage
----------------------

	usage: primer.py [-h] [--article ARTICLE] [--file] [--random] [--server]
                 [--https] [--port PORT] [--nojsoncache] [--nowikicache]
                 [--norelatedmedia] [--nothreaded]

	optional arguments:
	  -h, --help         show this help message and exit
	  --article ARTICLE  The article to generate. (World_War_I)
	  --file             Write data to files
	  --random           Get random image from Wikipedia.
	  --server           Run interactive HTTP server
	  --https            Serve using HTTPS
	  --port PORT        The port listened to by the server. Defaults to 8000.
	  --nojsoncache      Skip the JSON cache
	  --nowikicache      Skip the Wiki markup cache
	  --norelatedmedia   Skip related media discovery
	  --nothreaded       Disable multithreaded media lookup
  		
To run as an interactive server run:

	./primer.py --server
	
And open http://localhost:8000 in your browser
#!/usr/bin/env python
import os
import sys
import logging
import logging.config
import argparse
import json

import requests
import urlparse

import threading

import datetime
import time 

import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import ssl

from mwlib import wiki
from mwlib.parser.nodes import *
from mwlib.refine import core, compat
from mwlib.expander import expandstr
from mwlib.templ import *
from mwlib.templ.scanner import symbols, tokenize


logger = logging.getLogger("piratestudios.primer")

# Bam, right in the global scope...        
usejsoncache = True
usewikicache = True
userelatedmedia = True
threaded = False


random_image = None
random_image_updated = 0

class Client():
    def __init__(self):
        self.content = []
        self.related_media = {}
        self.wiki_version = "en"


    # Get the JSON representation of the article for the specified topic.
    def get_article(self, topic):
        global usejsoncache
        global threaded
        
        cacheDir = "./json_cache/{}".format(self.wiki_version)
        try:
            os.mkdir(cacheDir)
        except:
            pass
            
        filename = "{}/{}".format(cacheDir, topic)
        if usejsoncache is True and os.path.isfile(filename):
            print "cache hit for " + topic
            js = open(filename).read()
        else:
            markup = self.get_markup_for_topic(topic)

            templParser = mwlib.templ.parser.Parser(markup)
            templates = templParser.parse()
            print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$"
            markup = ""
            for t in templates:
                # print "==>{} {}<==".format(type(t), t)
                if isinstance(t, unicode):
                    markup+= t

                elif isinstance(t, mwlib.templ.nodes.Template):
                    print "==>{}<==".format(t[0])
                    if t[0] == "Wide image":
                        print "  -->{}<--".format(t[1][0])
                        markup+= " [[File:{}]] ".format(t[1][0])

            # print article
            print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$"

            markup = expandstr(markup)
            # print markup
            article = compat.parse_txt(markup)

            self.reset()
            if threaded:
                self.build_related_media(article)
            else:
                print "Not performing threaded processing"
            self.depth_first(article)
        
            obj = {"content":self.content, "title":topic, "url":"https://{}.wikipedia.org/wiki/{}".format(self.wiki_version, topic), "url":"https://{}.wikipedia.org/wiki/{}".format(self.wiki_version, topic)}
            js = json.dumps(obj, indent=2)
            
            open(filename, "w").write(js)
        return js

    # Returns the media in the article for the specified topic.
    def get_media_for_article(self, topic):
        media = []
        try:
            client = Client()
            markup = self.get_markup_for_topic(topic)
            article = compat.parse_txt(markup)
            self.depth_find_media(article, topic, media)
            #print "toplc: " + topic
            #print media
        except:
            pass

        return media

    # Convert a wiki link to a URL.
    def url_from_image_link(self, link):
        # print link
        if link.startswith("File:"):
            link = link[5:] # remove File:
        elif link.startswith("Image:"):
            link = link[6:] # remove Image:
        link = link.replace(" ", "_")
        import hashlib
        h = hashlib.md5()
        h.update(link)
        hashstring = h.hexdigest()
        # print hashstring
        
        return "https://upload.wikimedia.org/wikipedia/commons/{}/{}/{}".format(hashstring[0], hashstring[0:2], link)

    def contentType_for_file(self, file):
        if file.endswith("jpg") or file.endswith("jpeg"):
            return "image/jpeg"

        if file.endswith("png"):
            return "image/png"

        if file.endswith("gif"):
            return "image/gif"

        if file.endswith("svg"):
            return "image/svg+xml"

        if file.endswith("ogg"):
            return "audio/ogg"

        return None

    def related_media_thread(self, topic):
        media = self.get_media_for_article(topic)
        if len(media) > 0:
            if topic not in self.related_media:
                self.related_media[topic] = media 
            
    def build_related_media_internal(self, node, depth=0):
        if type(node) == ArticleLink:
            topic = node.target
            t = threading.Thread(target=self.related_media_thread, args=(topic,))
            self.related_media_threads.append(t)
            t.start()

        for c in node.children:
            self.build_related_media_internal(c, depth+1)
    
    def build_related_media(self, node):
        logging.debug("build_related_media started")
        self.related_media = {}
        self.related_media_threads = []
        self.build_related_media_internal(node)
        logging.debug("Waiting for {} threads to complete".format(len(self.related_media_threads)))
        for t in self.related_media_threads:
            t.join()
        self.related_media_threads = []
        logging.debug("build_related_media done")
        

    # Walk an article to discover its contained media.
    def depth_find_media(self, node, topic, media=[], depth=0):
        if type(node) == ImageLink:
            url = self.url_from_image_link(node.target)
            contentType = self.contentType_for_file(url)
            if contentType is not None:
                media.append({"url":url, "contentType":contentType, "caption":topic, "article":topic})

        # Constrain how many media items are found for each topic.
        if len(media) < 3:
            for c in node.children:
                self.depth_find_media(c, topic, media, depth+1)
            
    # Resets the accumulation data for the current block of text. This is done as depth_first transitions
    # between paragraphs.
    def reset(self):
        self.find_media = True
        self.block = {"text":"", "media":[]}
    
    # Walk an article to construct its JSON representation for playback.
    def depth_first(self, node, depth=0):
        global userelatedmedia
        global threaded
        
        # print "node: {} {}".format(type(node), node)
        # Magic node type signaling end of paragraph.
        if node.type == 21:
            # print "magic {}".format(node)
            self.block["text"] = self.block["text"].strip()
            # if there is text that isn't a template reference or if there is media, add the block
            # if (len(self.block["text"]) and self.block["text"][0] is not "{") or len(self.block["media"]):
            if (len(self.block["text"])) or len(self.block["media"]):
                self.content.append(self.block)
                # print "##start"
                # print self.block["text"]
                # print "end##"
                
            # Reset the current block
            self.reset()
            
        if type(node) == ArticleLink:
            # print "link: {} {} {}".format(type(node), node.target, node.children)
            # If there are no children, use the target as the text, otherwise rely on the children to add the text.
            if len(node.children) == 0:
                self.block["text"]+= node.target

            if self.find_media == True and userelatedmedia:
                if threaded:
                    if node.target in self.related_media:
                        media = self.related_media[node.target]
                    else:
                        media = []
                else:
                    media = self.get_media_for_article(node.target)
                    
                if len(media) > 0:
                    # self.block["media"].append(media[0])
                    self.block["media"].append(media)
                    self.find_media = False

        elif type(node) == ImageLink:
            # print "ImageLink: {}".format(node.target)
            
            url = self.url_from_image_link(node.target)
            
            caption = ""
            if len(node.children):
                caption = node.children[0].text
            self.block["media"].append({"url":url, "contentType":self.contentType_for_file(url), "caption":caption, "article":None})
            # Drop children of images to supress possible captions.
            node.children = []
            
        elif type(node) == Text:
            # print "{} {} {}".format("text", type(node), node.text)
            text = node.text
            
            # A sentence ended, so start looking for media again.
            if "." in text:
                self.find_media = True
            self.block["text"]+= "{}".format(text)

        # else:
        #     print "{} {}".format("unknown", type(node))

        for c in node.children:
            self.depth_first(c, depth+1)


    # Get the wiki markup for the specified topic.
    def get_markup_for_topic(self, topic):
        global usewikicache
        url = "https://{}.wikipedia.org/wiki/{}?action=raw".format(self.wiki_version, topic)

        cacheDir = "./markup_cache/{}".format(self.wiki_version)
        try:
            os.mkdir(cacheDir)
        except:
            pass
            
        filename = "{}/{}".format(cacheDir, topic)
        if usewikicache is True and os.path.isfile(filename):
            print "cache hit for " + topic
            markup = open(filename).read()
        else:
            response = requests.get(url, timeout=2.0)
            markup = response.text
            
            open(filename, "w").write(markup)
        return markup
    
    # Yes, this is sloppy.
    def get_random_image(self):
        global random_image_updated
        global random_image
        now = time.time()
        d = now - random_image_updated
        if d > 60: # Refresh every minute.
            i = 0
            media = []
            while len(media) == 0 and i<100:
                url = "https://{}.wikipedia.org/wiki/Special:Random?action=raw".format(self.wiki_version)
                response = requests.get(url, timeout=2.0)
                markup = response.text
                topic = urlparse.parse_qs(urlparse.urlparse(response.url).query)["title"]
                # print markup
                article = compat.parse_txt(markup)
                self.depth_find_media(article, topic, media)
                i+=1
        
            if len(media) > 0:
                random_image = media[0]
                random_image_updated = now

        return random_image
        
        


# Returns the JSON formatted article.
def get_article(topic):
    client = Client()
    article = client.get_article(topic)

    return article

# Returns a random image url from Wikipedia.
def get_random_image():
    client = Client()
    data = client.get_random_image()
    return json.dumps(data, indent=2)
    
    

class WikipediaHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        print self.path
        # Article Request.
        if self.path == '/' or self.path.startswith("/a/"):
            print "serving index.html"
            self.path = '/index.html'
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

        # Static asset request.
        elif self.path.startswith("/assets/"):
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        elif self.path == "/favicon.ico":
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

        # random background request.
        elif self.path.startswith("/r/"):
            data = get_random_image()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
            
        # Data request.
        elif self.path.startswith("/d/"):
            topic = self.path.split("/")[2]
            # print topic
            article = get_article(topic)
            # print article
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(article)


class ThreadingSimpleServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass


def listen(port):
    httpd = ThreadingSimpleServer(('', port), WikipediaHandler)
    logger.debug("listening on port {}".format(port))
    try:
        while True:
            sys.stdout.flush()
            httpd.handle_request()

    except KeyboardInterrupt:
        logger.debug("KeyboardInterrupt")
    

def main():  
    global usejsoncache
    global usewikicache
    global userelatedmedia
    global threaded

    start = datetime.datetime.now()
      
    # Force UTF8 encoding... this is sort of ugly.
    import sys
    reload(sys)
    sys.setdefaultencoding('UTF8')
    
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "verbose": {
                "format": "%(asctime)s:%(name)s:%(levelname)s:%(message)s",
                },
            },
        "handlers": {
            "stdout": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "stream": "ext://sys.stdout",
                },
            "stderr": {
                "level": "ERROR",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "stream": "ext://sys.stderr",
                },
            },
        "loggers": {
            "piratestudios": {
                "handlers": ["stdout", "stderr"],
                "level": "DEBUG",
                },
            },
        })

    parser = argparse.ArgumentParser()
    parser.add_argument("--article", default=None, help="The article to generate. (World_War_I)")
    parser.add_argument("--file", action="store_true", default=False, help="Write data to files")
    parser.add_argument("--random", action="store_true", default=False, help="Get random image from Wikipedia.")
    parser.add_argument("--server", default=False, action="store_true", help="Run interactive HTTP server")
    parser.add_argument("--https", default=False, action="store_true", help="Serve using HTTPS")
    parser.add_argument("--port", default=8000, help="The port listened to by the server. Defaults to 8000.")
    parser.add_argument("--nojsoncache", default=False, action="store_true", help="Skip the JSON cache")
    parser.add_argument("--nowikicache", default=False, action="store_true", help="Skip the Wiki markup cache")
    parser.add_argument("--norelatedmedia", default=False, action="store_true", help="Skip related media discovery")
    parser.add_argument("--nothreaded", default=False, action="store_true", help="Disable multithreaded media lookup")
    args = parser.parse_args()

    # Yuck
    usejsoncache = args.nojsoncache == False
    usewikicache = args.nowikicache == False
    userelatedmedia = args.norelatedmedia == False
    threaded = args.nothreaded == False

    if args.random is True:
        client = Client()
        article = client.get_random_image()
        

    if args.article is not None:    
        article = get_article(args.article)
        print article

        if args.file:
            open(args.article + ".json", "w").write(article)

    if args.server is True:
        PORT = int(args.port)

        httpd = ThreadingSimpleServer(('', PORT), WikipediaHandler)
        if args.https is True:
            logger.info("Enabling HTTPS support")
            httpd.socket = ssl.wrap_socket(httpd.socket, certfile="server.pem", server_side=True)
            
        logger.debug("serving at port {}".format(PORT))
        try:
            while True:
                sys.stdout.flush()
                httpd.handle_request()

        except KeyboardInterrupt:
            logger.debug("KeyboardInterrupt")

    end = datetime.datetime.now()
    logger.debug("done. Took {}".format(end-start))

if __name__ == "__main__":
    main()
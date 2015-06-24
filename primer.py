#!/usr/bin/env python
import os
import logging
import logging.config
import argparse
import random
import json

import requests

from bs4 import BeautifulSoup

import SimpleHTTPServer
import SocketServer

from mwlib import wiki
# import mwlib.parser.nodes
from mwlib.parser.nodes import *
from mwlib.refine import core, compat

import StringIO

logger = logging.getLogger("piratestudios.primer")


class Client():
    def __init__(self):
        self.content = []


    def get_article(self, topic):
        cacheDir = "./json_cache"
        try:
            os.mkdir(cacheDir)
        except:
            pass
            
        filename = "{}/{}".format(cacheDir, topic)
        if os.path.isfile(filename):
            print "cache hit for " + topic
            js = open(filename).read()
        else:
            markup = self.get_markup_for_topic(topic)
            article = compat.parse_txt(markup)
            self.reset()
            self.depth_first(article)
        
            obj = {"content":self.content, "title":topic, "url":"https://en.wikipedia.org/wiki/{}".format(topic), "url":"https://en.wikipedia.org/wiki/{}".format(topic)}
            js = json.dumps(obj, indent=2)
            
            open(filename, "w").write(js)
        return js

    def get_media_for_article(self, topic):
        media = []
        try:
            client = Client()
            markup = self.get_markup_for_topic(topic)
            article = compat.parse_txt(markup)
            self.depth_find_media(article, media)
            print "toplc: " + topic
            print media
        except:
            pass

        return media

    def url_from_image_link(self, link):
        print link
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


    def depth_find_media(self, node, media=[], depth=0):
        if type(node) == ImageLink:
            url = self.url_from_image_link(node.target)
            contentType = self.contentType_for_file(url)
            if contentType is not None:
                media.append({"url":url, "contentType":contentType})

        if len(media) < 3:
            for c in node.children:
                self.depth_find_media(c, media, depth+1)
            

    def reset(self):
        self.find_media = True
        self.block = {"text":"", "media":[]}
        
    def depth_first(self, node, depth=0):
        # Magic node type signaling end of paragraph.
        if node.type == 21:
            self.block["text"] = self.block["text"].strip()
            # if there is text that isn't a template reference or if there is media, add the block
            if (len(self.block["text"]) and self.block["text"][0] is not "{") or len(self.block["media"]):
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

            if self.find_media == True:
                media = self.get_media_for_article(node.target)
                if len(media) > 0:
                    self.block["media"].append(media[0])
                    self.find_media = False

        elif type(node) == ImageLink:
            # print "ImageLink: {}".format(node.target)
            
            url = self.url_from_image_link(node.target)
            
            self.block["media"].append({"url":url, "contentType":"image/jpeg"})
            # Drop children of images to supress possible captions.
            node.children = []
            
        elif type(node) == Text:# node.text and len(node.text) > 0:
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


    def get_markup_for_topic(self, topic):
        url = "https://en.wikipedia.org/w/index.php?title={}&action=edit".format(topic)

        cacheDir = "./markup_cache"
        try:
            os.mkdir(cacheDir)
        except:
            pass
            
        filename = "{}/{}".format(cacheDir, topic)
        if os.path.isfile(filename):
            print "cache hit for " + topic
            markup = open(filename).read()
        else:
            response = requests.get(url, timeout=2.0)
            markup = self.get_markup_from_html(response.text)
            
            open(filename, "w").write(markup)
        return markup
        
    def get_markup_from_html(self, html):
        soup = BeautifulSoup(html)
        textarea = soup.find("textarea")
        markup = textarea.contents[0]
        return markup

    def parse_markup_from_html(self, html):
        self.reset()

        markup = self.get_markup_from_html(html)

        article = compat.parse_txt(markup)
        self.depth_first(article)
            
        return {"content":self.content, "title":""}
     

    def parse_html(self, html):
        article = {}
        content = []
        
        soup = BeautifulSoup(html)
        
        title = soup.find("title")
        article["title"] = title.get_text()
        
        div = soup.find("div", id="mw-content-text")


        for c in div.contents:
            # print c.name
            if (c.name == "h3") or (c.name == "p" and len(content) == 0):
                block = { "media":[], "text":"" }
                paragraphs = []
                for sib in c.previous_siblings:
                    if sib.name == "p":
                        break;
                    elif sib.name == "div":
                        img = sib.find("img")
                        if img is not None:
                            media = {"url":img.get("src"), "contentType":"image/jpeg"}
                            block["media"].append(media)
                    
                for sib in c.next_siblings:
                    if sib.name == "p":
                        # print sib
                        block["text"]+= sib.get_text()
                    elif sib.name == "h1":
                        break
                    elif sib.name == "h2":
                        break
                    elif sib.name == "h3":
                        break
                    

                content.append(block)

        article["content"] = content
        return article

    def __str__(self):
        s = ""
        for d in self.dungeons:
            s += "{}\n".format(d)
        return s


def get_article(topic):
    client = Client()
    article = client.get_article(topic)

    return article
    

class WikipediaHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        print self.path
        if self.path == '/':
            self.path = '/index.html'
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        elif self.path.startswith("/assets/"):
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            
        else:
            topic = self.path[1:]
            # print topic
            article = get_article(topic)
            print article
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(article)
        

def main():    
    import sys
    reload(sys)  # Reload does the trick!
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
            "n3twork": {
                "handlers": ["stdout", "stderr"],
                "level": "DEBUG",
                },
            },
        })

    # Deterministic random sequences.
    random.seed(1)


    parser = argparse.ArgumentParser()
    parser.add_argument("--article", default=None, help="The article to generate. (World_War_I)")
    parser.add_argument("--file", action="store_true", default=False, help="Write data to files")
    parser.add_argument("--server", default=False, action="store_true", help="Run interactive HTTP server")
    args = parser.parse_args()

    if args.article is not None:    
        article = get_article(args.article)
        print article

        if args.file:
            open(args.article + ".json", "w").write(article)

    if args.server is True:
        PORT = 8000

        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler

        httpd = SocketServer.TCPServer(("", PORT), WikipediaHandler)

        print "serving at port", PORT
        httpd.serve_forever()


    logger.debug("done")

if __name__ == "__main__":
    main()
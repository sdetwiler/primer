#!/usr/bin/env python

import logging
import logging.config
import argparse
import random
import json

import requests

from bs4 import BeautifulSoup

import SimpleHTTPServer
import SocketServer

base_url = "https://www.wikipedia.org/wiki/"


logger = logging.getLogger("piratestudios.primer")


class Client():
    def __init__(self):
        pass
        
    def parse_url(self, url):
        response = requests.get(url)
        article = self.parse_html(response.text)
        article["url"] = url
        return article


    def parse_summary(self, html):
        # Find tables for sidebar images
        tables = div.findAll("table")
        for t in tables:
            images = t.findAll("img")
            for i in images:
                print i["src"]


    def parse_html(self, html):
        article = {}
        content = []
        
        soup = BeautifulSoup(html)
        
        title = soup.find("title")
        article["title"] = title.get_text()
        
        div = soup.find("div", id="mw-content-text")


        for c in div.contents:
            # print c.name
            if c.name == "h3" || (c.name == "p" && len(content) == 0):
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



class WikipediaHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        print self.path
        if self.path == '/':
            self.path = '/index.html'
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        else:
            topic = self.path[1:]
            print topic
            
            client = Client()
            url = "{}{}".format(base_url, topic)
            article = client.parse_url(url)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(article))
        

def main():
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
        client = Client()
        url = "{}{}".format(base_url, args.article)
        article = client.parse_url(url)
        print json.dumps(article, indent=2)

        if args.file:
            open(args.article + ".json", "w").write(txt)

    if args.server is True:
        PORT = 8000

        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler

        httpd = SocketServer.TCPServer(("", PORT), WikipediaHandler)

        print "serving at port", PORT
        httpd.serve_forever()


    logger.debug("done")

if __name__ == "__main__":
    main()
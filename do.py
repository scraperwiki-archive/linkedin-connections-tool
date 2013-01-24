#!/usr/bin/python
# Some parts of this file are: Copyright 2011 LinkedIn Corporation

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# OAuth docs:
# http://developer.linkedin.com/documents/authentication

import oauth2 as oauth
import httplib2
import time, os, simplejson
import urlparse
import BaseHTTPServer 
import sys
from xml.etree import ElementTree as ET
import scraperwiki

# Need to install:
# ElementTree for XML parsing: 
#		easy_install ElementTree
#		http://effbot.org/downloads#elementtree
# simplejson for JSON parsing: 
#		easy_install simplejson
#		https://github.com/simplejson/simplejson

import swconfig
 
request_token_url = 'https://api.linkedin.com/uas/oauth/requestToken'
access_token_url =  'https://api.linkedin.com/uas/oauth/accessToken'
authorize_url =     'https://api.linkedin.com/uas/oauth/authorize'

config_file   = '.service.dat'

http_status_print = BaseHTTPServer.BaseHTTPRequestHandler.responses
 

def get_auth():
	consumer = oauth.Consumer(swconfig.consumer_key, swconfig.consumer_secret)
	client = oauth.Client(consumer)

	try:
		filehandle = open(config_file)
		
	except IOError as e:
		filehandle = open(config_file,"w")
		print("We don't have a service.dat file, so we need to get access tokens!");
        # can put a "oauth_callback" URL in here http://developer.linkedin.com/documents/authentication
		content = make_request(client,request_token_url,{},"Failed to fetch request token","POST") 
		request_token = dict(urlparse.parse_qsl(content))
		print "Go to the following link in your browser:"
		print "%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'])
	 
		oauth_verifier = raw_input('What is the PIN? ')
	 
		token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
		token.set_verifier(oauth_verifier)
		client = oauth.Client(consumer, token)
	 
		content = make_request(client,access_token_url,{},"Failed to fetch access token","POST")
		
		access_token = dict(urlparse.parse_qsl(content))
	 
		token = oauth.Token(
			key=access_token['oauth_token'],
			secret=access_token['oauth_token_secret'])
	 
		client = oauth.Client(consumer, token)
		simplejson.dump(access_token,filehandle)
	
	else:
		config = simplejson.load(filehandle)
		if ("oauth_token" in config and "oauth_token_secret" in config):
			token = 	oauth.Token(config['oauth_token'],
	    				config['oauth_token_secret'])
			client = oauth.Client(consumer, token)
		else:
			print("There's a .service.dat file, but it doesn't contain a token and secret")
			sys.exit(1)
	return client

# Simple oauth request wrapper to handle responses and exceptions
def make_request(client,url,request_headers={},error_string="Failed Request",method="GET",body=None):
	if body:
		resp,content = client.request(url, method, headers=request_headers, body=body)
	else:
		resp,content = client.request(url, method, headers=request_headers)
	print resp.status
		
	if resp.status >= 200 and resp.status < 300:
		return content
	elif resp.status >= 500 and resp.status < 600:
		error_string = "Status:\n\tAn application error occured. HTTP 5XX response received."
		log_diagnostic_info(client,url,request_headers,method,body,resp,content,error_string)
		
	else:
		status_codes = {403: "\n** Status:\n\tA 403 response was received. Usually this means you have reached a throttle limit.",
						401: "\n** Status:\n\tA 401 response was received. Usually this means the OAuth signature was bad.",
						405: "\n** Status:\n\tA 405 response was received. Usually this means you used the wrong HTTP method (GET when you should POST, etc).",
						400: "\n** Status:\n\tA 400 response was received. Usually this means your request was formatted incorrectly or you added an unexpected parameter.",
						404: "\n** Status:\n\tA 404 response was received. The resource was not found."}
		if resp.status in status_codes:
			log_diagnostic_info(client,url,request_headers,method,body,resp,content,status_codes[resp.status])
		else:
			log_diagnostic_info(client,url,request_headers,method,body,resp,content,http_status_print[resp.status][1])
	
	
def log_diagnostic_info(client,url,request_headers,method,body,resp,content,error_string):
	# we build up a string, then log it, as multiple calls to () are not guaranteed to be contiguous
	log = "\n\n[********************LinkedIn API Diagnostics**************************]\n\n"
	log += "\n|-> Status: " + str(resp.status) + " <-|"
	log += "\n|-> " + simplejson.dumps(error_string) + " <-|"
	
	log += "\n|-> Key: " + swconfig.consumer_key + " <-|"
	log += "\n|-> URL: " + url + " <-|"
	log += "\n\n[*****Sent*****]\n";
	log += "\n|-> Headers:" + simplejson.dumps(request_headers) + " <-|"
	if (body):
		log += "\n|-> Body: " + body + " <-|"
	log += "\n|-> Method: " + method + " <-|"
	log += "\n\n[*****Received*****]\n"
	log += "\n|-> Response object: " + simplejson.dumps(resp) + " <-|"
	log += "\n|-> Content: " + content + " <-|";
	log += "\n\n[******************End LinkedIn API Diagnostics************************]\n\n"
	print log



if __name__ == "__main__":
    # Get authorization set up and create the OAuth client
    client = get_auth()

    ##############################
    # Getting Data from LinkedIn #
    ##############################

    print "\n********Get the connections********"
    #response = make_request(client,"http://api.linkedin.com/v1/people/~/connections?format=json")
    response = make_request(client,"http://api.linkedin.com/v1/people/~:(first-name,last-name,positions:(company:(name)))?format=json")
    connections = simplejson.loads(response)
    print connections
    sys.exit()
    print "total connections:", connections['_total']
    private = 0
    for connection in connections["values"]:
        print connection
        sys.exit()
        if connection['id'] == 'private':
            private += 1
            continue
        record = {
            'firstName': connection['firstName'],
            'lastName': connection['lastName'],
            'headline': connection['headline'],
            'industry': connection.get('industry', None),
            'linkedin_url': connection['siteStandardProfileRequest']['url'],
            'country': connection['location']['country']['code'],
            'location_name': connection['location']['name'],
            'id': connection['id']
        }
        print record
        scraperwiki.sqlite.save(['id'], record, table_name='linkedin_people')
    print "private connections (not sharing data with 3rd party apps):", private

    sys.exit()

    # Simple profile call
    print "\n********A basic user profile call********"
    response = make_request(client,"http://api.linkedin.com/v1/people/~")

    print response

    # Simple profile call, returned in JSON
    print "\n********Get the profile in JSON********"
    response = make_request(client,"http://api.linkedin.com/v1/people/~",{"x-li-format":'json'})
    print response

    # Simple profile call, returned in JSON, using query param instead of header
    print "\n********Get the profile in JSON********"
    response = make_request(client,"http://api.linkedin.com/v1/people/~?format=json")
    print response

    # Simple connections call
    print "\n********Get the connections********"
    response = make_request(client,"http://api.linkedin.com/v1/people/~/connections")
    print response

    # Simple connections call
    print "\n********Get only 10 connections - using parameters********"
    response = make_request(client,"http://api.linkedin.com/v1/people/~/connections?count=10")
    print response

    # Get network updates that are shares or connection updates
    print "\n********GET network updates that are CONN and SHAR********"
    response = make_request(client,"http://api.linkedin.com/v1/people/~/network/updates?type=SHAR&type=CONN")
    print response

    # People search using facets and encoding input parameters
    #print "\n********People Search using facets and Encoding input parameters i.e. UTF8********"
    #response = make_request(client,"http://api.linkedin.com/v1/people-search:(people:(first-name,last-name,headline),facets:(code,buckets))?title=D%C3%A9veloppeur&facet=industry,4&facets=location,industry")
    #print response

    ############################
    # Field Selectors          #
    ############################


    print "\n********A basic user profile call with field selectors********"
    api_url = "http://api.linkedin.com/v1/people/~:(first-name,last-name,positions)"
    response = make_request(client,api_url)
    print response


    print "\n********A basic user profile call with field selectors going into a subresource********"
    api_url = "http://api.linkedin.com/v1/people/~:(first-name,last-name,positions:(company:(name)))"
    response = make_request(client,api_url)
    print response


    print "\n********A basic user profile call into a subresource return data in JSON********"
    api_url = "https://api.linkedin.com/v1/people/~/connections:(first-name,last-name,headline)?format=json"
    response = make_request(client,api_url)
    print response


    print "\n********A more complicated example using postings into groups********"
    api_url = "http://api.linkedin.com/v1/groups/3297124/posts:(id,category,creator:(id,first-name,last-name),title,summary,creation-timestamp,site-group-post-url,comments,likes)"
    response = make_request(client,api_url)
    print response

    ####################################################################################
    # Understanding the response, creating logging and response headers                #
    ####################################################################################

    print "\n********A basic user profile call and response dissected********"
    api_url = "https://api.linkedin.com/v1/people/~";
    resp,content = client.request(api_url)

    print "\n** Response Headers:\n%s\n" % (resp) 

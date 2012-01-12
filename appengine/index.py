#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""Simple pages."""

# Python imports
import datetime
import os
import logging
import re

# AppEngine Imports
from google.appengine.ext import webapp
from google.appengine.api import memcache

# Our App imports
import models
from utils.render import render as r

twitter = ['@linuxconfau', '#linux.conf.au', '#lca2012']

channels = {
    'caro': 'lca2012-caro',
    'c001': 'lca2012-c001',
    'studio': 'lca2012-studio',
    't101': 'lca2012-t101',
    'studio1': 'lca2012-studio1',
    'studio2': 'lca2012-studio2',
    'studio2': 'lca2012-studio2',
    't102': 'lca2012-t102',
}

# IP Address which are considered "In Room"
LOCALIPS = [
]

class StaticTemplate(webapp.RequestHandler):
    """Renders the HTML templates."""

    def get(self, group):
        # FIXME(mithro): This shouldn't be duplicated.
        if not re.match('[a-z/]+', group):
            group = 'caro'
        if group not in channels:
            group = 'caro'
        channel = channels[group]

        template = self.request.get('template', '')
        if not re.match('[a-z]+', template):
            template = 'index'

            # Is the request coming from the room?
            for ipregex in LOCALIPS:
                if re.match(ipregex, self.request.remote_addr):
                    template = 'inroom'

        screenstr = self.request.get('screen', 'False')
        if screenstr.lower()[0] in ('y', 't'):
            screen = True
        else:
            screen = False

        hashtag = " OR ".join(twitter)

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(r('templates/%s.html' % template, locals()))


class StreamsTemplate(webapp.RequestHandler):
    """Renders the streams.js file."""

    def get(self, group):
        # FIXME(mithro): This shouldn't be duplicated.
        if not re.match('[a-z/]+', group):
            group = 'caro'
        if group not in channels:
            group = 'caro'
        channel = channels[group]

        # Get all the active streaming severs for this channel
        ten_mins_ago = datetime.datetime.now() - datetime.timedelta(minutes=10)
        q = models.Encoder.all()
        q.filter('group =', group)

        active_servers = []
        for server in q:
            print server, server.lastseen, ten_mins_ago
            if server.lastseen < ten_mins_ago:
                continue
            active_servers.append(server)

        if not active_servers:
            # FIXME: Technical difficulties server....
            server = BACKUP_SERVER
        else:
            # Choose the least loaded server
            server = sorted(active_servers, cmp=lambda a, b: cmp(a.bitrate, b.bitrate))[0].ip

        self.response.headers['Content-Type'] = 'text/javascript'
        # Make sure this page isn't cached, otherwise the server load balancing won't work.
        self.response.headers['Pragma'] = 'no-cache'
        self.response.headers['Cache-Control'] = 'no-cache'
        self.response.headers['Expires'] = '-1'

        self.response.out.write(r('templates/streams.js', locals()))


SECRET='tellnoone'

class RegisterHandler(webapp.RequestHandler):
    """Registers an encoding server into the application."""

    def post(self):
        self.response.headers['Content-Type'] = 'text/plain'

        secret = self.request.get('secret')
        if secret != SECRET:
            self.response.out.write('ERROR SECRET\n')
            return

        group = self.request.get('group')
        if group not in channels:
            self.response.out.write('ERROR GROUP\n')
            return

        ip = self.request.get('ip')
        clients = int(self.request.get('clients'))
        bitrate = int(self.request.get('bitrate'))

        s = models.Encoder(
                key_name='%s-%s' % (group, ip),
                group=group,
                ip=ip,
                clients=clients,
                bitrate=bitrate)
        s.put()
        self.response.out.write('OK\n')


class StatsHandler(webapp.RequestHandler):
    """Print out some stats about registered encoders."""

    def get(self):
        servers = sorted(models.Encoder.all(), cmp=lambda a, b: cmp((a.group, a.bitrate), (b.group, b.bitrate)))

        self.response.headers['Content-Type'] = 'text/plain'
        # Make sure this page isn't cached
        self.response.headers['Pragma'] = 'no-cache'
        self.response.headers['Cache-Control'] = 'no-cache'
        self.response.headers['Expires'] = '-1'

        for server in servers:
            self.response.out.write('ip:%s group:%s clients:%i bitrate:%i lastseen:%s\n' % (
                server.ip, server.group, server.clients, server.bitrate, server.lastseen))

# -*- coding: utf-8 -*-
"""
Created on Sun Jan 14 18:58:25 2018

@author: Andy
"""

import irc.client
from irc.client import SimpleIRCClient
import requests
import logging
import time
import sched
import functools
import math
import codecs
from pprint import pprint
# import os

#dev
from importlib import reload
def init():
  reload(t)
  globals()['tw'] = t.TwitchClient()
  globals()['tw'].connect()
  # globals()['tw'].join('#brownman')

CONNECT_TIMEOUT = 30
HOST = 'irc.chat.twitch.tv'
PORT = 6667
NICK = 'thestreetlampsalad'
AUTH = 'oauth:vda6o52iw9t75banzz3s13ppaj4u2s'
API_ID = 'qy2m8ydqa3e0dgnrxuvcxrvg711s5e'
API_SECRET = '71vepe1xaigqqr9le8ha0w71gtacev'
VIEWER_UPDATE_INTERVAL = 90
ATTEMPT_RECONNECT_INTERVAL = 9000
TIME_BETWEEN_CONNECTS = 3
DATA_LOCATION = 'data'

CHANNEL_LIST = [
  'savjz',
  'richard_hammer',
  'geekandsundry'
]

# logging.basicConfig(format='%(funcName)s:%(lineno)i:%(message)s', level=logging.DEBUG)
log = logging.getLogger('twitch_chat')
# formatter = logging.Formatter('%(funcName)s:%(lineno)i:%(message)s')
# ch = logging.StreamHandler()
# ch.setFormatter(formatter)
# log.addHandler(ch)

class TwitchClient(SimpleIRCClient):
  def __init__(self):
    self._exponential_backoff = 0
    self.channels = {}
    self.scheduler = sched.scheduler(time.time, time.sleep)
    SimpleIRCClient.__init__(self)
    

  def connect(self):
    if(self._exponential_backoff > CONNECT_TIMEOUT):
      log.warn("Exceeded maximum retries, cancel connect")
      self._exponential_backoff = 0
      return False
    if(self._exponential_backoff > 0):
      log.info("Backing off for {}".format(self._exponential_backoff))
      time.sleep(self._exponential_backoff)
      self._exponential_backoff *= 2
    else:
      self._exponential_backoff = 1
    
    log.info("Attempting to connect IRC server.")
    SimpleIRCClient.connect(self, HOST, PORT, nickname=NICK, password=AUTH)
  

  def _hash_channel(self, channel):
    return channel if(channel.startswith('#')) else '#' + channel
  

  def _unhash_channel(self, channel):
    return channel[1:] if(channel.startswith('#')) else channel
  

  def join(self, channel):
    channel = self._hash_channel(channel)
    self.connection.join(channel)


  def on_join(self, c, e):
    log.debug('Enter')
    channel = self._unhash_channel(e.target)
    if(channel not in self.channels):
      self.channels[channel] = {
        'name': channel,
        'connected': True
      }
      self.update_channel_details(channel)
    

  def update_channel_details(self, channel, join=False):
    '''
    Get the viewer count of a channel from TwitchAPI
    Pass in join=True to attempt to join when channel is online
    '''
    log.debug('Enter')

    headers = {
      'Accept': 'application/vnd.twitchtv.v5+json',
      'Client-ID': API_ID
    }
    url = 'https://api.twitch.tv/kraken/streams/'
    url += self._get_channel_id(channel)
    req = requests.get(url, headers=headers)
    res = req.json()
    log.debug(res)
    if('stream' in res and res['stream']):
      if(channel not in self.channels):
        self.channels[channel] = {
          'name': channel,
          'connected': True
        }
      self.channels[channel]['scheduled'] = False

      viewers = res['stream']['viewers']
      game = res['stream']['channel']['game']
      log.info('Viewers for channel {0}: {1}'.format(channel, viewers))
      # save viewer and game info to local channels obj
      self.channels[channel]['viewers'] = viewers
      self.channels[channel]['game'] = game
      # save viewer and game info to csv
      self.write_to_csv(channel + '_status', [str(viewers), game])
      # schedule update viewer count for later
      refresh = functools.partial(self.update_channel_details, channel)
      self.scheduler.enter(VIEWER_UPDATE_INTERVAL, 1, refresh)
      # reconnect
      if(join == True):
        self.join(channel)
    else:
      if(channel not in self.channels):
        self.chanenls[channel] = {
          'name': channel,
        }
      log.warn('Unable to get number of viewers')
      self.channels[channel]['connected'] = False
      self.channels[channel]['scheduled'] = True
      reconnect = functools.partial(self.update_channel_details, channel, join=True)
      self.scheduler.enter(ATTEMPT_RECONNECT_INTERVAL, 1, reconnect)

    # pretty print channel status
    with open('bot_status', 'w') as f:
      pprint(self.channels, stream=f)
      f.write('\n\nScheduler:')
      pprint(self.scheduler.queue, stream=f)

     
  def _get_channel_id(self, channel):
    '''
    Get the numeric channel id of a channel and save to self.channels object
    '''
    log.debug('Enter')

    channel = self._unhash_channel(channel)
    if(channel in self.channels):
      if('id' in self.channels[channel]):
        return self.channels[channel]['id']

    headers = {
      'Accept': 'application/vnd.twitchtv.v5+json',
      'Client-ID': API_ID
    }
    req = requests.get('https://api.twitch.tv/kraken/users', headers=headers,
      params={ 'login': channel })
    # log.debug(req.json())
    channel_id = req.json()['users'][0]['_id']

    if(channel not in self.channels):
      return channel_id
    else:
      self.channels[channel]['id'] = channel_id
      return channel_id


  def write_to_csv(self, file, line):
    '''
    Write the given line as a csv to file, appending current timestamp
    @params
      file - filename
        Message Files: ${channel}_messages
        Channel Logs: ${channel}_status
      line - array of values to push as csv
    '''
    path = DATA_LOCATION + '\\' + file
    timestamp = math.floor(time.time())
    line = str(timestamp) + '~|^' + '~|^'.join(line) + '\n'
    with codecs.open(path, 'a', 'utf-8') as f:
      f.write(line)


  def join_channel_in_list(self):
    '''
    Gradually attempt to connected to every channel in the channel list
    '''
    channel_joined = False
    for channel in CHANNEL_LIST:
      if(channel_joined):
        break
      if(channel not in self.channels):
        self.join(channel)
        channel_joined = True
      elif(self.channels[channel]['connected'] == False and
           self.channels[channel]['scheduled'] == False):
        self.join(channel)
        channel_joined = True

    # no more channels to attempt
    if(channel_joined):
      self.scheduler.enter(TIME_BETWEEN_CONNECTS, 1, self.join_channel_in_list)


  def loop(self):
    '''
    Loop to handle queued events
    '''
    while(True):
      # check connected
      if(not self.connection.is_connected()):
        self.connect()
      # check for scheduled items
      if(not self.scheduler.empty()):
        self.scheduler.run(False)
      # process reactor
      self.reactor.process_once()


  def start(self):
    self.join_channel_in_list()
    self.loop()


  def on_pubmsg(self, c, e):
    msg = e.arguments[0]
    channel = self._unhash_channel(e.target)
    self.write_to_csv(channel + '_messages', [msg])
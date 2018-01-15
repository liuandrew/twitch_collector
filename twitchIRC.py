# -*- coding: utf-8 -*-
"""
Created on Thu Dec 28 22:24:08 2017

@author: Andy
"""

import socket
import sys
import datetime
import codecs

class TwitchIrc:
  irc = socket.socket()
  server = 'irc.chat.twitch.tv'
  botnick = 'thestreetlampsalad'
  auth = 'oauth:vda6o52iw9t75banzz3s13ppaj4u2s'
  pong = ':tmi.twitch.tv'
  
  def __init__(self):
    self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
  def connect(self):
    self.irc.connect((self.server, 6667))
    self.irc.send(bytes('PASS ' + self.auth + '\n', 'utf-8'))
    self.irc.send(bytes('NICK ' + self.botnick + '\n', 'utf-8'))
    
  def get_text(self):
    try:
      text = self.irc.recv(2048).decode('utf-8')
      # keep alive with ping/pong
      if(text.find('PING') != -1):
        self.irc.send(bytes('PONG ' + self.pong + '\n', 'utf-8'))
        print('!!PONGING!!')
      return text
    except:
      print('error')

  def write_lines(self):
    text = self.get_text()
    lines = text.split('\r\n')[:-1]
    channels = {}
    for line in lines:
      print(line)
      channel = line.split('PRIVMSG ')
      if(len(channel) < 2):
        continue
      channel = channel[1].split(' :')[0].split('#')
      if(len(channel) < 2):
        continue
      channel = channel[1]
      if(channel not in channels):
        channels[channel] = []
      # 
      time = datetime.datetime.now().timestamp()
      msg = line.split('#' + channel + ' :')[1]
      channels[channel].append(str(time) + '((msg)):' + msg + '\n')
    for channel in channels:
      with codecs.open(channel, 'a', 'utf-8') as file:
        for line in channels[channel]:
          file.write(line)

  def join(self, channel):
    self.irc.send(bytes('JOIN ' + channel + '\n', 'utf-8'))

  def get_sock(self):
    return self.irc
  
  def send(self, msg):
    self.irc.send(bytes(msg + '\n', 'utf-8'))

#%%
tw = TwitchIrc()
tw.connect()
tw.join('#disguisedtoasths')
tw.join('#trumpsc')
print(tw.get_text())

#%%
print(tw.get_text())

#%%
tw.write_lines()
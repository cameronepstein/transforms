#!/usr/bin/env python

from MaltegoTransform import *
import sys
import os
import requests

website = sys.argv[1]
robots = []

m = MaltegoTransform()

try:
r = requests.get('http://' + website + '/robots.txt')
if r.status_code == 200:
robots = str(r.text).split('\n')
for i in robots:
m.addEntity('maltego.Phrase', i)
else:
m.addUIMessage("No Robots.txt found..")
except Exception as e:
m.addUIMessage(str(e))

m.returnOutput()

#!/usr/bin/python

import fileinput
import httplib
import json
import sys
import time

# if successive photos have timestamps fewer than timeBuffer seconds apart,
# this script treats them as having been taken at the same place. AP readings
# will be combined as long as timestamps stay sufficiently close together,
# and a single location lookup will be done at the end and applied to all
# photos.

timeBuffer = 300

# hitting the API too hard is a bad idea. Have a reasonable delay

delay = 5

lastPhotoTime = 10000

# APs seen by current chain of consecutive photos
currentAPs = {}
currentPhotos = []
# APs with unknown timestamp seen since last photo
limboAPs = {}
# APs seen since last powercycle
newAPs = {}

lookups = []

for line in fileinput.input():
  fields = line.rstrip().split(',')
  if len(fields) < 3:
    sys.stderr.writelines('bad line %s\n' % line)
    continue
  try:
    localTime, absoluteTime = map(int, fields[0:2])
  except ValueError:
    sys.stderr.writelines('bad timestamps %s\n' % line)
    continue
  command = fields[2]
  # the card only learns absoluteTime when the camera writes a file to it
  # (from the file timestamp). Between poweron and the first file written,
  # absoluteTime == localTime == seconds since poweron
  if command == 'AP' or command == 'NEWAP':
    mac, power = fields[3:5]
    if absoluteTime > lastPhotoTime and absoluteTime < lastPhotoTime + timeBuffer:
      currentAPs[mac] = power
    else:
      newAPs[mac] = power
  if command == 'POWERON':
    # after a powercycle, we won't know the absolute time until a photo is
    # written. If there are multiple powercycles before the next photo is
    # taken, one of two things must be true:
    #   (1) the next photo is within timeBuffer of the last photo, hence all
    #     APs detected during the intervening powercycles are also within
    #     timeBuffer.
    #   (2) the next photo is outside timeBuffer, in which case there is no
    #     way to determine when the intervening powercycles occurred, so
    #     all APs detected must be discarded.
    # Put them in limbo for now.
    limboAPs.update(newAPs)
    newAPs = {}
  if command == 'NEWPHOTO':
    filename, size = fields[3:5]
    if absoluteTime >= lastPhotoTime and absoluteTime < lastPhotoTime + timeBuffer:
      # still in a sequence of photos, all new and limbo APs are valid
      currentAPs.update(limboAPs)
      currentAPs.update(newAPs)
      currentPhotos.append([filename, size, str(absoluteTime)])
    else:
      # too much time has elapsed, so first wrap up the previous sequence:
      lookups.append([currentPhotos, currentAPs])
      # then start a new one
      currentPhotos = [[filename, size, str(absoluteTime)]]
      currentAPs = newAPs
      if absoluteTime < lastPhotoTime:
        # interesting if it happens
        sys.stderr.writelines('time rolled back on %s\n' % filename)
    # either way, reset state:
    lastPhotoTime = absoluteTime
    limboAPs = {}
    newAPs = {}

lookups.append([currentPhotos, currentAPs])

# now we look stuff up

maps = httplib.HTTPConnection("www.google.com")
accessToken = None

for photos, aps in lookups:
  if len(aps) == 0:
    continue
  request = {
    'version': '1.1.0',
    'host': 'dichro.nyc.corp.google.com',
    'request_address': True,
    'address_language': 'en_US',
    'wifi_towers': [],
  }
  sys.stderr.writelines('photos %s\n' % ', '.join([':'.join(x[0:3:2]) for x in photos]))
  for ap, power in aps.iteritems():
    sys.stderr.writelines('  %s (%s)\n' % (ap, power))
    request['wifi_towers'].append({
      'mac_address': '-'.join([ap[0:2], ap[2:4], ap[4:6], ap[6:8], ap[8:10], ap[10:12]]),
      'signal_strength': power,
      'age': int((time.time() - int(photos[-1][2])) * 1000),  # why not?
    })
  if accessToken:
    request['access_token'] = accessToken
  jsonRequest = json.dumps(request)
  print 'REQ', jsonRequest
  maps.request('POST', '/loc/json', jsonRequest)
  response = maps.getresponse()
  print 'HTTP', response.status, response.reason
  while response.status != 200:
    print 'sleeping'
    time.sleep(60)
    del request['access_token']
    jsonRequest = json.dumps(request)
    print 'REQ', jsonRequest
    maps.request('POST', '/loc/json', jsonRequest)
    response = maps.getresponse()
    print 'HTTP', response.status, response.reason
  jsonReply = response.read()
  print 'REP', jsonReply
  reply = json.loads(jsonReply)
  if reply: 
    if 'location' in reply:
      for photo in photos:
        photo.extend([reply['location']['latitude'], reply['location']['longitude'], reply['location']['accuracy']])
        print 'PHOTO', ','.join(map(str, photo))
    if 'access_token' in reply:
      accessToken = reply['access_token']

time.sleep(delay)
  

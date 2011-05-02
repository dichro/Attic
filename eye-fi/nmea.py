#!/usr/bin/python

import fileinput
import math
import os
import time

def convertDegrees(str, pos, neg):
  '''Converts locate.py's decimal degrees to NMEA's dddmm.mmm format'''
  sign = pos
  d = float(str)
  if d < 0:
    sign = neg
    d = -d
  frac, deg = math.modf(d)
  return '%f,%s' % (deg * 100 + frac * 60, sign)

for l in fileinput.input():
  type, line = l.rstrip().split(None, 1)
  if type != 'PHOTO':
    continue
  filename, size_s, timestamp, latitude_s, longitude_s, altitude = line.split(',')
  tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst = time.localtime(int(timestamp))

  # only good enough for perl's exiftools to parse it
  print '$GPRMC,%02d%02d%02d,A,%s,%s,,,%02d%02d%d,' % (
    tm_hour, tm_min, tm_sec,
    convertDegrees(latitude_s, 'N', 'S'),
    convertDegrees(longitude_s, 'E', 'W'),
    tm_mday, tm_mon, tm_year)

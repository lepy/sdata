import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))


import time
import datetime
import sdata.timestamp

def to_timestamp(dt, epoch=datetime.datetime(1970,1,1)):
    """2012-01-08 15:34:10.022403 -> 1326036850.02
    now = datetime.utcnow()
    print now
    print totimestamp(now)"""
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 86400.) * 10 ** 6) / 10 ** 6


def local_tzname():
    #
    if time.daylight:
        offsetHour = time.altzone / 3600
    else:
        offsetHour = time.timezone / 3600
    return 'Etc/GMT%+d' % offsetHour


def test_timestamp():
    timestr = "2017-04-26T09:04:00.660000+00:00"
    utctime = sdata.timestamp.parse_date(timestr)
    print(utctime.astimezone(tz=datetime.timezone.utc).isoformat())
    print(timestr)
    assert timestr == utctime.astimezone(tz=datetime.timezone.utc).isoformat()

    utctime2 = sdata.timestamp.get_utc_timestamp(utctime)
    print(utctime2.isoformat())

    localtime = sdata.timestamp.get_local_timestamp(utctime)
    print(localtime.isoformat())

    localtimestr = '2017-04-26 11:04:00.660000+02:00'
    localtime2 = sdata.timestamp.parse_date(localtimestr)
    print(localtime2.isoformat())
    utctime3 = sdata.timestamp.get_utc_timestamp(localtime2)
    print(utctime3.isoformat())
    assert timestr == sdata.timestamp.get_utc_timestamp(localtime2).isoformat()

    timestr = "2017-04-26T09:04:00+00:00"
    utctime = sdata.timestamp.parse_date(timestr)
    print(utctime.isoformat())

    timestr = "2017-04-26"
    utctime = sdata.timestamp.parse_date(timestr)
    print(utctime.isoformat())
    print(sdata.timestamp.get_local_timestamp(utctime).isoformat())


if __name__ == '__main__':
    test_timestamp()

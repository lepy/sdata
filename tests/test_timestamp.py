import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))


import time
import datetime
import pytz
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


def datetime2timestamp():
    ts = 1493197440.66  # time.time()
    utctime = datetime.datetime.utcfromtimestamp(ts)
    utctime = utctime.replace(tzinfo=pytz.utc)

    # utctime = datetime.datetime.now(tz=pytz.UTC)
    print("UTC:", utctime.astimezone(tz=pytz.UTC).isoformat())
    print("CEST", utctime.astimezone(tz=pytz.timezone('Europe/Berlin')).isoformat())
    print("CET ", utctime.astimezone(tz=pytz.timezone('CET')).isoformat())

    assert utctime.astimezone(tz=pytz.UTC).isoformat() == '2017-04-26T09:04:00.660000+00:00'
    assert utctime.astimezone(tz=pytz.timezone('Europe/Berlin')).isoformat() == '2017-04-26T11:04:00.660000+02:00'

    print(utctime.strftime('%Y-%m-%d %H:%M:%S.%f %Z'))
    print(utctime.strftime('%Y-%m-%d %H:%M:%S.%f %z'))
    print(utctime.isoformat())

    tz = pytz.timezone('Europe/Berlin')
    localtime = datetime.datetime.now(tz=tz)
    print(localtime.strftime('%Y-%m-%d %H:%M:%S.%f %Z'))
    print(localtime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
    print(localtime.astimezone(tz=pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f%z'))

    # tzname = local_tzname()
    # print tzname
    tzname = "Etc/GMT-2"
    localtime = utctime.astimezone(tz=pytz.timezone(tzname))
    print("!", localtime.astimezone(tz=pytz.timezone(tzname)).isoformat())
    # print localtime.astimezone(tz=pytz.timezone(tzname)).strftime('%Y-%m-%d %H:%M:%S.%f%z')
    # print localtime.astimezone(tz=pytz.timezone(tzname)).strftime('%Y-%m-%d %H:%M:%S.%f(%Z)')
    assert localtime.astimezone(tz=pytz.timezone(tzname)).isoformat() == "2017-04-26T11:04:00.660000+02:00"
    print("UTC:", localtime.astimezone(tz=pytz.UTC).isoformat())
    assert localtime.astimezone(tz=pytz.timezone("UTC")).isoformat() == "2017-04-26T09:04:00.660000+00:00"

    timestr = "2017-04-26T09:04:00.660000+00:00"
    time2 = sdata.timestamp.parse_date(timestr)
    print(time2.astimezone(tz=pytz.timezone("UTC")).isoformat())
    print(timestr)
    assert timestr == time2.astimezone(tz=pytz.timezone("UTC")).isoformat()


def test_timestamp():
    timestr = "2017-04-26T09:04:00.660000+00:00"
    utctime = sdata.timestamp.parse_date(timestr)
    print(utctime.astimezone(tz=pytz.timezone("UTC")).isoformat())
    print(timestr)
    assert timestr == utctime.astimezone(tz=pytz.timezone("UTC")).isoformat()

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
    # datetime2timestamp()

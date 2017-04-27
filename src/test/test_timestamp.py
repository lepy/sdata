import time
import datetime
import os
import pytz
import iso8601


def to_timestamp(dt, epoch=datetime.datetime(1970,1,1)):
    """2012-01-08 15:34:10.022403 -> 1326036850.02
    now = datetime.utcnow()
    print now
    print totimestamp(now)"""
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 86400.) * 10**6) / 10**6


def local_tzname():
    #
    if time.daylight:
        offsetHour = time.altzone / 3600
    else:
        offsetHour = time.timezone / 3600
    return 'Etc/GMT%+d' % offsetHour

def datetime2timestamp():
    ts = 1493197440.66 # time.time()
    utctime = datetime.datetime.utcfromtimestamp(ts)
    utctime = utctime.replace(tzinfo=pytz.utc)

    # utctime = datetime.datetime.now(tz=pytz.UTC)
    print("UTC:", utctime.astimezone(tz=pytz.UTC).isoformat())
    print("CEST", utctime.astimezone(tz=pytz.timezone('Europe/Berlin')).isoformat())
    print("CET ", utctime.astimezone(tz=pytz.timezone('CET')).isoformat())

    assert utctime.astimezone(tz=pytz.UTC).isoformat()=='2017-04-26T09:04:00.660000+00:00'
    assert utctime.astimezone(tz=pytz.timezone('Europe/Berlin')).isoformat()=='2017-04-26T11:04:00.660000+02:00'

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
    assert localtime.astimezone(tz=pytz.timezone(tzname)).isoformat()=="2017-04-26T11:04:00.660000+02:00"
    print("UTC:", localtime.astimezone(tz=pytz.UTC).isoformat())
    assert localtime.astimezone(tz=pytz.timezone("UTC")).isoformat()=="2017-04-26T09:04:00.660000+00:00"

    timestr = "2017-04-26T09:04:00.660000+00:00"
    time2 = iso8601.parse_date(timestr)
    print(time2.astimezone(tz=pytz.timezone("UTC")).isoformat())
    print(timestr)
    assert timestr==time2.astimezone(tz=pytz.timezone("UTC")).isoformat()




def test_timestamp():
    #http://stackoverflow.com/questions/8777753/converting-datetime-date-to-utc-timestamp-in-python
    ts = time.time()
    # print os.environ.get('TZ')
    print(time.timezone)
    ts = 1493197440.66
    print(ts, ts.strftime('%X %x %Z'))


    utc_offset = datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)

    print(utc_offset)

    print(dir(datetime.tzinfo()))
    # print (datetime.tzinfo().tzname(utc_offset))


    tt  = datetime.datetime.fromtimestamp(ts)
    ut = to_timestamp(tt)
    print("UTC", ut, datetime.datetime.utcfromtimestamp(ut).strftime('%Y-%m-%d %H:%M:%S.%f+%z'))
    print(tt.__str__())
    print(tt.utcoffset())
    print("utctimetuple", tt.utctimetuple())


    st = tt.strftime('%Y-%m-%d %H:%M:%s')

    print("strformat:{}".format(tt.strftime('%Y-%m-%d %H:%M:%S')))
    print("isoformat:{}".format(tt.isoformat()))

    assert tt.isoformat() == "2017-04-26T11:04:00.660000"
    print(tt.strftime('%Y-%m-%d %H:%M:%S'))
    assert tt.strftime('%Y-%m-%d %H:%M:%S') == "2017-04-26 11:04:00"
    print(tt.strftime('%Y-%m-%d %H:%M:%S.%f'))
    assert tt.strftime('%Y-%m-%d %H:%M:%S.%f') == "2017-04-26 11:04:00.660000"
    print(tt.strftime('%Y-%m-%d %H:%M:%S.%f+%Z'))
    assert tt.strftime('%Y-%m-%d %H:%M:%S.%f+%z') == "2017-04-26 11:04:00.660000"


if __name__ == '__main__':
    # test_timestamp()
    datetime2timestamp()

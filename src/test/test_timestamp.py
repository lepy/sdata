import time
import datetime

def test_timestamp():
    ts = time.time()
    ts = 1493197440.66
    print(ts)

    tt  = datetime.datetime.fromtimestamp(ts)
    print(tt.__str__())

    st = tt.strftime('%Y-%m-%d %H:%M:%s')

    print("strformat:{}".format(tt.strftime('%Y-%m-%d %H:%M:%S')))
    print("isoformat:{}".format(tt.isoformat()))

    assert tt.isoformat() == "2017-04-26T11:04:00.660000"
    print(tt.strftime('%Y-%m-%d %H:%M:%S'))
    assert tt.strftime('%Y-%m-%d %H:%M:%S') == "2017-04-26 11:04:00"
    print(tt.strftime('%Y-%m-%d %H:%M:%S.%f'))
    assert tt.strftime('%Y-%m-%d %H:%M:%S.%f') == "2017-04-26 11:04:00.660000"
    # print(tt.strftime('%Y-%m-%d %H:%M:%S.%f+%Z'))
    # assert tt.strftime('%Y-%m-%d %H:%M:%S.%f+%z') == "2017-04-26 11:04:00.660000"

if __name__ == '__main__':
    test_timestamp()
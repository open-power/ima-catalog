from struct import *
import csv
from common import *

NAMELEN_OFFSET = 0x14

def read_event(event_dump):
    event = {}
    elen, event['domain'], event['record byte offset'], event['record length'], \
        event['counter offset'], event['flag'], event['primary group index'], \
        event['group count'] = unpack_from(">HxxBxHHHIHH", event_dump)

    event['name'], nlen = read_string(event_dump[NAMELEN_OFFSET:])
    event['description'], dlen = read_string(event_dump[(NAMELEN_OFFSET + nlen):])
    event['detailed description'], ddlen = read_string(event_dump[(NAMELEN_OFFSET + nlen + dlen):])

    return elen, event

def read_events():
    f = open('81e00610.v7.lid', 'r')
    f.seek(0x2000, 0)
    event_length = 0x31
    dump = f.read(PAGE_SIZE * event_length)

    i = 0
    event_count = 0x532
    offset = 0
    f = open('events.csv', 'wt')
    try:
        writer = csv.writer(f)

        for i in range(0, event_count):
            elen, event = read_event(dump[offset:])
            offset += elen
            if i == 0:
                writer.writerow((event.keys()))
            writer.writerow((event.values()))
    finally:
        f.close()

read_events()

from struct import *
import csv
from common import *

NAMELEN_OFFSET = 0x30

def read_group(group_dump):
    group = {}
    glen, group['flag'], group['domain'], group['event group offset'], \
        group['event group length'], group['schema index'], \
        group['event count'] = unpack_from(">HxxIBxHHBB", group_dump)
    group['event indexes'] = unpack_from(">16H", group_dump[0x10:])
    group['name'], nlen = read_string(group_dump[NAMELEN_OFFSET:])
    group['description'], dlen = read_string(group_dump[(NAMELEN_OFFSET + nlen):])

    return glen, group

def read_groups():
    f = open('81e00610.v7.lid', 'r')
    f.seek(0x2a000, 0)
    group_length = 5
    dump = f.read(PAGE_SIZE * group_length)

    i = 0
    group_count = 0x8b
    offset = 0
    f = open('groups.csv', 'wt')
    try:
        writer = csv.writer(f)

        for i in range(0, group_count):
            glen, group = read_group(dump[offset:])
            offset += glen
            if i == 0:
                writer.writerow((group.keys()))
            writer.writerow((group.values()))
    finally:
        f.close()

read_groups()

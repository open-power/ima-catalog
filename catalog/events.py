# This file packages all events into a binary file, which will be a part of the
# catalog file.
from struct import *
import csv
from common import *

def event_pack(event):
    header = pack(">HBxHHHIHH", event['formula_index'], event['domain'],
                  event['record_byte_offset'], event['record_length'],
                  event['counter_offset'], event['flag'],
                  event['primary_group_index'], event['group_count'])

    e = header + pack_text(event['name']) + pack_text(event['description'])
    e += pack_text(event['detailed_description'])

    return pad16(e)

def pack_events(events_csv):
    events = ""

    with open(events_csv) as csvfile:
        reader = csv.DictReader(csvfile)
        event = {}
        count = 0
        core_offset = -1
        chip_offset = -1
        pmu_offset = -1
        for row in reader:
            if chip_offset == -1 and int(row['domain']) == 1:
                chip_offset = len(events)

            if core_offset == -1 and int(row['domain']) == 2:
                core_offset = len(events)

            if pmu_offset == -1 and int(row['domain']) == 3:
                pmu_offset = len(events)

            count += 1
            if row['formula index'] == "-1":
                event['formula_index'] = 0xffff
            else:
                event['formula_index'] = int(row['formula index'])
            event['domain'] = int(row['domain'])
            event['record_byte_offset'] = int(row['record byte offset'])
            event['record_length'] = int(row['record length'])
            event['counter_offset'] = int(row['counter offset'])
            event['flag'] = int(row['flag'])
            event['primary_group_index'] = int(row['primary group index'])
            event['group_count'] = int(row['group count'])
            event['name'] = row['name']
            event['description'] = row['description']
            event['detailed_description'] = row['detailed description']

            events += event_pack(event)

        return pad_page(events, PAGE_SIZE), count, (chip_offset, core_offset, pmu_offset)

if __name__ == "__main__":
    events, count, offsets = pack_events('events.csv')
    if len(events) == 0:
        print "Error in generating events binary dump"

    f = open('events.bin', 'w')
    f.write(events)
    f.close()
#    hexdump(events, " ", 16)

#!/usr/bin/python
#
# Copyright (C) 2016 Santosh Sivaraj <santosiv@in.ibm.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

from struct import *
from common import *
import sys

GNAMELEN_OFFSET = 0x30
ENAMELEN_OFFSET = 0x14
FNAMELEN_OFFSET = 0x10

def read_group(group_dump):
    group = {}
    glen, group['flag'], group['domain'], group['event group offset'], \
        group['event group length'], group['schema index'], \
        group['event count'] = unpack_from(">HxxIBxHHBB", group_dump)
    group['event indexes'] = unpack_from(">16H", group_dump[0x10:])
    group['name'], nlen = read_string(group_dump[GNAMELEN_OFFSET:])
    group['description'], dlen = read_string(group_dump[(GNAMELEN_OFFSET + nlen):])

    return glen, group

def read_formula(formula_dump):
    formula = {}
    tlen, formula['flag'], formula['Group'] = unpack_from(">HxxIH6x",
                                                          formula_dump)
    if formula['flag'] == 0x4:
        formula['Grouped'] = 'y'
    else:
        formula['Grouped'] = 'n'

    formula['Formula Name'], nlen = read_string(formula_dump[FNAMELEN_OFFSET:])
    formula['Formula Description'], dlen = read_string(formula_dump[(FNAMELEN_OFFSET + nlen):])
    formula['Formula'], flen = read_string(formula_dump[(FNAMELEN_OFFSET + nlen + dlen):])
    formula['Unit'], ulen = read_string(formula_dump[(FNAMELEN_OFFSET + nlen + dlen + flen):])

    return tlen, formula

def read_event(event_dump):
    event = {}
    elen, event['formula index'], event['domain'], event['record byte offset'], event['record length'], \
        event['counter offset'], event['flag'], event['primary group index'], \
        event['group count'] = unpack_from(">HHBxHHHIHH", event_dump)

    if event['formula index'] == 0xffff:
        event['formula index'] = "-1"

    event['name'], nlen = read_string(event_dump[ENAMELEN_OFFSET:])
    event['description'], dlen = read_string(event_dump[(ENAMELEN_OFFSET + nlen):])
    event['detailed description'], ddlen = read_string(event_dump[(ENAMELEN_OFFSET + nlen + dlen):])

    return elen, event

def read_groups(dump_file, page_offset, num_pages, num_count, group_type):
    f = open(dump_file, 'r')
    f.seek(page_offset * PAGE_SIZE, 0)
    dump = f.read(PAGE_SIZE * num_pages)

    if group_type == 'groups':
        read_fn = read_group
    elif group_type == 'events':
        read_fn = read_event
    elif group_type == 'formulae':
        read_fn = read_formula
    else:
        print "No such group"

    offset = 0
    groups = []
    for i in range(0, num_count):
        glen, group = read_fn(dump[offset:])
        offset += glen
        groups.append(group)

    f.close()

    return groups

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Require a lid file to read from"
        exit(1)

    lid_file = sys.argv[1]

    f = open(lid_file, 'r')
    dump = f.read(PAGE_SIZE)
    f.close()

    desc, length, version, build_date, schema_offset, schema_len, schema_len, \
    event_offset, event_len, event_count, group_offset, group_len, \
    group_count, formula_offset, formula_len, formula_count = unpack_from(">IIQ16s32xHHHxxHHHxxHHHxxHHHxx",
                                                                          dump)

    signature = struct.unpack('4s', struct.pack('>I', desc))[0]
    if signature != "24x7":
        print "Not a catalog file"
        exit(1)

    print "File Signature: %s\nLength: %d\nVersion: %lu\nBuild Date: %s" % (signature, length, version, build_date)

    write_to_csv('formulae.csv', read_groups(lid_file, formula_offset, formula_len, formula_count, 'formulae'))
    write_to_csv('events.csv', read_groups(lid_file, event_offset, event_len, event_count, 'events'))
    write_to_csv('groups.csv', read_groups(lid_file, group_offset, group_len, group_count, 'groups'))

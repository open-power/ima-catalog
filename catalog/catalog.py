#!/usr/bin/python
#
# Copyright (C) 2016 Santosh Sivaraj <santosiv@in.ibm.com>
# Copyright (C) 2016 Rajarshi Das <drajarshi@in.ibm.com>
# Copyright (C) 2016 IBM Corporation
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version
# 2 of the License, or (at your option) any later version.

import struct
import time
import sys
from datetime import datetime
from common import *
from events import pack_events
from groups import pack_groups
from formulae import pack_formulae
from generate_dts import gen_dts

def dump_schema(cat_file):
    f = open(cat_file)
    f.seek(0x1000)
    s = f.read(PAGE_SIZE)
    f.close()

    return s

def create_catalog(version, old_lid):
    events, enum, event_offsets = pack_events('events.csv')
    groups, gnum, group_offsets  = pack_groups('groups.csv')
    formulae, fnum = pack_formulae('formulae.csv')
    # we will not create the schema now, will extract the schema from the
    # existing catalog file.
    schema = dump_schema(old_lid)

    schema_offset = 1
    events_offset = schema_offset + len(schema) / PAGE_SIZE
    events_length = len(events) / PAGE_SIZE
    groups_offset = events_offset + len(events) / PAGE_SIZE
    groups_length = len(groups) / PAGE_SIZE
    formulae_offset = groups_offset + len(groups) / PAGE_SIZE
    formulae_length = len(formulae) / PAGE_SIZE
    # WARNING: schema len and offset is hardcoded here
    header = struct.pack(">IIQ16s32xHHHxxHHHxxHHHxxHHHxx", 0x32347837, 64,
                         version,
                         datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S'),
                         1, 1, 4, events_offset, events_length, enum,
                         groups_offset, groups_length, gnum, formulae_offset,
                         formulae_length, fnum)
    core_event_offset = event_offsets[1]
    chip_event_offset = event_offsets[0]
    pmu_event_offset = event_offsets[2]
    core_group_offset = group_offsets[1]
    chip_group_offset = group_offsets[0]
    pmu_group_offset  = 0xffffffff # invalid -  we don't have pmu groups
    header += struct.pack(">IIIIII8x", core_event_offset, pmu_event_offset,
                          chip_event_offset, core_group_offset,
                          pmu_group_offset, chip_group_offset)

    return pad_page(header, PAGE_SIZE) + schema + events + groups + formulae

if __name__ == "__main__":
    if len(sys.argv) <= 3:
        print "Usage: ./%s version old_lid out_file" % (sys.argv[0])
        print "\nThe new LID and DTS files will be named as <out_file>.lid and <out_file>.dts"
        exit(1)

    lid_filename = str(sys.argv[3]) + '.lid'
    dts_filename = str(sys.argv[3]) + '.dts'

    # get the version for the new build, and older catalog file to extract the
    # schema data
    c = create_catalog(int(sys.argv[1]), sys.argv[2])
    padlen = 64 - len(c) / PAGE_SIZE
    c += struct.pack('%dx' % (padlen * PAGE_SIZE))

    f = open(lid_filename, 'wt')
    f.write(c)
    f.close()

    # Specify input filename (new lid), verbose flag, and dts output filename
    gen_dts(lid_filename, False, dts_filename)

#!/usr/bin/python
#/*
# *
# * Generate IMA performance events catalog
#
# * Copyright (C) 2017 Santosh Sivaraj <santosiv@in.ibm.com>, IBM
# * Copyright (C) 2017 Rajarshi Das <drajarshi@in.ibm.com>, IBM
# * Copyright (C) 2017 IBM Corporation
#
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# */

import struct
import time
import sys
from datetime import datetime
from common import *
from events import pack_events
from groups import pack_groups
from formulae import pack_formulae
from generate_dts import gen_dts,gen_dtb

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
    print 'version: {}'.format(version)
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
    unitname = ''
    pvr = ''
    coreimaflag = ''
    threadimaflag = ''

    if len(sys.argv) <= 3:
	print "In order to generate a new catalog LID and new DTS file:\n"
#	print "Usage: ./%s version old_lid out_file" % (sys.argv[0])
#       print "Usage: ./%s version old_lid new_prefix\n" % (sys.argv[0])
        print "Usage: ./%s version old_lid new_prefix <unitname> <pvrname> <threadima> <coreima> \n" % (sys.argv[0])
	print "e.g. ./%s 	8  v8.3.lid  e8100910 mcs 4D0200 yes yes \n" % (sys.argv[0])
	print "The arguments marked in <> are optional. \n"
	print "The new LID and DTS files will be named as <new_prefix>.lid and <new_prefix>.dts"
        exit(1)

    print 'Arguments specified:\n'
    print 'Version: ' + str(sys.argv[1]) + ' Old LID file: ' + str(sys.argv[2])

    new_lid_filename = str(sys.argv[3]) + '.lid'
    print 'New LID file: {}'.format(new_lid_filename)
    dts_filename = str(sys.argv[3]) + '.dts'
    print 'DTS file: {}'.format(dts_filename)

    if len(sys.argv) >= 5: 
    	unitname = str(sys.argv[4])
    if len(sys.argv) >= 6: 
    	pvr  = str(sys.argv[5])
    if len(sys.argv) >= 7: 
    	coreimaflag  = str(sys.argv[6])
    if len(sys.argv) == 8: 
    	threadimaflag = str(sys.argv[7])

    # get the version for the new build, and older catalog file to extract the
    # schema data
#    c = create_catalog(int(sys.argv[1]), sys.argv[2])
    # Handle the LID# and the LID version# in the 'version' field
    c = create_catalog(int(sys.argv[1], 0), sys.argv[2])
    padlen = 64 - len(c) / PAGE_SIZE
    c += struct.pack('%dx' % (padlen * PAGE_SIZE))

#   f = open(sys.argv[3], 'wt')
    f = open(new_lid_filename, 'wt')
    f.write(c)
    f.close()
	
    # Specify input filename (new lid), verbose flag, and dts output filename 
#   gen_dts(new_lid_filename, False, dts_filename)
    # Specify input filename (new lid), verbose flag, dts output filename , unit to fetch, pvr id, core ima (yes or no), thread ima (yes or no)
    gen_dts(new_lid_filename, False, dts_filename, unitname, pvr, coreimaflag, threadimaflag)

    # Generate the dtb binary
    dtb_filename = str(sys.argv[3])+'.dtb.bin'
    print 'DTB file: {}'.format(dtb_filename)
    gen_dtb(dts_filename, dtb_filename)

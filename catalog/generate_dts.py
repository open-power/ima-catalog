#!/usr/bin/python
#
# Copyright (C) 2016 Madhavan Srinivasan <maddy@linux.vnet.ibm.com>, IBM
#           (C) 2016 Hemant K. Shaw <hemant@linux.vnet.ibm.com>
#           (C) 2016 Rajarshi Das <drajarshi@in.ibm.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version
# 2 of the License, or (at your option) any later version.

import sys, getopt
import string
from struct import *
from collections import namedtuple
import os

event_domain_1 = []	#Chip IMA events
event_domain_2 = []	#Core IMA event (PDBAR)
event_domain_2_a = []	#Thread IMA event (LDBAR)
event_domain_3 = []	#per-thread PMU events
event_domain_4 = []	#OCC Sensors evenst
group_chip = []		#Chip IMA Group

nest_units = {
    "MCS":0,
    "PowerBus":1,
    "Pumps_and":1,
    "X-link":2,
    "A-link":3,
    "PHB":4,
    "Unknown":5
}

nest_unit_names = ["mcs", "powerbus", "xlink", "alink","phb"]

nest_mcs_scale = "1.2207e-4"
nest_mcs_unit = "MiB"
core_ima_scale = "128"

# Filter out the raw (non-ascii) byes
def get_name(st):
    res = set(string.printable)
    return filter(lambda x: x in res, st)

class Page0:
    def __init__(self, data):
	self.page0_format = 'I I Q 16s 32s H H H 2s H H H 2s H H H 2s \
                             H H H 2s I I I I I I 8s'
	self.page0_str = 'desc len ver build res1 sd_off sd_len sd_cnt\
			  res2 ed_off ed_len ed_cnt res3 gd_off\
			  gd_len gd_cnt res4 fr_off fr_len  fr_cnt\
			  res5 coree_off th_off che_off coreg_off\
			  thg_off chg_off res6'
	self.page0_arr = namedtuple('page0_arr', self.page0_str)
	self.page0 = self.page0_arr._make(unpack("> "+self.page0_format, data))

    def get_events_start(self):
	return (self.page0.ed_off * 4096)

    def get_events_count(self):
	return (self.page0.ed_cnt)

    def get_group_start(self):
	return (self.page0.gd_off * 4096)

    def get_group_count(self):
	return (self.page0.gd_cnt)

class Event:
    def __init__(self, fn, offset):
        self.offset = offset
        self.event_hformat = 'H H B s H H H I H H H'
        self.event_str = 'len fr domain res1 st_off ev_len ev_off flag \
			      pr_idx grp_cnt ev_name_len'
        self.event_arr = namedtuple('event_arr', self.event_str)
        fn.seek(0)
        fn.seek(self.offset)
        self._event = self.event_arr._make(unpack("> "+self.event_hformat,
                                                  fn.read(calcsize(self.event_hformat))))
        self._ev_offset = self._event.st_off + self._event.ev_off
        self._ev_name_r = fn.read(self._event.ev_name_len - 2)
        self._ev_name = get_name(self._ev_name_r)
        self._ev_desc_ft = 'H'
        self._ev_desc_str = 'len'
        self._ev_desc = namedtuple('_ev_desc', self._ev_desc_str)
        self._ev_des = self._ev_desc._make(unpack("> "+self._ev_desc_ft,
                                                  fn.read(calcsize(self._ev_desc_ft))))
        self._ev_description = fn.read(self._ev_des.len-2)
        self._ev_description = get_name(self._ev_description)
        self._ev_des_d = self._ev_desc._make(unpack("> "+self._ev_desc_ft,
                                                    fn.read(calcsize(self._ev_desc_ft))))
        self._ev_de_desc = fn.read(self._ev_des_d.len)
        ev_list = [self._ev_name, self._ev_offset, self._ev_description]
            if (self._event.domain == 1):
                event_domain_1.append(ev_list)
            elif (self._event.domain == 2):
                event_domain_2.append(ev_list)
                event_domain_2_a.append(ev_list)
            elif (self._event.domain == 3):
                event_domain_3.append(ev_list)
            else:
                print "Unknown Domain"


class Events:
    def __init__(self, fn, offset, cnt):
        self.offset = offset
        self.cnt = cnt
        self.event_hformat = 'H'
        self.event_str = 'len'
        self.event_arr = namedtuple('event_arr', self.event_str)
            for i in range(0, cnt):
                fn.seek(0)
                fn.seek(self.offset)
                self._event = self.event_arr._make(unpack("> "+self.event_hformat,
                                                          fn.read(calcsize(self.event_hformat))))
                Event(fn, self.offset)
                self.offset += self._event.len

class Group:
    def __init__(self, fn, offset):
        self.offset = offset
        self.grp_hformat = 'H 2s I B s H H B B HHHHHHHHHHHHHHHH H'
        self.grp_str = 'len res1 flag domain res2 sta_off gr_len sc_idx\
                                    ev_cnt ev_idx0 ev_idx1 ev_idx2 ev_idx3\
                                    ev_idx4 ev_idx5 ev_idx6 ev_idx7 ev_idx8\
                                    ev_idx9 ev_idx10 ev_idx11 ev_idx12\
                                    ev_idx13 ev_idx14 ev_idx15 name_len'
        self.grp_arr = namedtuple('grp_arr', self.grp_str)
        fn.seek(0)
        fn.seek(self.offset)
        self._group = self.grp_arr._make(unpack("> "+self.grp_hformat,
                                                fn.read(calcsize(self.grp_hformat))))
        self._grp_name_r = fn.read(self._group.name_len - 2)
        self._grp_name = self._grp_name_r.strip("0")
        self.dt_index = -1
        for key, value in nest_units.items():
                if self._grp_name.startswith(key):
                    self.dt_index = value
        if ( self.dt_index == -1):
                return

        arr = []
        arr.append(self._group.ev_idx0)
        arr.append(self._group.ev_idx1)
        arr.append(self._group.ev_idx2)
        arr.append(self._group.ev_idx3)
        arr.append(self._group.ev_idx4)
        arr.append(self._group.ev_idx5)
        arr.append(self._group.ev_idx6)
        arr.append(self._group.ev_idx7)
        arr.append(self._group.ev_idx8)
        arr.append(self._group.ev_idx9)
        arr.append(self._group.ev_idx10)
        arr.append(self._group.ev_idx11)
        arr.append(self._group.ev_idx12)
        arr.append(self._group.ev_idx13)
        arr.append(self._group.ev_idx14)
        arr.append(self._group.ev_idx15)

        for i in range(0, self._group.ev_cnt):
            group_chip[self.dt_index].append(arr[i])


class Groups:
    def __init__(self, fn, offset, cnt):
        self.offset = offset
        self.cnt = cnt
        self.group_len = 'H'
        self.group_str = 'len'
        self.group_arr = namedtuple('group_arr', self.group_str)
            for i in range(0, len(nest_units)):
                group_chip.append([])

            for i in range(0, cnt):
                fn.seek(0)
                fn.seek(self.offset)
                self._group = self.group_arr._make(unpack("> "+self.group_len,
                                                          fn.read(calcsize(self.group_len))))
                Group(fn, self.offset)
                self.offset += self._group.len


def dt_event(tabs, name, reg, size, unit, scale, desc, nodename): # Simplified node name
    s = ""
    s += '\t' * tabs +'%s@%x {\n'% (nodename, reg)
    s += '\t' * (tabs+1) + 'event-name = "%s" ;\n' % (name)
    s += '\t' * (tabs+1) + 'reg = <0x%x 0x%x>;\n'%(reg,size)
    if unit != '' and unit.strip() :
	s += '\t' * (tabs+1) + 'unit = "%s" ;\n'%(unit)
    if scale != '' and scale.strip() :
	s += '\t' * (tabs+1) + 'scale = "%s" ;\n'%(scale)
        s += '\t' * (tabs + 1) + 'desc = "%s" ;\n' % (desc)
	s += '\t' * tabs + '};'
    return s

def dt_unit(tabs,unit,events, compat):
    xlink_cyc_event_added = False
    xlink_cyc_last_sample_event_added = False
    alink_cyc_event_added = False
    alink_cyc_last_sample_event_added = False
    event_count = 0

    s = ""
    tabs += 1
    s += '\t' * tabs +'%s {\n'% (nest_unit_names[unit])
    tabs += 1
    s += '\t' * tabs + "compatible = \"%s\";\n"%compat
    s += '\t' * tabs + "ranges;\n"
    s += '\t' * tabs + "#address-cells = <0x1>;\n"
    s += '\t' * tabs + "#size-cells = <0x1>;\n\n"
    event_scale = ''
    event_unit = ''
    if nest_unit_names[unit] == "mcs":
        event_scale = nest_mcs_scale
        event_unit = nest_mcs_unit
    for i in events:
        event = event_domain_1[i]
        if event[0] == 'PM_XLINK_CYCLES' and xlink_cyc_event_added == True:
            continue
        if event[0] == 'PM_XLINK_CYCLES_LAST_SAMPLE' and \
           xlink_cyc_last_sample_event_added == True:
            continue
        if event[0] == 'PM_ALINK_CYCLES' and alink_cyc_event_added == True:
            continue
        if event[0] == 'PM_ALINK_CYCLES_LAST_SAMPLE' and \
           alink_cyc_last_sample_event_added == True:
            continue

        nodename = nest_unit_names[unit] + "-" + str(event_count)
        s += dt_event((tabs), event[0], event[1], 8, event_unit,
                      event_scale, event[2], nodename)
        event_count = event_count + 1
        if event[0] == 'PM_XLINK_CYCLES':
            xlink_cyc_event_added = True
        if event[0] == 'PM_XLINK_CYCLES_LAST_SAMPLE':
            xlink_cyc_last_sample_event_added = True
        if event[0] == 'PM_ALINK_CYCLES':
            alink_cyc_event_added = True
        if event[0] == 'PM_ALINK_CYCLES_LAST_SAMPLE':
            alink_cyc_last_sample_event_added = True
        s += "\n"

    s += '\t' * (tabs-1) + "};\n"
    return s

def core_ima_dt_unit(tabs, events):
    s = ""
    groupname = "core-ima"
    s += '\t' * tabs + '%s {\n' % (groupname)
    tabs +=1
    s += '\t' * tabs + "compatible = \"%s\";\n" % "ibm,ima-counters-core"
    s += '\t' * tabs + "ranges;\n"
    s += '\t' * tabs + "#address-cells = <0x1>;\n"
    s += '\t' * tabs + "#size-cells = <0x1>;\n\n"
    event_count = 0
    for i in events:
        nodename = groupname + "-" + str(event_count)
        s += dt_event(tabs, i[0], i[1], 8, '', core_ima_scale, i[2], nodename)
        event_count = event_count + 1
        s += "\n"

    s += '\t' * (tabs - 1) + "};\n"
    return s

def thread_ima_dt_unit(tabs, events):
    s = ""
    groupname = "thread-ima"
    s += '\t' * tabs + '%s {\n' % (groupname)
    tabs +=1
    s += '\t' * tabs + "compatible = \"%s\";\n" % "ibm,ima-counters-thread"
    s += '\t' * tabs + "ranges;\n"
    s += '\t' * tabs + "#address-cells = <0x1>;\n"
    s += '\t' * tabs + "#size-cells = <0x1>;\n\n"
    event_count = 0
    for i in events:
        nodename = groupname + "-" + str(event_count)
        s += dt_event(tabs, i[0], i[1], 8, '', '', i[2], nodename)
        event_count = event_count + 1
        s += "\n"

    s += '\t' * (tabs - 1) + "};\n"
    return s


def gen_dtb(ofname, odtbfname):
    dtb_command = "dtc -I dts -O dtb -o " + odtbfname + " ./" + ofname

    if odtbfname == '':
	print 'Output DTB filename missing. Specify -d <DTB filename> and retry. Exiting.'
	exit(-1)

    try:
        os.system(dtb_command)
    except:
        print 'Error in dtb command: {}'.format(dtb_command)

    print 'Generated DTB file: {}'.format(odtbfname)


def gen_dts(ifname, verbose, ofname, unitname, pvrname, threadima, coreima):
    try:
        fn = open(ifname, "rb")
    except:
        print 'Input filename missing. Specify -i <catalog lid file name> and retry.. Exiting.'
        exit(-1)

    try:
        of = open(ofname, "w")
    except:
        print 'Output filename missing. Specify -o <output file name> and retry.. Exiting.'
        exit(-1)

    if pvrname == '': # pvr name was not specified.
        pvrname = "4D0200"

    # the page0 catalog is 128 bytes long
    page0 = Page0(fn.read(128))
    Events(fn, page0.get_events_start(), page0.get_events_count())
    Groups(fn, page0.get_group_start(), page0.get_group_count())

    s =\
"""
/dts-v1/;

/ {
\tname = "";
\tcompatible = \"ibm,opal-in-memory-counters\";
\t#address-cells = <0x1>;
\t#size-cells = <0x1>;
\tima-nest-offset = <0x320000>;
\tima-nest-size = <0x30000>;
\tversion-id = \"\";\n
"""

    pvr_list = pvrname.split(',')

    for pvr in pvr_list:
        pvr_str = '\tpvr@' + pvr + ' {'
        pvr_node =\
"""
\t\t#address-cells = <0x1>;
\t\t#size-cells = <0x1>;
\t\tima-nest-offset = <0x320000>;
\t\tima-nest-size = <0x30000>;
\t\tversion-id = \"\";
"""
        tabs = 0

        if pvr not in '4E0100': # P9 DD1 parts. No Nest units for now.
            for i in range(len(nest_units)):
                if unitname != 'all' and unitname != '': # specific unit indicated. Print that unit only
                    if nest_unit_names[i] == unitname:
                        if i < len(nest_unit_names):
                            if (len(group_chip[i])):
                                s += dt_unit(tabs,i,group_chip[i], "ibm,ima-counters-nest")
                        break
                elif unitname == 'all': # Include all NEST units
                    if i < len(nest_unit_names):
                        if (len(group_chip[i])):
                            s += dt_unit(tabs,i,group_chip[i], "ibm,ima-counters-nest")
                else: # no unit name was explicitly specified. Assume 'mcs' if pvrname is 4D0200
                    if pvrname == '4D0200':
                        if nest_unit_names[i] == 'mcs':
                            if i < len(nest_unit_names):
                                if (len(group_chip[i])):
                                    s += dt_unit(tabs,i,group_chip[i], "ibm,ima-counters-nest")
                            break
                    else: # pvrname is not 4D0200. Print all NEST units
                        if i < len(nest_unit_names):
                            if (len(group_chip[i])):
                                s += dt_unit(tabs,i,group_chip[i], "ibm,ima-counters-nest")
        else: # for P9 DD1 (4E0100) print core and thread ima by default
            coreima = "yes"
            threadima = "yes"

        if coreima == "yes":
            s += core_ima_dt_unit(1, event_domain_2)

        if threadima == "yes":
            s += thread_ima_dt_unit(1, event_domain_2_a)

    s += "};\n"

    of.write(s)
    of.close
    print 'Generated DTS file: {}'.format(ofname)

if __name__ == "__main__":
    ifname = "" # input file name
    ofname = "" # output file name
    verbose = False
    coreima = "no" # Do not print core ima by default (if no unit was explicitly specified)
    threadima = "no" # Do not print thread ima by default (if no unit was explicitly specified)
    pvrname = ""
    unitname = ""
    odtbfname = "" # output dtb file name

    options, remainder = getopt.getopt(sys.argv[1:], 'c:d:i:p:t:u:vo:',
                                       ['coreima=',
					'outputdtb=',
					'input=',
					'pvr=',
					'threadima=',
					'unit=',
					'verbose',
					'output='
                                       ])

    for opt, arg in options:
	if opt in ('-c', '--core'):
	    coreima = arg
	elif opt in ('-i', '--input'):
	    ifname = arg
	elif opt in ('-p', '--pvr'):
	    pvrname = arg
	elif opt in ('-t', '--thread'):
	    threadima = arg
	elif opt in ('-u', '--unit'):
	    unitname = arg
	elif opt in ('-v', '--verbose'):
	    verbose = True
	elif opt in ('-o', '--output'):
	    ofname = arg
	elif opt in ('-d', '--outputdtb'):
	    odtbfname = arg

    gen_dts(ifname, verbose, ofname, unitname, pvrname, coreima, threadima)
    gen_dtb(ofname, odtbfname)

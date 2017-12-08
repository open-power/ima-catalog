#!/usr/bin/python
#/*
# * Copyright (C) 2017 Madhavan Srinivasan <maddy@linux.vnet.ibm.com>, IBM
#             (C) 2017 Hemant K. Shaw <hemant@linux.vnet.ibm.com>
#             (C) 2017 Rajarshi Das <drajarshi@in.ibm.com>
# *
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# */


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

nest_units_P8 = {
	"MCS":0,
	"PowerBus":1,
	"Pumps_and":1,
	"X-link":2,
	"A-link":3,
	"PHB":4,
	"Unknown":5
}

# XLINK0 is also part of XLINK_OUT.
# To add XLINK_IN back, reset the mapping from XLINK_IN: 3, in sequence
# e.g. xlink_out: 4, .... capp: 7, ntl and ats: 8, nx: 9
nest_units_P9 = {
	"PowerBus":0,
	"MCS":1,
	"MBA":2,
#	"XLINK_IN":3, # Need a separate common node for *IN and *OUT
	"XLINK_OUT":3,
	"MCD":4,
	"PHB":5, # Group name starts with PCIE. Map this to group phb below
	"CAPP":6,
	"NTL":7, # NVLink
        "ATS":7, # NVLink
	"NX":8
}

nvlink_P9 = {
        "0": ["NTL0", "NPCQ0", "ATS", "XTS"],
        "1": ["NTL1", "NPCQ0", "ATS", "XTS"],
        "2": ["NTL2", "NPCQ1", "ATS", "XTS"],
        "3": ["NTL3", "NPCQ1", "ATS", "XTS"],
        "4": ["NTL4", "NPCQ2", "ATS", "XTS"],
        "5": ["NTL5", "NPCQ2", "ATS", "XTS"],
}

TOD_index = 220 # Event position for 'TOD'. Used to trim events list before calling dt_unit2. P9/ NEST only

# List of events which need to be skipped for each unit, while preparing the P9 DTS
P9_NEST_skip_list = {
 'mcs': ['PM_PB_CYC', 'PM_PB_CYC2']
}

nest_unit_names_P8 = ["mcs", "powerbus", "xlink", "alink","phb"]
nest_unit_indices_P8 = [0, 0, 0, 0, 0]

nest_unit_prefixes_P8 = ["NODEF", "PM_PB_", "NODEF", "NODEF", "NODEF"]

# The following commented section corresponds to 'xlink_in' that existed previously. 
#nest_unit_names_P9 = ["powerbus", "mcs", "mba", "xlink_in", "xlink_out", "mcd", "phb", "capp", "ntl", "nx"] # ntl => nvlink
#nest_unit_indices_P9 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#nest_unit_prefixes_P9 = ["PM_PB_", "NODEF", "NODEF", "NODEF", "NODEF", "NODEF", "NODEF"\
#				, "NODEF", "NODEF", "PM_NX_"] # "NODEF" implies it is constructed at runtime
#nest_unit_scale_P9 = ["256", "256", "1", "4096", "4096", "256", "1", "256", "256", "256"] # Per unit prescale
#nest_unit_names_supported_P9 = ["mcs", "powerbus", "xlink", "phb"] # Modify this based on actual support
#nest_unit_names_supported_P9 = ["mcs", "powerbus", "xlink_in", "xlink_out", "phb", "mba", "mcd", "capp", "ntl", "nx"] # Modify this based on actual support
#nest_unit_names_multi_P9 = ["mcs", "mba", "xlink_in", "xlink_out", "mcd", "phb", "ntl", "capp"] # Units that are multiple (e.g. mcs0-3)
#nest_unit_count_multi_P9 = [2, 8, 1, 2, 2, 6, 6, 2] # how many units?

nest_unit_names_P9 = ["powerbus", "mcs", "mba", "xlink_out", "mcd", "phb", "capp", "ntl", "nx"] # ntl => nvlink
nest_unit_indices_P9 = [0, 0, 0, 0, 0, 0, 0, 0, 0]

nest_unit_prefixes_P9 = ["PM_PB_", "NODEF", "NODEF", "NODEF", "NODEF", "NODEF"\
				, "NODEF", "NODEF", "PM_NX_"] # "NODEF" implies it is constructed at runtime

nest_unit_scale_P9 = ["256", "256", "1", "4096", "256", "1", "256", "256", "256"] # Per unit prescale

nest_unit_names_supported_P9 = ["mcs", "powerbus", "xlink_out", "phb", "mba", "mcd", "capp", "ntl", "nx"] # Modify this based on actual support
# Not added 'ats' in the above list, since the ats events already get added under the group_chip[] with index for 'ntl'

nest_unit_names_multi_P8 = ["mcs", "xlink", "alink", "phb"]
nest_unit_count_multi_P8 = [4, 2, 2, 3]

nest_unit_names_multi_P9 = ["mcs", "mba", "xlink_out", "mcd", "phb", "ntl", "capp"] # Units that are multiple (e.g. mcs0-3)
nest_unit_count_multi_P9 = [2, 8, 3, 2, 6, 6, 2] # number of units per unit type

nest_unit_names = []
nest_unit_indices = []
nest_units = []

nest_unit_names_multi = []
nest_unit_count_multi = []

nest_unit_prefixes = []

nest_mcs_scale = "1.2207e-4"
nest_mcs_unit = "MiB"

cb_nest_offset = 0x3fc00;

nest_mcs_scale_P9 = "4"
nest_mcs_unit_P9 = "MiB/s"

core_imc_scale = "512"
thread_imc_scale = "512"

mcs_unit_count = 4 # 4 MCS (MC) units expected

nest_offset_P9 = 0x180000;
nest_size_P9   = 0x40000;
cb_nest_offset_P9 = 0x3fc00;

core_thread_size_P9 = 0x2000;

type_chip_P9   = 0x10;
type_core_P9   = 0x4;
type_thread_P9   = 0x1;

pvrvalue = ""

#< P9 below
nest_offset	   = 0x320000;
nest_size	   = 0x80000;
type_chip      = 0x10;
type_core      = 0x4;
type_thread    = 0x1;

core_thread_size = 0x2000;

# PVR lists
p8_pvr_list = ["4D0200", "4D0100", "4D0000"]
# The reduced list was originally intended to print only 'mcs' nodes
# . But to align with the pull request from Mar 13 '17, 
# printing only 'mcs' nodes for 4D0100 as well.
p8_reduced_pvr_list = ["4D0200", "4D0100"]
p9_pvr_list = ["4E0100", "4E0200"] # 4E implies P9. 01=> DD1, 02=> DD2

# Track the UP and DOWN events
down_xfer_event = 0
up_xfer_event = 0

# Filter out the raw (non-ascii) byes
def get_name(st):
        res = set(string.printable)
        return filter(lambda x: x in res, st)

class Page0:
	def __init__(self, data):
		self.page0_format = "I I Q 16s 32s H H H\
					2s H H H 2s H H H 2s H H H 2s I I I\
					I I I 8s"
		self.page0_str = 'desc len ver build res1 sd_off sd_len sd_cnt\
					res2 ed_off ed_len ed_cnt res3 gd_off\
					gd_len gd_cnt res4 fr_off fr_len  fr_cnt\
					res5 coree_off th_off che_off coreg_off\
					thg_off chg_off res6'
		self.page0_arr = namedtuple('page0_arr', self.page0_str)
		self.page0 = self.page0_arr._make(unpack("> "+self.page0_format,
								data))

	def get_events_start(self):
		return (self.page0.ed_off * 4096)

	def get_events_count(self):
		return (self.page0.ed_cnt)

	def get_group_start(self):
		return (self.page0.gd_off * 4096)

	def get_group_count(self):
		return (self.page0.gd_cnt)

	def get_pvr_and_version(self):
		return (self.page0.ver)

class Event:
	def __init__(self, fn, offset):
                self.offset = offset
                self.event_hformat = 'H H B s H H H I H H H'
                self.event_str = 'len fr domain res1 st_off ev_len ev_off flag\
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

                print('length of event_domain_1: {}'.format(len(event_domain_1)))
                for i in range(0,len(event_domain_1)):
                  print('event_domain_1: {}'.format(event_domain_1[i]))

class Group:
	def __init__(self, fn, offset, nest_units):
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
				print 'matched group: {} with key: {}'.format(self._grp_name, key)
#				if (key=='ATS'): This check is not required since the units_supported only includes 'NTL'
#                                  self.dt_index = nest_units['NTL'] # If we match ATS, include the events in the 'NTL' group
#                                else:
			        self.dt_index = value
                                break
                        if not (pvrvalue in p8_reduced_pvr_list or\
                            pvrvalue in p8_pvr_list):
                            print('check. group name: {}'.format(self._grp_name))
#		Since XLINK0 is also part of XLINK_OUT, XLINK_IN is not required.
#		Uncomment the lines if we need to separately add XLINK0 group specific events into XLINK_IN
#                            if 'XLINK0' in self._grp_name:
#                                    print('group name is {}'.format(self._grp_name))
#                                    self.dt_index = nest_units['XLINK_IN']
#                                    break
#                            elif ('XLINK1' in self._grp_name) or ('XLINK2' in self._grp_name):
                            if ('XLINK0' in self._grp_name) or ('XLINK1' in self._grp_name) \
                                      or ('XLINK2' in self._grp_name):
                                    print('group name is {}'.format(self._grp_name))
                                    self.dt_index = nest_units['XLINK_OUT']
                                    break
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

		print 'arr: {}'.format(arr)

		for i in range(0, self._group.ev_cnt):
			group_chip[self.dt_index].append(arr[i])
		print 'group_chip[{}]: {}'.format(self.dt_index, group_chip[self.dt_index])


class Groups:
	def __init__(self, fn, offset, cnt, nest_units):
		self.offset = offset
		self.cnt = cnt
		self.group_len = 'H'
		self.group_str = 'len'
		self.group_arr = namedtuple('group_arr', self.group_str)
		for i in range(0, len(nest_units)):
			group_chip.append([])

		print 'group count: {}'.format(cnt)
		for i in range(0, cnt):
			fn.seek(0)
			fn.seek(self.offset)
			self._group = self.group_arr._make(unpack("> "+self.group_len,
								fn.read(calcsize(self.group_len))))
			Group(fn, self.offset, nest_units)
			self.offset += self._group.len


def dt_event(tabs, name, reg, size, unit, scale, desc, nodename): # Simplified node name
	s = ""
	s += '\t' * tabs +'%s@%x {\n'% (nodename, reg)
	s += '\t' * (tabs+1) + 'event-name = "%s" ;\n' % (name)
	s += '\t' * (tabs+1) + 'reg = <0x%x 0x%x>;\n'%(reg,size)
	if unit != '' and unit != 'N/A' and unit.strip() :
		s += '\t' * (tabs+1) + 'unit = "%s" ;\n'%(unit)
	if scale != '' and scale != 'N/A' and scale.strip() :
		s += '\t' * (tabs+1) + 'scale = "%s" ;\n'%(scale)
	if desc != '' : # Add desc only if available
        	s += '\t' * (tabs + 1) + 'desc = "%s" ;\n' % (desc)
	s += '\t' * tabs + '};'
	return s

# 'unit' and 'scale' not covered in dt_event2(). Also, the name and offset change.
def dt_event2(tabs, name, reg, size, unit, scale, desc, nodename, \
			event_prefix): # Simplified node name
	global pvrvalue
	global p8_pvr_list, p8_reduced_pvr_list, p9_pvr_list

	unit_type = ''
	unit_name_ = ''
	unit_name = ''

	name_split2 = ''
	name_split = ''

	global up_xfer_event, down_xfer_event

	s = ""

#	Start the node always on P9
	if not (pvrvalue in p8_pvr_list or pvrvalue in p8_reduced_pvr_list):
		s += '\t' * tabs + '%s@%x {\n'% (nodename, reg)

	pm_prefix = "PM_"
	# For repeatable groups / events
			
	if (event_prefix != ''):
		print 'event_prefix: {}'.format(event_prefix);
		print 'name: {}'.format(name);

#		Split the first time only.
		name_split = name.split(event_prefix,1);
		print 'name_split: {}'.format(name_split);

		if pvrvalue in p8_pvr_list or pvrvalue in p8_reduced_pvr_list:
			print 'pvrvalue: {}'.format(pvrvalue)
			print 'p8_pvr_list: {}'.format(p8_pvr_list)
			print 'p8_reduced_pvr_list: {}'.format(p8_reduced_pvr_list)
			print 'down_xfer_event: {}'.format(down_xfer_event)
			print 'up_xfer_event: {}'.format(up_xfer_event)

			if ("_MC" in name_split[1]): # DOWN_128B_DATA_XFER_MC0
				name_split2 = name_split[1].split("_MC",1) # 'DOWN_128B_DATA_XFER',''
				# update the event nodes just once
				print 'name_split2[0]: {}\n'.format(name_split2[0])
				if (((name_split2[0]=="DOWN_128B_DATA_XFER") and down_xfer_event == 0) or\
					((name_split2[0]=="UP_128B_DATA_XFER") and up_xfer_event == 0)):
					print 'in..\n'
#					Start the node for P8 case within the if condition
					s += '\t' * tabs + '%s@%x {\n'% (nodename, reg)

					s += '\t' * (tabs+1) + 'event-name = "%s" ;\n'\
					% (name_split2[0]) # DOWN_128B_DATA_XFER

					if (name_split2[0]=="DOWN_128B_DATA_XFER"):
						down_xfer_event = 1
					if (name_split2[0]=="UP_128B_DATA_XFER"):
						up_xfer_event = 1
					s += '\t' * (tabs+1) + 'unit = "%s" ;\n' % (nest_mcs_unit)
					s += '\t' * (tabs+1) + 'scale = "%s" ;\n' % (nest_mcs_scale)
		else:
			s += '\t' * (tabs+1) + 'event-name = "%s" ;\n'\
			 % (name_split[1])

		if (event_prefix != 'CPM_'): # Not core / thread
			unit_name_ = event_prefix.split(pm_prefix); # e.g. {,MCS0_}
			unit_name = unit_name_[1].split('_'); # e.g.  {MCS0,}

			if pvrvalue in p8_pvr_list or pvrvalue in p8_reduced_pvr_list:
				unit_type = unit_name; # type and name are both MCS
			else:
				unit_type = unit_name[0].rstrip('0123456789'); # {MCS}
			print 'unit_name: {}, unit_type: {}'.format(unit_name, unit_type);
	else: # P9, NVLink: event_prefix=''
		s += '\t' * (tabs+1) + 'event-name = "%s" ;\n' %name

	print 'printing reg: {}, size: {}'.format(reg,size)

	# If we are P8, and we updated the event-name, unit and scale, then 
	# update the offset and size
	if pvrvalue in p8_pvr_list or pvrvalue in p8_reduced_pvr_list:
		if ((up_xfer_event == 1) or (down_xfer_event == 1)):
			s += '\t' * (tabs+1) + 'reg = <0x%x 0x%x>;\n'%(reg,size)
	else:
		s += '\t' * (tabs+1) + 'reg = <0x%x 0x%x>;\n'%(reg,size)

	print 'in hex: s: {}'.format(s)

	if desc != '' : # Add desc only if available
		if pvrvalue in p8_pvr_list or pvrvalue in p8_reduced_pvr_list:
			# Update the description only if the event isn't updated already
			print 'down_xfer_event: {}'.format(down_xfer_event)			
			print 'up_xfer_event: {}'.format(up_xfer_event)			

			if ((down_xfer_event == 1) or (up_xfer_event == 1)):
				if (down_xfer_event == 1):
					desc = "Total Write Bandwidth seen on both MCS";
					down_xfer_event = 2
				if (up_xfer_event == 1):
					desc = "Total Read Bandwidth seen on both MCS";
					up_xfer_event = 2
				s += '\t' * (tabs + 1) + 'desc = "%s" ;\n' % (desc)

				s += '\t' * tabs  + '};' # end the node within the if condition
				s += '\n'
		else:
			if (unit_type != ''): # repeatable unit. Remove the unit index
				print 'at repeatable unit. replacing {} with {}'.format(unit_name[0],unit_type);
				print 'desc before replacement: {}'.format(desc);
				desc_r = desc.replace(unit_name[0], unit_type); # replace MCS0 with MCS in the description to make it generic
				desc = desc_r;
				print 'desc after replacement: {}'.format(desc);
        		s += '\t' * (tabs + 1) + 'desc = "%s" ;\n' % (desc)

#	End the node always on P9
	if not (pvrvalue in p8_pvr_list or pvrvalue in p8_reduced_pvr_list):
		s += '\t' * tabs + '};'
		s += '\n'

	return s

# Group the NVlink events 
def dt_group_nvlink_events_P9(events):
  nvlink_groups_P9 = {}

  for key,value in nvlink_P9.items():
   newkey = 'nvlink' + key # nvlink0
   eventlist = []
   for i in range(0,len(events)): # PM_NTL0*
    for j in range(0,len(value)): # NTL0
     if (value[j] in event_domain_1[events[i]][0]):
       eventlist.append(events[i])
       break
   nvlink_groups_P9[newkey] = eventlist

  print('nvlink_groups_P9: {}'.format(nvlink_groups_P9))
  return nvlink_groups_P9

def dt_unit2(tabs, unit, events, compat, unit_names, unit_indices, unit_count, unit_prefixes): # In case there are multiple nodes of one type
	i = 0
	t = ""
	print 'unit: {} count: {}'.format(unit_names[unit], unit_count)

        if (unit > -1) and not (pvrvalue in p8_reduced_pvr_list or\
                              pvrvalue in p8_pvr_list):
           while TOD_index in events:
            events.remove(TOD_index) # Remove the TOD event entry if P9/NEST

           for k,v in P9_NEST_skip_list.items(): # Remove the entries in the P9/NEST skip list
            if unit_names[unit] == k:
               print('events before applying skip list: {}'.format(events))
               for i in range(0,len(v)):
                for j in range(0,len(event_domain_1)):
#                 print(event_domain_1[j][0])
                  if (event_domain_1[j][0] == v[i]):
                   events.remove(j)
                   break
               print('events after applying skip list: {}'.format(events))
               
#       First print the common node for the unit: includes all the common events
	[unit_common_string, event_prefix, unit_prefix] = dt_unit_common(tabs, unit, events, compat, \
				unit_names, unit_indices, unit_count, unit_prefixes);

	t += unit_common_string;

#       For NVlink (P9), need to have a dummy unit node/ super node, hence commented section below.
#       If a unit node/ super node is not required, uncomment the following 4 lines.
#        if not (pvrvalue in p8_reduced_pvr_list or\
#           pvrvalue in p8_pvr_list): # P9
#           if (unit_names[unit]) == 'ntl':
#                 return t # Do not prepare the supernodes since nvlink requires common nodes only

        if not (pvrvalue in p8_reduced_pvr_list or\
           pvrvalue in p8_pvr_list): # P9
           if (unit_names[unit]) == 'ntl': 
                    unit_count = 1 # One unit node/super node is created per common event node for nvlink

	# then print the data per iteration (of the unit)
        print 'unit: {} count: {}'.format(unit_names[unit], unit_count)

        if unit_count > 1: # need to split the unit's data uniformly
                event_prefix_all = event_prefix
                if unit_prefixes[unit] == "NODEF":
                 if pvrvalue in p8_reduced_pvr_list or\
                   pvrvalue in p8_pvr_list:
                    events_per_iteration = len(events) / unit_count
                 else: # P9
                  if unit_names[unit] != "ntl":
                    events_per_iteration = len(events) / unit_count # mcs, mba, capp, nx, xlink, phb
                  else:
                    events_per_iteration = len(events) # ntl

		print 'events_per_iteration: {}'.format(events_per_iteration)
                print('unit: {}, unit_count: {}'.format(unit_names[unit], unit_count))
                i = 0
                while i < unit_count:
                        print('iteration count: {}'.format(i))
                        events_single = events[i*events_per_iteration:(i*events_per_iteration)+events_per_iteration] # split the events per iteration within the unit
			print 'events_single: {}'.format(events_single)
                        if not (pvrvalue in p8_reduced_pvr_list or\
                                pvrvalue in p8_pvr_list):
                              if (unit_names[unit] == 'xlink_in') or\
                                 (unit_names[unit] == 'xlink_out'): # Xlink
                                 event_prefix_xlink = event_prefix_all
                                 event_prefix = event_prefix_xlink[i]
                              elif unit_names[unit] == 'mcs':
                                 event_prefix_mcs = event_prefix_all
                                 event_prefix = event_prefix_mcs[i]
                              elif unit_names[unit] == 'capp':
                                 event_prefix_capp = event_prefix_all
                                 event_prefix = event_prefix_capp[i]
                              elif unit_names[unit] == 'ntl':
                                 event_prefix = i # pass just the index
                           # for MBA, and PHB the event_prefix is generated inside dt_unit_single2()
                       
                        print('event_prefix: {}'.format(event_prefix))
                        t += dt_unit_single2(tabs, unit, events_single, compat, unit_names, unit_indices, unit_prefix, unit_count, unit_prefixes, event_prefix);
                        unit_indices[unit] = unit_indices[unit] + 1
                        i = i + 1
        else: # only one unit of this type. P9: NX, PB
                if unit_names[unit] == 'xlink_in': # Since the same array is used for both xlink_in (single unit) and xlink_out (2 units)
                  event_prefix_all = event_prefix # array
                  event_prefix = event_prefix_all[0]
                t += dt_unit_single2(tabs, unit, events, compat, unit_names, unit_indices, unit_prefix, unit_count, unit_prefixes, event_prefix)
                unit_indices[unit] = unit_indices[unit] + 1

        return t

def dt_unit(tabs, unit, events, compat, nest_unit_names, nest_unit_indices, nest_unit_count, nest_unit_prefixes): # In case there are multiple nodes of one type
	i = 0
	t = ""
	print 'unit: {} count: {}'.format(nest_unit_names[unit], nest_unit_count)

        # First print the common data for the unit
        [unit_common_string, event_prefix, unit_prefix] = dt_unit_common(tabs, unit, events, compat, \
                                nest_unit_names, nest_unit_indices, nest_unit_count, nest_unit_prefixes);

        t += unit_common_string;

        unit_prefix = nest_unit_names[unit].upper();
        unit_prefix = "NEST_" + unit_prefix;

#	if nest_unit_names[unit] == "mcs": # 4 mcs nodes
	if nest_unit_count > 1: # need to split the unit's data uniformly
		events_per_iteration =len(events) / nest_unit_count
		print 'events_per_iteration: {}'.format(events_per_iteration) # debug

		while i < nest_unit_count:
#			Assuming dt_unit() runs only for a P8 PVR
			if nest_unit_names[unit] == 'mcs':
				events_single = [events[i]] # Offsets for all 4 mcs units are available in the 1st 4 events itself. 'List'ify the single event
			else:
				events_single = events[i*events_per_iteration:(i*events_per_iteration)+events_per_iteration] # split the events per iteration within the unit
			print 'unit: {}'.format(unit) # debug
			t += dt_unit_single(tabs, unit, events_single, compat, nest_unit_names, unit_prefix, nest_unit_indices, nest_unit_prefixes) # added unit_prefix
			nest_unit_indices[unit] = nest_unit_indices[unit] + 1
			i = i + 1
	else:
		t += dt_unit_single(tabs, unit, events, compat, nest_unit_names, unit_prefix, nest_unit_indices, nest_unit_prefixes)
		nest_unit_indices[unit] = nest_unit_indices[unit] + 1

	return t

# get the upper and lower (common node) prefixes as well as the event prefix
# An ordered group of NVLink events gets passed in, mapping each of the nvlink units.
# Therefore, only the corresponding upper and lower prefixes need to be prepared.
def dt_unit_get_prefix_P9_NVlink(events):
        prefix_upper=''
        prefix_lower=''
	nv_index_done = []

	for i in range(0, len(events)):
	    if 'NTL' in event_domain_1[events[i]][0]:
		nvlink_index = event_domain_1[events[i]][0].strip('PM_').split('_')[0].strip('NTL')
		if (nvlink_index in nv_index_done):
		      continue
		prefix_upper = 'NVLINK' + nvlink_index
		prefix_lower = 'nvlink' + nvlink_index
		nv_index_done.append(nvlink_index)

        return (prefix_upper, prefix_lower)

def dt_unit_get_prefix_P9_xlink(events):
	prefix_upper = ''
	prefix_lower = ''
        event_prefix = ''
        xlink0 = False # No xlink0 event processed yet
        xlink1 = False
        xlink2 = False
        event_prefix_xl = []

        print('in dt_unit_get_prefix_P9_xlink: events: '%(events))
	for i in range(0, len(events)):
            event = event_domain_1[events[i]][0]
	    if 'XLINK1' in event or \
			 'XLINK2' in event or\
                          'XLINK0' in event:
                if 'XLINK1' in event and xlink1 == False or\
                  'XLINK2' in event and xlink2 == False or\
                  'XLINK0' in event and xlink0 == False:
		 prefix_upper = 'XLINK_OUT'
		 prefix_lower = 'xlink-out'
                 if 'XLINK1' in event:
                  event_prefix = 'PM_XLINK1_'
                  event_prefix_xl.append(event_prefix)
                  xlink1 = True
                 if 'XLINK2' in event:
                  event_prefix = 'PM_XLINK2_'
                  event_prefix_xl.append(event_prefix)
                  xlink2 = True
                 if 'XLINK0' in event:
                  event_prefix = 'PM_XLINK0_'
                  event_prefix_xl.append(event_prefix)
                  xlink0 = True
#	If XLINK0 becomes part of XLINK_IN, uncomment
#	the lines below, and remove the XLINK0 if cases (2) above
#	as well as the event_prefix setting for XLINK0 above.

#	    elif 'XLINK0' in event and xlink0 == False:
#		prefix_upper = 'XLINK_IN'
#		prefix_lower = 'xlink-in'
#               event_prefix = 'PM_XLINK0_'
#               event_prefix_xl.append(event_prefix)
#               xlink0 = True
        return (prefix_upper, prefix_lower, event_prefix_xl)

# print the node with the common set of events for the unit
# If P9 and NVLink, then this routine is called once for each nvlink unit
def dt_unit_common(tabs, unit, events, compat, nest_unit_names, nest_unit_indices, nest_unit_count, nest_unit_prefixes):
	global pvrvalue
	global p8_pvr_list, p8_reduced_pvr_list, p9_pvr_list
	
	if (unit <= -1): # For core and thread
		prefix = "CORE_THREAD";
		prefix2 = "core-thread-events";
	else:
                if pvrvalue in p8_reduced_pvr_list or\
                   pvrvalue in p8_pvr_list:
                  prefix = nest_unit_names[unit].upper() 
		  prefix = "NEST_" + prefix;
	
		  prefix2= "nest-" + nest_unit_names[unit] + "-events";
                else: #P9
                  if (nest_unit_names[unit] == 'ntl'): # NVLink
                   (prefix_upper_nv, prefix_lower_nv) = dt_unit_get_prefix_P9_NVlink(events)
                   prefix = "NEST_" + prefix_upper_nv
                   prefix2 = "nest-" + prefix_lower_nv + "-events"
                  elif (nest_unit_names[unit] == 'xlink_out' or\
                       nest_unit_names[unit] == 'xlink_in'): # Xlink
                   (prefix_upper_xl, prefix_lower_xl, event_prefix_xl) = \
                          dt_unit_get_prefix_P9_xlink(events)
                   prefix = "NEST_" + prefix_upper_xl
                   prefix2 = "nest-" + prefix_lower_xl + "-events"
                  else: # all other units
                   prefix = nest_unit_names[unit].upper() 
		   prefix = "NEST_" + prefix;
	
		   prefix2= "nest-" + nest_unit_names[unit] + "-events";
    
        unit_prefix = prefix # Return this so it can be reused. E.g. NEST_XLINK_OUT
                     
#       prefix and prefix2 above are for the common node
#       e.g. prefix: NEST_XLINK_IN, prefix2: nest-xlink-in-events

        s = ""
	s += '\t' * tabs +'%s: %s {\n'% (prefix, prefix2)
        tabs += 1
        tabs += 1
        s += '\t' * tabs + "#address-cells = <0x1>;\n"
        s += '\t' * tabs + "#size-cells = <0x1>;\n\n"

	event_processed_count = 0
	event_prefix = "";
	# Need a prefix assigned for all units, regardless of whether they are repeatable
	# or otherwise
	if unit <= -1: # core / thread
		event_prefix = "CPM_";	
					
	else:
#	 Fix event prefix directly if it is specified, else construct.
         print('unit: {}'.format(unit))
	 if nest_unit_prefixes[unit] == "NODEF":
                if pvrvalue in p8_reduced_pvr_list or\
                   pvrvalue in p8_pvr_list:
		    events_per_iteration = len(events) / nest_unit_count
                else: # P9
                  if nest_unit_names[unit] != "ntl":
                    events_per_iteration = len(events) / nest_unit_count # mcs, mba, capp, nx, xlink
                    print('unit: {}, event count: {}, events_per_iteration: {}'.format(nest_unit_names[unit], len(events), events_per_iteration))
                  else:
                    events_per_iteration = len(events) # ntl. Complete list of grouped events to be consumed

		# Prepare prefix using the nest unit name since no prefix exists.
		# In P8, the event reads as PM_MCS_..UP/DOWN_128B_DATA_XFER_MC0/1/2/3
		# But the DTS needs to read them as PM_MCS0/1/2/3_UP/DOWN_128B_DATA_XFER
		if pvrvalue in p8_reduced_pvr_list or\
			pvrvalue in p8_pvr_list:
			event_prefix = "PM_" + nest_unit_names[unit].upper() +\
					"_";
		else:
                     print('nest_unit: {}'.format(nest_unit_names[unit]))
                     if nest_unit_names[unit] != 'xlink_in' and\
                         nest_unit_names[unit] != 'xlink_out' and\
                         nest_unit_names[unit] != 'ntl': # prefixes identified
                        if nest_unit_names[unit] == 'mcs':
                         event_prefix_mcs = ['PM_MCS01_', 'PM_MCS23_']
                        elif nest_unit_names[unit] == 'capp':
                         event_prefix_capp = ['PM_CAPP1_', 'PM_CAPP2_']
                        else:  # MBA, PHB
			 event_prefix = "PM_" + nest_unit_names[unit].upper() +\
				str(nest_unit_indices[unit]) + "_";
	 else: # For P9: NX, PowerBus
		events_per_iteration = len(events)
		event_prefix = nest_unit_prefixes[unit]

	 print 'unit: {} events: {}'.format(unit, events)

#	For core / thread, must find the starting (lowest) offset first since
#	the event list is not in ascending offset order. Same for P9/NEST
#       However, find the starting offset only from one unit's events if the 
#       unit name covers multiple units (e.g. mcs)

	if (unit <= -1) or\
                not (pvrvalue in p8_reduced_pvr_list or\
                   pvrvalue in p8_pvr_list):
		imastartoffset = 0
		for i in events:
                        if (unit <= -1):
			 event = i
                        else:
                         event = event_domain_1[i]

			if event_processed_count == 0:
				imastartoffset = event[1]

                        # for P9/NEST break if we processed events from 1 iteration
			if ((unit > -1) and (event_processed_count == events_per_iteration)):
				break;

			if event[1] < imastartoffset:
				imastartoffset = event[1]
			event_processed_count = event_processed_count + 1

 
		event_processed_count = 0
		
#	Run the main loop (for core / thread/ NEST)
	for i in events:
                print('main loop. i: {}'.format(i))
		if (unit <= -1): # core / thread
		 event = i
		else:
		 event = event_domain_1[i]
                print('main loop. event: {}'.format(event))

		print 'event: [0]: {}, [1]: {}, [2]: {}'.format(event[0],event[1],event[2])
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
		
#		Set the ima start offset only for NEST if P8
   		if (unit > -1) and \
                 (pvrvalue in p8_reduced_pvr_list or\
                   pvrvalue in p8_pvr_list):
			if event_processed_count == 0:
				imastartoffset = event[1];
				print 'imastartoffset: {}'.format(imastartoffset)

                if nest_unit_names[unit] == 'ntl': # nvlink
                   offset = event[1]
                else:
		   offset = event[1] - imastartoffset;
		print 'event: {} offset: {}'.format(event[0],offset)
 
		nodename = "event"
		if nest_unit_names[unit] == 'mcs': # Setting event unit and scale to 'N/A'
						   # for unit 'MCS' as it is covered already
			event_unit = 'N/A'
			event_scale = 'N/A'
		else:
			event_unit = ''
			event_scale = ''

		if (event[0] != 'RESERVED'):
			if pvrvalue in p8_reduced_pvr_list or\
				pvrvalue in p8_pvr_list:
#			skip _LAST_SAMPLE events in P8 catalog
				if ((unit > -1) and ("_LAST_SAMPLE" in event[0])):
					continue;	
                        else: # P9
                           if  nest_unit_names[unit] == 'mcs':
                             for i in range(0,len(event_prefix_mcs)):
                                  if (event_prefix_mcs[i] in event[0]):
                                          event_prefix = event_prefix_mcs[i]
                                          break
                           elif nest_unit_names[unit] == 'xlink_in' or\
                                nest_unit_names[unit] == 'xlink_out':
                             for i in range(0,len(event_prefix_xl)):
                                  if (event_prefix_xl[i] in event[0]):
                                          event_prefix = event_prefix_xl[i]
                                          break
                           elif nest_unit_names[unit] == 'capp':
                             for i in range(0,len(event_prefix_capp)):
                                  if (event_prefix_capp[i] in event[0]):
                                          event_prefix = event_prefix_capp[i]
                                          break
                           elif nest_unit_names[unit] == 'ntl': # nvlink
                             event_prefix = '' # no event_prefix for nvlink events
                      
			print 'calling dt_event2 on event: {}'.format(event[0]);
			s += dt_event2((tabs), event[0], offset, 8, event_unit,\
			      event_scale, event[2], nodename, event_prefix)

		if event[0] == 'PM_XLINK_CYCLES':
			xlink_cyc_event_added = True
		if event[0] == 'PM_XLINK_CYCLES_LAST_SAMPLE':
			xlink_cyc_last_sample_event_added = True
		if event[0] == 'PM_ALINK_CYCLES':
			alink_cyc_event_added = True
		if event[0] == 'PM_ALINK_CYCLES_LAST_SAMPLE':
			alink_cyc_last_sample_event_added = True

		event_processed_count = event_processed_count + 1;

#		For P8, process at least 3 sets of events so that we get to the UP_
#		and the DOWN_ events
		if pvrvalue in p8_reduced_pvr_list or\
			pvrvalue in p8_pvr_list:
			if ((unit > -1) and (event_processed_count ==\
						events_per_iteration*3)):
				break;
		else:
#		for NEST units, process as many events as there are for 1 iteration
#		Applies to P9 only.
			if ((unit > -1) and (event_processed_count == events_per_iteration)):
				break;
	s += '\t' * (tabs-1) + "};\n"

        if not (pvrvalue in p8_reduced_pvr_list or\
                       pvrvalue in p8_pvr_list):
		if nest_unit_names[unit] == 'mcs':
		  event_prefix = event_prefix_mcs
		elif nest_unit_names[unit] == 'xlink_in' or\
		     nest_unit_names[unit] == 'xlink_out':
		  event_prefix = event_prefix_xl
		elif nest_unit_names[unit] == 'capp':
		  event_prefix = event_prefix_capp
		elif nest_unit_names[unit] == 'ntl': # nvlink
		  event_prefix = '' # no event_prefix for nvlink events

	return [s, event_prefix, unit_prefix];

def dt_unit_single2(tabs, unit, events, compat, nest_unit_names, nest_unit_indices, unit_prefix\
#				, unitcount, nest_unit_prefixes):
				, unitcount, nest_unit_prefixes, event_prefix):
	xlink_cyc_event_added = False
	xlink_cyc_last_sample_event_added = False
	alink_cyc_event_added = False
	alink_cyc_last_sample_event_added = False

	global nest_offset_P9,nest_size_P9
	global core_thread_size_P9
	global type_chip_P9,type_core_P9,type_thread_P9

        print('dt_unit_single2: unit: %d' %(unit))

	if unit <= -1:
		event_prefix = unit_prefix
		unit_prefix = "CORE_THREAD"
	else:
                if not (pvrvalue in p8_reduced_pvr_list or\
                        pvrvalue in p8_pvr_list):
                     if (nest_unit_names[unit] == 'mba'\
                         or nest_unit_names[unit] == 'phb'):
                        # Construct the event_prefix for MBA, PHB based on nest_unit_indices
                         event_prefix = "PM_" + nest_unit_names[unit].upper() +\
                                str(nest_unit_indices[unit]) + "_";
                     elif (nest_unit_names[unit] == 'ntl'):
                          event_prefix = "" # No event prefix since we have a dummy supernode /unit node for nvlink 

                else:
		 if nest_unit_prefixes[unit] == "NODEF":
			event_prefix = nest_unit_names[unit].upper();
			event_prefix = "PM_" + event_prefix + str(nest_unit_indices[unit])\
				 + "_";
		 else:
			event_prefix = nest_unit_prefixes[unit]

	s = ""
        tabs += 1
	if (unit == -1):
		s += '\t' * tabs +'%s {\n'% ("core")
	elif (unit == -2):
		s += '\t' * tabs +'%s {\n'% ("thread")
	else:
		# Mark only 'nx' unit as 'nx' instead of 'nx0'
		if (nest_unit_names[unit] == 'nx'):	
			s += '\t' * tabs +'%s {\n'% (nest_unit_names[unit])
                else:
                 if not (pvrvalue in p8_reduced_pvr_list or\
                        pvrvalue in p8_pvr_list): # P9
                   if (nest_unit_names[unit] == 'mcs'):
                        index = event_prefix.strip('PM_MCS').rstrip('_')
                        name = nest_unit_names[unit]
                   elif (nest_unit_names[unit] == 'xlink_in') or\
                        (nest_unit_names[unit] == 'xlink_out'):
                        index = event_prefix.strip('PM_XLINK').rstrip('_')
                        name = nest_unit_names[unit].split('_')[0] # xlink instead of xlink_in/_out
                   elif (nest_unit_names[unit] == 'ntl'):
                         tmp = unit_prefix.split('_')[1].lower() # Convert NEST_NVLINK3 to nvlink3
                         name = 'nvlink'
                         index = tmp.split(name)[1]  # E.g. nvlink3 -> index=3, name=nvlink
                   elif (nest_unit_names[unit] == 'capp'):
                        index = (int)(event_prefix.strip('PM_CAPP').rstrip('_')) - 1
                        name = nest_unit_names[unit]
                   elif (nest_unit_names[unit] == 'mba' or nest_unit_names[unit] == 'phb'\
                                 or nest_unit_names[unit] == 'powerbus'):
                        index = nest_unit_indices[unit]
                        name = nest_unit_names[unit]
                  
                   print('index: {}'.format(index)) 
                   if (nest_unit_names[unit] == 'mcs'):
                        print('unit: {}, index: {}'.format(nest_unit_names[unit], index))
		   s += '\t' * tabs +'%s%s {\n'% (name, str(index)) # To accomodate mcs '01'
                 else:
		   s += '\t' * tabs +'%s%d {\n'% (nest_unit_names[unit], nest_unit_indices[unit])
	tabs += 1
	s += '\t' * tabs + "compatible = \"%s\";\n"%compat
	s += '\t' * tabs + "events-prefix = \"%s\";\n"%event_prefix
        event_scale = ''
        event_unit = ''

	if unit == -1:
		event_scale = core_imc_scale
	elif unit == -2:
		event_scale = thread_imc_scale
        else: # NEST
                event_scale = nest_unit_scale_P9[unit] # different scale values per unit type

#       Print the event_scale for all.
	if (event_unit != ''):
		s += '\t' * tabs + "unit = \"%s\";\n"%event_unit
	if (event_scale != ''):
		s += '\t' * tabs + "scale = \"%s\";\n"%event_scale

#	Need the minimum starting offset in case of core / thread
        if (unit <= -1) or\
         not (pvrvalue in p8_reduced_pvr_list or\
                        pvrvalue in p8_pvr_list): # P9 and NEST
                imastartoffset = 0
		event_processed_count = 0
                for i in events:
                        if (unit <= -1):
                         event = i
                        else:
                         if nest_unit_names[unit] == 'ntl': # for NVLink, imastartoffset = 0
                            break
                         event = event_domain_1[i]

                        if event_processed_count == 0:
                                imastartoffset = event[1]
#                       MCS node can not have *PB_CYC* event
                        if nest_unit_names[unit] == 'mcs' and (event[0]=='PM_PB_CYC'\
                          or event[0]=='PM_PB_CYC2'):
                          print('skipping event {} for unit {}'.format(event[0], nest_unit_names[unit]))
                          event_processed_count = event_processed_count + 1
                          continue
                        if nest_unit_names[unit] == 'phb':
                           print('event: {}, start offset: {}'.format(event[0], event[1]))
                        if event[1] < imastartoffset:
                                imastartoffset = event[1]
                        if nest_unit_names[unit] == 'phb':
                           print('imastartoffset set to: {}'.format(imastartoffset))
                        event_processed_count = event_processed_count + 1
                event_processed_count = 0

	if (unit <= -1):
#		event = event_domain_2[i]
		s += '\t' * tabs + "reg = <0x%x 0x8>;\n"%imastartoffset
		s += '\t' * tabs + "events = < &%s >;\n"%unit_prefix
		if (unit == -1):
			s += '\t' * tabs + "type = <0x%x>;\n"%type_core_P9
		else:
			s += '\t' * tabs + "type = <0x%x>;\n"%type_thread_P9
		s += '\t' * tabs + "size = <0x%x>;\n"%core_thread_size_P9
	else:
	 for i in events:
		event = event_domain_1[i]
		print 'event: [0]: {}, [1]: {}, [2]: {}'.format(event[0],event[1],event[2])
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
		nodename = "event"
		if nest_unit_names[unit] == 'mcs': # Setting event unit and scale to 'N/A'
						   # for unit 'MCS' as it is covered already
			event_unit = 'N/A'
			event_scale = 'N/A'

		if event[0] == 'PM_XLINK_CYCLES':
			xlink_cyc_event_added = True
		if event[0] == 'PM_XLINK_CYCLES_LAST_SAMPLE':
			xlink_cyc_last_sample_event_added = True
		if event[0] == 'PM_ALINK_CYCLES':
			alink_cyc_event_added = True
		if event[0] == 'PM_ALINK_CYCLES_LAST_SAMPLE':
			alink_cyc_last_sample_event_added = True

#		Do not include 'RESERVED' events. Look for the first non-'RESERVED' event
#		and use its offset to write the node.
		if (event[0] != 'RESERVED'):
                        if not (pvrvalue in p8_reduced_pvr_list or\
                        pvrvalue in p8_pvr_list): # P9 and NEST
			 s += '\t' * tabs + "reg = <0x%x 0x8>;\n"%imastartoffset
                        else: 
			 s += '\t' * tabs + "reg = <0x%x 0x8>;\n"%event[1]
			s += '\t' * tabs + "events = < &%s >;\n"%unit_prefix
			s += '\t' * tabs + "type = <0x%x>;\n"%type_chip_P9
			s += '\t' * tabs + "size = <0x%x>;\n"%nest_size_P9
			s += '\t' * tabs + "offset = <0x%x>;\n"%nest_offset_P9
			s += '\t' * tabs + "cb_offset = <0x%x>;\n"%cb_nest_offset_P9
			break;

	tabs -= 1;
#	s += '\t' * (tabs-1) + "};\n"
	s += '\t' * (tabs) + "};\n"
	return s


# This routine prints out the events and data per unit in the following format
# <--------------- start of sample format ------------------>
#        mcs3 {
#                compatible = "ibm,imc-counters-nest";
#                ranges;
#                #address-cells = <0x1>;
#                #size-cells = <0x1>;
#                unit = "MiB";
#                scale = "1.2207e-4";
#
#                event@298 {
#                        event-name = "PM_MCS3_RRTO_QFULL_NO_DISP" ;
#                        reg = <0x298 0x8>;
#                        desc = "RRTO not dispatched in MCS3 due to capacity - pulses once for each time a valid RRTO op is not dispatched due to a command list full condition" ;
#                };
# <-------------- end of sample format -------------------->

def dt_unit_single(tabs,unit,events, compat, nest_unit_names, unit_prefix, nest_unit_indices, nest_unit_prefixes): # Print one single unit at a time (e.g. MCS0)
	xlink_cyc_event_added = False
	xlink_cyc_last_sample_event_added = False
	alink_cyc_event_added = False
	alink_cyc_last_sample_event_added = False

        if unit <= -1:
                event_prefix = unit_prefix
                unit_prefix = "CORE_THREAD"
        else:
                if nest_unit_prefixes[unit] == "NODEF":
                        event_prefix = nest_unit_names[unit].upper();
                        event_prefix = "PM_" + event_prefix + str(nest_unit_indices[unit])\
                                 + "_";
                else:
                        event_prefix = nest_unit_prefixes[unit]

        s = ""
        tabs += 1
        if (unit == -1):
                s += '\t' * tabs +'%s {\n'% ("core")
        elif (unit == -2):
                s += '\t' * tabs +'%s {\n'% ("thread")
        else:
                # Mark only 'nx' unit as 'nx' instead of 'nx0'
                if (nest_unit_names[unit] == 'nx'):
                        s += '\t' * tabs +'%s {\n'% (nest_unit_names[unit])
                else:
                        s += '\t' * tabs +'%s%d {\n'% (nest_unit_names[unit], nest_unit_indices[unit])
        tabs += 1
        s += '\t' * tabs + "compatible = \"%s\";\n"%compat
        s += '\t' * tabs + "events-prefix = \"%s\";\n"%event_prefix

        event_scale = ''
        event_unit = ''

	if unit == -1:
		event_scale = core_imc_scale
	elif unit == -2:
		event_scale = thread_imc_scale

	if ((unit == -1) or (unit == -2)): # Print a common unit and scale only if core or thread
		if (event_unit != ''):
			s += '\t' * tabs + "unit = \"%s\";\n"%event_unit
		if (event_scale != ''):
			s += '\t' * tabs + "scale = \"%s\";\n"%event_scale

#       Need the minimum starting offset in case of core / thread
        if (unit <= -1):
                imastartoffset = 0
                event_processed_count = 0
                for i in events:
                        event = i
                        if event_processed_count == 0:
                                imastartoffset = event[1]
                        if event[1] < imastartoffset:
                                imastartoffset = event[1]
                        event_processed_count = event_processed_count + 1
                event_processed_count = 0

        if (unit <= -1):
                s += '\t' * tabs + "reg = <0x%x 0x8>;\n"%imastartoffset
                s += '\t' * tabs + "events = < &%s >;\n"%unit_prefix
                if (unit == -1):
                        s += '\t' * tabs + "type = <0x%x>;\n"%type_core
                else:
                        s += '\t' * tabs + "type = <0x%x>;\n"%type_thread
                s += '\t' * tabs + "size = <0x%x>;\n"%core_thread_size
        else:
	  for i in events:
		event = event_domain_1[i]
		print 'event: [0]: {}, [1]: {}, [2]: {}'.format(event[0],event[1],event[2])
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
		nodename = "event"
		if nest_unit_names[unit] == 'mcs': # Setting event unit and scale to 'N/A'
						   # for unit 'MCS' as it is covered already
			event_unit = 'N/A'
			event_scale = 'N/A'

		if event[0] == 'PM_XLINK_CYCLES':
			xlink_cyc_event_added = True
		if event[0] == 'PM_XLINK_CYCLES_LAST_SAMPLE':
			xlink_cyc_last_sample_event_added = True
		if event[0] == 'PM_ALINK_CYCLES':
			alink_cyc_event_added = True
		if event[0] == 'PM_ALINK_CYCLES_LAST_SAMPLE':
			alink_cyc_last_sample_event_added = True

#		Do not include 'RESERVED' events
		if (event[0] != 'RESERVED'):
                        s += '\t' * tabs + "reg = <0x%x 0x8>;\n"%event[1]
                        s += '\t' * tabs + "events = < &%s >;\n"%unit_prefix
                        s += '\t' * tabs + "type = <0x%x>;\n"%type_chip
                        s += '\t' * tabs + "size = <0x%x>;\n"%nest_size
                        s += '\t' * tabs + "offset = <0x%x>;\n"%nest_offset
                        s += '\t' * tabs + "cb_offset = <0x%x>;\n"%cb_nest_offset
			print 'added data for event: {}'.format(event[0])
                        break;

#	Assuming for P8 we do not need to reduce the tabs count
	s += '\t' * (tabs-1) + "};\n"
	return s

def core_imc_dt_unit(tabs, events):
        s = ""
	groupname = "core"
        s += '\t' * tabs + '%s {\n' % (groupname)
        tabs +=1
        s += '\t' * tabs + "compatible = \"%s\";\n" % "ibm,imc-counters-core"
        s += '\t' * tabs + "ranges;\n"
        s += '\t' * tabs + "#address-cells = <0x1>;\n"
        s += '\t' * tabs + "#size-cells = <0x1>;\n"
        s += '\t' * tabs + "scale = \"%s\";\n\n"%core_imc_scale

	event_count = 0
        for i in events:
		nodename = "event"
		# core_imc_scale is added in the parent node itself. So not adding in the event nodes
		# Do not print 'RESERVED' events
		if (i[0] != 'RESERVED'):
                	s += dt_event(tabs, i[0], i[1], 8, '', '', i[2], nodename)
			event_count = event_count + 1
                	s += "\n"
        s += '\t' * (tabs - 1) + "};\n"
        return s

# Print the common node for core and thread
def core_thread_imc_dt_unit2_common(tabs, unit, events, compat, unit_names, unit_indices, unit_count, unit_prefixes):
	# First print the common data for the unit
	[unit_common_string, event_prefix, unit_prefix] = dt_unit_common(tabs, unit, events, compat, \
				unit_names, unit_indices, unit_count, unit_prefixes);

	# event_prefix is set to 'CPM_' once dt_unit_common() returns.
	return [unit_common_string, event_prefix]

# Print the core-specific unit only
def core_imc_dt_unit2(tabs, unit, events, compat, unit_names, unit_indices, unit_prefix, unit_count, unit_prefixes):
        s = ""
        event_prefix = '' # dummy. This is used within dt_unit2() 
        s += dt_unit_single2(tabs, unit, events, compat, unit_names, unit_indices, unit_prefix, unit_count, unit_prefixes, event_prefix)

        return s

def thread_imc_dt_unit2(tabs, unit, events, compat, unit_names, unit_indices, unit_prefix, unit_count, unit_prefixes):
	s = ""
        event_prefix = '' # dummy. This is used within dt_unit2()
        s += dt_unit_single2(tabs, unit, events, compat, unit_names, unit_indices, unit_prefix, unit_count, unit_prefixes, event_prefix)

        return s

def thread_imc_dt_unit(tabs, events):
        s = ""
	groupname = "thread"
        s += '\t' * tabs + '%s {\n' % (groupname)
        tabs +=1
        s += '\t' * tabs + "compatible = \"%s\";\n" % "ibm,imc-counters-thread"
        s += '\t' * tabs + "ranges;\n"
        s += '\t' * tabs + "#address-cells = <0x1>;\n"
        s += '\t' * tabs + "#size-cells = <0x1>;\n"
        s += '\t' * tabs + "scale = \"%s\";\n\n"%thread_imc_scale

	event_count = 0
        for i in events:
		nodename = "event"
		if (i[0] != 'RESERVED'):
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

def get_unit_count(unitname, nest_unit_names_multi, nest_unit_count_multi):
	unitcount = 1 # A minimum of 1 unit if it isnt a multi count unit

	print 'in get_unit_count. nest_unit_names_multi: {}'.format(nest_unit_names_multi)
	print 'in get_unit_count. nest_unit_count_multi: {}'.format(nest_unit_count_multi)
	print 'in get_unit_count. unitname: {}'.format(unitname)
	for k in range(len(nest_unit_names_multi)):
		print 'get_unit_count: matching {} with {}'.format(unitname, nest_unit_names_multi[k])
		if unitname == nest_unit_names_multi[k]:
			unitcount = nest_unit_count_multi[k]
			break
	return unitcount
       
def gen_dts(ifname, verbose, ofname, unitname, pvrname, threadimc, coreimc):
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
	print "pvr name was not specified. Defaulting to 4D0200.."
        pvrname = "4D0200"

 pvr_list = pvrname.split(',')
 global p8_pvr_list, p8_reduced_pvr_list, p9_pvr_list
 global pvrvalue

# Assuming we do not add P8 and P9 PVRs together.
 for pvr in pvr_list:
	pvrvalue = pvr # set the global. Used within dt_event2()
	print 'pvr: {}'.format(pvr) # debug
	if pvr in p9_pvr_list:
		nest_unit_names = nest_unit_names_P9
		nest_unit_indices = nest_unit_indices_P9
		nest_units = nest_units_P9
		nest_unit_names_multi = nest_unit_names_multi_P9
		nest_unit_count_multi = nest_unit_count_multi_P9
		nest_unit_prefixes = nest_unit_prefixes_P9
	else: # P8
		nest_unit_names = nest_unit_names_P8
		nest_unit_indices = nest_unit_indices_P8
		nest_units = nest_units_P8
		nest_unit_names_multi = nest_unit_names_multi_P8
		nest_unit_count_multi = nest_unit_count_multi_P8
		nest_unit_prefixes = nest_unit_prefixes_P8
		print 'set nest unit prefixes for P8: {}'.format(nest_unit_prefixes) #debug

 print 'nest_unit_names: {}'.format(nest_unit_names)

# the page0 catalog is 128 bytes long
 page0 = Page0(fn.read(128))
 Events(fn, page0.get_events_start(), page0.get_events_count())
# Need to pass the nest_unit information as it is set in the scope of gen_dts()

 Groups(fn, page0.get_group_start(), page0.get_group_count(), nest_units)

 print 'version from LID: {}'.format(hex(int(page0.get_pvr_and_version()) & 0xFFFF))
 LID_version = hex(int(page0.get_pvr_and_version()) & 0xFFFF)
 LID_version = LID_version.rstrip('LX') # strip out the trailing 'L'

 s =\
"""
/dts-v1/;

/ {
\tname = "";
\tcompatible = \"ibm,opal-in-memory-counters\";
\t#address-cells = <0x1>;
\t#size-cells = <0x1>;
"""
# Per latest change, nest-offset and nest-size should be in each unit's node (22-may)
# if pvr_list[0] in p9_pvr_list: # change the nest offset and size based on PVR (P9/P8)
#  s += \
#"""
#\timc-nest-offset = <0x180000>;
#\timc-nest-size = <0x40000>;
#"""
# else:
#  s += \
#"""
#\timc-nest-offset = <0x320000>;
#\timc-nest-size = <0x30000>;
#"""
# End change (22-may)

 s += "\tversion-id = <{}>;\n\n".format(LID_version)
 for pvr in pvr_list:
        pvr_str = '\tpvr@' + pvr + ' {'
	if pvr in p9_pvr_list:
         pvr_node =\
"""
\t\t#address-cells = <0x1>;
\t\t#size-cells = <0x1>;
\t\timc-nest-offset = <0x180000>;
\t\timc-nest-size = <0x40000>;
\t\tversion-id = \"\";
"""
	else:
         pvr_node =\
"""
\t\t#address-cells = <0x1>;
\t\t#size-cells = <0x1>;
\t\timc-nest-offset = <0x320000>;
\t\timc-nest-size = <0x80000>;
\t\tversion-id = \"\";
"""
        tabs = 0

        if pvr not in p9_pvr_list: # Handle P8 differently
         for i in range(len(nest_units)):
                if unitname != 'all' and unitname != '': # specific unit indicated. Print that unit only
                  if nest_unit_names[i] == unitname:
                        if i < len(nest_unit_names):
                                if (len(group_chip[i])): # are there events associated with the unit?
					unitcount = get_unit_count(unitname, nest_unit_names_multi, nest_unit_count_multi)
                                        s += dt_unit(tabs,i,group_chip[i], "ibm,imc-counters", nest_unit_names, nest_unit_indices, unitcount, nest_unit_prefixes)
                        break
                elif unitname == 'all': # Include all NEST units
                        if i < len(nest_unit_names):
                                if (len(group_chip[i])):
					unitcount = get_unit_count(nest_unit_names[i], nest_unit_names_multi, nest_unit_count_multi)
                                        s += dt_unit(tabs,i,group_chip[i], "ibm,imc-counters", nest_unit_names, nest_unit_indices, unitcount, nest_unit_prefixes)
                else: # no unit name was explicitly specified. Assume 'mcs' if pvrname is 4D0200
                 if pvrname in p8_reduced_pvr_list: # 4D0200 only
                  if nest_unit_names[i] == 'mcs':
                        if i < len(nest_unit_names):
                                if (len(group_chip[i])):
					unitcount = get_unit_count(nest_unit_names[i], nest_unit_names_multi, nest_unit_count_multi)
                                        s += dt_unit(tabs,i,group_chip[i], "ibm,imc-counters", nest_unit_names, nest_unit_indices, unitcount, nest_unit_prefixes)
                        break
                 else: # pvrname is not 4D0200. Print all NEST units
                        if i < len(nest_unit_names):
                                if (len(group_chip[i])):
					unitcount = get_unit_count(nest_unit_names[i], nest_unit_names_multi, nest_unit_count_multi)
                                        s += dt_unit(tabs,i,group_chip[i], "ibm,imc-counters", nest_unit_names, nest_unit_indices, unitcount, nest_unit_prefixes)
        else: # for P9 DD1 (4E0100) print core and thread imc by default. Add the supported NEST units too.
                coreimc = "yes"
                threadimc = "yes"
                nvlink_P9 = {}

		for i in range(len(nest_unit_names_supported_P9)):
                 print('len(nest_units): {}'.format(len(nest_units)))
         	 for j in range(len(nest_units)):
		  print 'matching : {} with {}'.format(nest_unit_names_supported_P9[i],nest_unit_names[j])
		  if nest_unit_names[j] == nest_unit_names_supported_P9[i]:
                      if j < len(nest_unit_names):
                              if (len(group_chip[j])): # There are events associated with this unit
				      print 'group_chip: {}'.format(group_chip[j])
                                      if (nest_unit_names[j] == 'ntl'): # nvlink. Group them per unit
                                       nvlink_P9 = dt_group_nvlink_events_P9(group_chip[j])
				       unitcount = len(nvlink_P9)
                                       for k,v in nvlink_P9.items(): # call it once per nvlink unit
                                        s += dt_unit2(tabs, j, v, "ibm,imc-counters", nest_unit_names, nest_unit_indices, unitcount, nest_unit_prefixes)
				      else:
                                       unitcount = get_unit_count(nest_unit_names[j], nest_unit_names_multi, nest_unit_count_multi)
				       print 'writing out unit for {}'.format(nest_unit_names[j]);
                                       s += dt_unit2(tabs,j,group_chip[j], "ibm,imc-counters", nest_unit_names, nest_unit_indices, unitcount, nest_unit_prefixes)
                      break

        if coreimc == "yes":
		[common_string, unit_prefix] = core_thread_imc_dt_unit2_common(tabs, -1, event_domain_2, "ibm,imc-counters", nest_unit_names, nest_unit_indices, 1, nest_unit_prefixes)
		s += common_string
                s += core_imc_dt_unit2(tabs, -1, event_domain_2, "ibm,imc-counters", nest_unit_names, nest_unit_indices, unit_prefix, 1, nest_unit_prefixes) # last 4 fields unused
        if threadimc == "yes":
		if coreimc != "yes":
			[common_string, unit_prefix] = core_thread_imc_dt_unit2_common(tabs, -2, event_domain_2_a, "ibm,imc-counters", nest_unit_names, nest_unit_indices, 1, nest_unit_prefixes)
			s += common_string
                s += thread_imc_dt_unit2(tabs, -2, event_domain_2_a, "ibm,imc-counters", nest_unit_names, nest_unit_indices, unit_prefix, 1, nest_unit_prefixes) # last 4 fields unused
 s += "};\n"

 of.write(s)
 of.close
 print 'Generated DTS file: {}'.format(ofname)

if __name__ == "__main__":
 ifname = "" # input file name
 ofname = "" # output file name
 verbose = False
 coreimc = "no" # Do not print core imc by default (if no unit was explicitly specified)
 threadimc = "no" # Do not print thread imc by default (if no unit was explicitly specified)
 pvrname = ""
 unitname = ""
 odtbfname = "" # output dtb file name

 options, remainder = getopt.getopt(sys.argv[1:], 'c:d:i:p:t:u:vo:', ['coreimc=',
							'outputdtb=',
							'input=',
							'pvr=',
							'threadimc=',
							'unit=',
							'verbose',
							'output='
							])

 for opt, arg in options:
	if opt in ('-c', '--core'):
		coreimc = arg
	elif opt in ('-i', '--input'):
		ifname = arg
	elif opt in ('-p', '--pvr'):
		pvrname = arg
	elif opt in ('-t', '--thread'):
		threadimc = arg
	elif opt in ('-u', '--unit'):
		unitname = arg
	elif opt in ('-v', '--verbose'):
		verbose = True
	elif opt in ('-o', '--output'):
		ofname = arg
	elif opt in ('-d', '--outputdtb'):
		odtbfname = arg

 gen_dts(ifname, verbose, ofname, unitname, pvrname, coreimc, threadimc)
 gen_dtb(ofname, odtbfname)

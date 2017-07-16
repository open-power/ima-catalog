#!/bin/bash
#
# Build script to create DTBs from In Memory Accumulation (IMA) Catalog repository.
#
# For a given platform, we could have multiple DTS (Device Tree Source) file.
# Build script first builds DTB (Device Tree Binary) file from DTS using dtc
# compiler. It then packs generated DTBs to one single binary file called
# "ima_catalog.bin". This "ima_catalog.bin" is what is flashed to PNOR partition.
#
# Based on "openpower/capp-ucode" build.sh script.
#

#
# #define PNOR_SUBPART_HEADER_SIZE 0x1000
# struct pnor_hostboot_toc {
# 	be32 ec;
# 	be32 offset; /* from start of header.  4K aligned */
# 	be32 size; /* */
# };
# #define PNOR_HOSTBOOT_TOC_MAX_ENTRIES ((PNOR_SUBPART_HEADER_SIZE - 8)/sizeof(struct pnor_hostboot_toc))
# struct pnor_hostboot_header {
# 	char eyecatcher[4];
# 	be32 version;
# 	struct pnor_hostboot_toc toc[PNOR_HOSTBOOT_TOC_MAX_ENTRIES];
# };

#
# Two parameters are passed to this script
# 1)Path to host-tools -- we need this for the dtc and xz commands.
# 2)Platform to build  -- We need this to pick the right DTS file.
#

declare -a ima_arr
declare -a ima_pvr
declare -a ima_file

usage () { 
	echo "Usage: $0  <Path to dtc/xz> <platform to build \"POWER8 or POWER9\">" 1>&2;
	exit 0;
}

if [ $# -le 1 ]
   then
	usage
fi

#Catalog files to pickup for a given platform
declare -a POWER8=('81E00610.4D0100.dts' '81E00610.4D0200.dts')
declare -a POWER8_PVR=(0x4d0100 0x4d0200)
declare -a POWER8_FILENAME=(0x4d0100.bin 0x4d0200.bin)

declare -a POWER9=('81E00612.4E0100.dts' '81E00612.4E0200.dts')
declare -a POWER9_PVR=(0x4e0100 0x4e0200)
declare -a POWER9_FILENAME=(0x4e0100.bin 0x4e0200.bin)

align() {
    echo $(( (($1 + ($alignment - 1))) & ~($alignment - 1) ))
}

if [ "$2" == "POWER8" ]; then
   ima_arr=("${POWER8[@]}")
   ima_pvr=("${POWER8_PVR[@]}")
   ima_file=("${POWER8_FILENAME[@]}")
elif [ "$2" == "POWER9" ]; then
   ima_arr=("${POWER9[@]}")
   ima_pvr=("${POWER9_PVR[@]}")
   ima_file=("${POWER9_FILENAME[@]}")
fi

entries=$((${#ima_arr[@]}))
debug=true
if [ -n "$DEBUG" ] ; then
    debug=echo
fi

#Generate the Device Tree Binary (DTB) files from DTS (text)
if [ $entries -gt 0 ]; then
    for i in $(seq 0 $(($entries - 1)) ) ; do
	$1/dtc -O dtb -I dts -o ${ima_file[${i}]} ${ima_arr[${i}]}
	$1/xz -9 -C crc32 ${ima_file[${i}]}
	mv ${ima_file[${i}]}.xz ${ima_file[${i}]}

	size=$( stat -c %s ${ima_file[${i}]} )
	if [ "$2" == "POWER8" ]; then
	    pad=$(( 8000 - $(($size))))
	else
	    pad=$(( 32768 - $(($size))))
	fi
	dd if=/dev/zero count=$pad bs=1 >> ${ima_file[${i}]}
    done
fi

#Create a tmp file for manipulation
TMPFILE=$(mktemp)

EYECATCHER=$(( 0x494D4143 )) # ascii 'IMAC'
VERSION=1
NUMBEROFTOCENTRIES=$entries

printf "0: %.8x" $EYECATCHER | xxd -r -g0 >> $TMPFILE
printf "0: %.8x" $VERSION | xxd -r -g0 >> $TMPFILE

sections=0
alignment=$(( 0x1000 ))
offset=$alignment


for i in $(seq 0 $(($NUMBEROFTOCENTRIES - 1 ))) ; do
    # Work out if we added this file already
    matched=0
    for s in $(seq $sections); do
        if cmp -s ${ima_file[$i]} ${sectionfile[$s]} ; then
            $debug matched ${ima_file[$i]} ${sectionfile[$s]}
            matched=1
            section=$s
            break 1
        fi
    done
    if [ $matched == 0 ] ; then
        sections=$(( $sections + 1 ))
        sectionfile[$sections]=${ima_file[$i]}
        sectionsize[$sections]=$( stat -c %s ${sectionfile[$sections]} )
        sectionoffset[$sections]=$(align $offset)
        offset=$(( $offset + ${sectionsize[$sections]} ))
        $debug Adding section ${ima_file[$i]} size: ${sectionsize[$sections]} offset: ${sectionoffset[$sections]}
        section=$sections
    fi

    # Add TOC entry for every DTB to
    printf "0: %.8x" ${ima_pvr[$i]} | xxd -r -g0 >> $TMPFILE
    printf "0: %.8x" ${sectionoffset[$section]} | xxd -r -g0 >> $TMPFILE
    printf "0: %.8x" ${sectionsize[$section]} | xxd -r -g0 >> $TMPFILE
done

# write zeros to alignment
bytes=$(( $alignment - 8 - ($NUMBEROFTOCENTRIES * 12) ))
dd if=/dev/zero count=$bytes bs=1 >> $TMPFILE

# Add file sections
for i in $(seq $sections) ; do
    cat ${sectionfile[$i]} >> $TMPFILE

    # write zeros to alignment
    bytes=$(( $(align ${sectionsize[$i]}) - ${sectionsize[$i]} ))
    dd if=/dev/zero count=$bytes bs=1 >> $TMPFILE
done

mv $TMPFILE ima_catalog.bin

if [ "$3" == "dev" ]; then
   if [ "$2" == "POWER8" ]; then
      dd if=./ima_catalog.bin bs=32K count=1 > ./ima_catalog.temp.bin
      $1/ecc --inject ./ima_catalog.temp.bin --output ./ima_catalog.bin.ecc --p8
   elif [ "$2" == "POWER9" ]; then
      dd if=./ima_catalog.bin bs=256K count=1 > ./ima_catalog.temp.bin
      $1/ecc --inject ./ima_catalog.temp.bin --output ./ima_catalog.bin.ecc --p8
   fi
fi

rm -rf $TMPFILE

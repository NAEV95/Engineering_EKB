#!/bin/bash
#source /etc/modules.sh
module load amber/16/mpi/intel-2015-update2
#source /usr/local/amber18/amber.sh

TOP=protein_ok.pdb
#REF=../../../keap_solv_oct.rst7
TRJ1=md-pbc.trr
#TRJ2=../../nc/md_NVT_310K_2.nc
#TRJ3=../../nc/md_NVT_310K_3.nc
#TRJ4=../../nc/md_NVT_310K_4.nc
#...add as needed
AA=235
cat<<EOF>cpptraj.in
parm $TOP [keapwt]
trajin $TRJ1
#reference $REF parm $TOP [4dx5_C]
#reference $REF [ref]
#rms fit ref [ref] :1-${AA}&!@H= :1-${AA}&!@H= 
#rms whole ref [ref] :1-${AA}@CA,C,N :1-${AA}@CA,C,N out rmsd_backbone.dat time 0.1
secstruct protein out ss-protein.gnu :1-${AA} sumout ss-cumulative.gnu
run
quit
EOF

cpptraj -i cpptraj.in

awk 'BEGIN{NAA='${AA}'}{if ($1 ~ /[0-9]/) {if ($2 == "1.000") {para+=$3} else if ($2 == "2.000") {anti+=$3} else if ($2 == "3.000") {helix3_10+=$3} else if ($2 == "4.000") {alpha+=$3} else if ($2 == "5.000") {helixpi+=$3} else if ($2 == "6.000") {turn+=$3} else if ($2 == "7.000") {bend+=$3}}}END{printf "%8s%8s%8s%8s%8s%8s%8s\n", "B_Para","B_Anti","H_3-10","HAlpha","H_Pi","Turn","Bend"; printf "%8.4f%8.4f%8.4f%8.4f%8.4f%8.4f%8.4f\n", para/NAA, anti/NAA,helix3_10/NAA,alpha/NAA,helixpi/NAA,turn/NAA,bend/NAA}' ss-cumulative.gnu > ss-cumulative.dat

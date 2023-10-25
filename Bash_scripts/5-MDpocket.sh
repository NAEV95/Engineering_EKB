#!/bin/bash -l
#$ -S /bin/bash
#$ -l h_rt=1:00:0
#$ -l mem=2G
#$ -t 1-312
#$ -N Batch_1_mdpocket
#$ -pe mpi 160
#$ -cwd

module load vmd/1.9.3/text-only

cd $SGE_TASK_ID
echo "Batch array test $SGE_TASK_ID"
cp ../needed_align.tcl .
vmd -dispdev none -e needed_align.tcl 
/lustre/scratch/ucbenae/Paul_Sim/catdcd -o traj-aligned.dcd -otype dcd -s protein_ok.pdb -first 1 -last 2001 -pdb traj-aligned.pdb
../mdpocket --trajectory_file traj-aligned.dcd --trajectory_format dcd -f protein_ok.pdb --selected_pocket ../griglia_nick.pdb 


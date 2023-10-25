#!/bin/bash -l 
#$ -S /bin/bash
#$ -l h_rt=0:30:0
#$ -l mem=2G
#$ -t 1-312
#$ -N PBC-fix

#$ -pe mpi 160
#$ -cwd

module unload default-modules/2018
module unload compilers mpi
module load compilers/intel/2018/update3
module load mpi/intel/2018/update3/intel
module load gromacs/2019.3/intel-2018

cd $SGE_TASK_IDd    

echo 1 | gmx trjconv -s md_0_1.tpr -f md_0_1.trr -o md-pbc.trr -pbc whole -nice -19

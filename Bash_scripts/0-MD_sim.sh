#!/bin/bash -l
#$ -S /bin/bash
#$ -l h_rt=3:00:0
#$ -l mem=2G
#$ -t 1-312
#$ -N Batch_4
#$ -pe mpi 160
#$ -cwd

module unload compilers mpi
module load compilers/intel/2018/update3
module load mpi/intel/2018/update3/intel
module load gromacs/2019.3/intel-2018

# change into subdirectory 1 (or 2 or 3...)
cd $SGE_TASK_ID
echo "Batch array test $SGE_TASK_ID"
# any GROMACS commands here (remember to use gerun to run parallel gromacs or you won't be able to use all the cores you requested).

echo 15|gmx pdb2gmx -f EKB1m.pdb -o processed.gro -water tip3p -ignh
gmx editconf -f processed.gro -o newbox.gro -c -d 1.0 -bt cubic
gmx solvate -cp newbox.gro -cs spc216.gro -o solv.gro -p topol.top
gmx grompp -f ions.mdp -c solv.gro -p topol.top -o ions.tpr -maxwarn 1
echo 13|gmx genion -s ions.tpr -o solv_ions.gro -p topol.top -pname NA -nname CL -neutral -conc 0.5
gmx grompp -f minim.mdp -c solv_ions.gro -p topol.top -o em.tpr 
gerun mdrun_mpi -deffnm em
gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr
gerun mdrun_mpi -deffnm nvt
gmx grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr
gerun mdrun_mpi -deffnm npt
gmx grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -o md_0_1.tpr
gerun mdrun_mpi -deffnm md_0_1 -cpi -append
echo 10 0|gmx energy -f em.edr -o potential.xvg
echo 16 0|gmx energy -f nvt.edr
echo 17 0|gmx energy -f npt.edr -o pressure.xvg
echo 23 0|gmx energy -f npt.edr -o density.xvg
echo 0|gmx trjconv -s md_0_1.tpr -f md_0_1.xtc -o md_0_1_noPBC.xtc -pbc mol -ur compact
echo 4 4|gmx rms -s md_0_1.tpr -f md_0_1_noPBC.xtc -o rmsd.xvg -tu ns
echo 1|gmx gyrate -s md_0_1.tpr -f md_0_1_noPBC.xtc -o gyrate.xvg
echo 1|gmx rmsf -s md_0_1.tpr -f md_0_1_noPBC.xtc -o rmsf_10ns.xvg -oq bfac.pdb -res -b 0 -e 10000

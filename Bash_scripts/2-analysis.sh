#!/bin/bash -l 
#$ -S /bin/bash
#$ -l h_rt=1:00:0
#$ -l mem=2G
#$ -t 1-312
#$ -N Analysis
#$ -m e
#$ -pe mpi 160
#$ -cwd

module load gromacs/2019.3/intel-2018
module load vmd/1.9.3/text-only
module load python3/3.7
module load amber/16/mpi/intel-2015-update2

for name in $(ls -d */)
do
    name2=$(basename $name /)  
    cd $name
    
    rm \#*
    rm Summary_${name2}.dat
    gmx editconf -f solv.gro -o solv.pdb #SAVE ONLY PDB WITHOUT WATER
    grep -v "SOL" solv.pdb > protein_ok.pdb
    rm solv.pdb
    awk 'NR>4{print $2}' protein_ok.pdb > protein_serials #SAVE SERIALS OF ATOM ID 
    cp ../trajanalyze_templ.tcl .
    vmd -dispdev none -e trajanalyze_templ.tcl
    rm Summary_${name2}.dat
    rm Summary.dat
    ####################################################################
    ## Analysis of protein and its BS' RoG
    ## Analysis of protein and its BS' RMSD from the initial frame
    
    cp ../av_std-sel-region-column.sh .
    chmod +x av_std-sel-region-column.sh



    echo "#### AVERAGE VALUE    STANDARD DEVIATION ####">> Summary_${name2}.dat
    echo "RoG protein all heavy atoms" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RoG_pro_noh.dat 2 2 1002 >> Summary_${name2}.dat

    echo "RoG protein backbone atoms" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RoG_pro_backbone.dat 2 2 1002 >> Summary_${name2}.dat

    echo "RoG protein CA atoms" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RoG_pro_CA.dat 2 2 1002 >> Summary_${name2}.dat

    echo "RoG BS all heavy atoms" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RoG_BS_noh.dat 2 2 1002 >> Summary_${name2}.dat
    
    echo "RoG BS backbone atoms" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RoG_BS_backbone.dat 2 2 1002 >> Summary_${name2}.dat
    
    echo "RoG BS CA atoms" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RoG_BS_CA.dat 2 2 1002 >> Summary_${name2}.dat
    
    echo "RMSD protein all heavy atoms from starting structure" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RMSD_pro_noh.dat 2 2 1002 >> Summary_${name2}.dat

    echo "RMSD protein backbone atoms from starting structure" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RMSD_pro_backbone.dat 2 2 1002 >> Summary_${name2}.dat
       
    echo "RMSD protein CA atoms from starting structure" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RMSD_pro_CA.dat 2 2 1002 >> Summary_${name2}.dat

    echo "RMSD BS all heavy atoms from starting structure" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RMSD_BS_noh.dat 2 2 1002 >> Summary_${name2}.dat

    echo "RMSD BS backbone atoms from starting structure" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RMSD_BS_backbone.dat 2 2 1002 >> Summary_${name2}.dat
       
    echo "RMSD BS CA atoms from starting structure" >> Summary_${name2}.dat
    ./av_std-sel-region-column.sh RMSD_BS_CA.dat 2 2 1002 >> Summary_${name2}.dat

    ##########################################################################
    #
    #
    #
    cp ../secondary-structure-analysis.sh .
    chmod +x ./secondary-structure-analysis.sh
    ./secondary-structure-analysis.sh
    echo "">>Summary_${name2}.dat
    echo "Secondary Structure Analysis">>Summary_${name2}.dat
    echo "(Percentage of protein residues in defined element of SS structure)/time">>Summary_${name2}.dat
    cat ss-cumulative.dat >>Summary_${name2}.dat
    echo "(Percentage of protein residues in a random coil conformation)/time">>Summary_${name2}.dat
    echo " 0"$(awk 'NR==2{print "1-("$1"+"$2"+"$3"+"$4"+"$5"+"$6"+"$7")"}' ss-cumulative.dat  | bc -l) >>Summary_${name2}.dat
    echo " ">>Summary_${name2}.dat

    ########################## Sequence Analysis ##################
    cp ../pdb-to-seq-template1.awk .
    awk -f pdb-to-seq-template1.awk protein_ok.pdb
    grep -v "structureX::FIRST:A:END:C::::" template1.ali > sequence.fasta
    python3.7 ../ipc.py sequence.fasta
    echo "">>Summary_${name2}.dat
    echo "">>Summary_${name2}.dat
    echo "Molecular Weight and isoelectric point calculation">>Summary_${name2}.dat
    cat sequence.fasta.pI.txt >>Summary_${name2}.dat
    echo "">>Summary_${name2}.dat
    echo "">>Summary_${name2}.dat
    cd ..

done

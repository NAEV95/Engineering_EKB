#!/bin/bash
for name in $(ls -d */)
do
    name2=$(basename $name /)  
    cd $name    
    awk 'NR>1{print $0}' sequence.fasta > tmp
    sed 's/*//g' tmp > sequence_${name2}.fasta
    cd ..
done

#!/bin/bash

for dir in $(ls -d */)
do
dir2=$(basename $dir /)
cd $dir
for name in $(ls sequence_*.fasta)
do
name2=$(basename $name .fasta | cut -d'_' -f2)
tr -d "\n\r" < $name > tmp
mv tmp $name
sed 's/ //g' $name > ${name2}_ok.fasta
sed 's/filename/'"seq_features${name2}.dat"'/g' ../template.py > tmp_template.py
sed 's/sequence/'$(cat ${name2}_ok.fasta)'/g' tmp_template.py > template_${name2}.py
python3.7 template_${name2}.py
rm template_${name2}.py ${name2}_ok.fasta
done
cd ..
done

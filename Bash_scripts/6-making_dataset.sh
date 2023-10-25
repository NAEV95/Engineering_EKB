
#!/bin/bash
source /etc/modules.sh
module load gromacs2018-4_gnu_cuda_mpi_plumed 


############# PART 1 : POCKET DESCRIPTORS BY FPOCKET #####################
# 42 DESCRIPTORS AVERAGED FOR THE WHOLE TRAJECTORY
# THE VERY FIRST NUMBER REPRESENTS THE FOLDER (1....312), THEN WE HAVE THESE 42 VALUES
#

for name in $(ls -d ?/)
do
    name2=$(basename $name /)  
    cd $name
    for i in {0..42..1}
    do
       ./av_std-sel-region-column.sh mdpout_descriptors.txt $i 2 1002 > dataset_${i}.dat
    done
cd ..
done

for name in $(ls -d ??/)
do
    name2=$(basename $name /)  
    cd $name
    for i in {0..42..1}
    do
	./av_std-sel-region-column.sh mdpout_descriptors.txt $i 2 1002 > dataset_${i}.dat
    done
    cd ..
done

for name in $(ls -d ???/)
do
    name2=$(basename $name /)  
    cd $name
    for i in {0..42..1}
    do
	./av_std-sel-region-column.sh mdpout_descriptors.txt $i 2 1002 > dataset_${i}.dat
    done
cd ..
done
    

############# PART 2 : DYNAMICAL PROPERTIES ANALYZED FROM THE MD SIMULATIONS  #####################
# 12 DESCRIPTORS
# 
#


for name in $(ls -d ?/)
do
    name2=$(basename $name /)  
    cd $name
    rm MD*.dat
    ./av_std-sel-region-column.sh RoG_pro_noh.dat 2 2 1002 >> MD${name2}_1.dat
    ./av_std-sel-region-column.sh RoG_pro_backbone.dat 2 2 1002 >> MD${name2}_2.dat
    ./av_std-sel-region-column.sh RoG_pro_CA.dat 2 2 1002 >> MD${name2}_3.dat
    ./av_std-sel-region-column.sh RoG_BS_noh.dat 2 2 1002 >> MD${name2}_4.dat
    ./av_std-sel-region-column.sh RoG_BS_backbone.dat 2 2 1002 >> MD${name2}_5.dat
    ./av_std-sel-region-column.sh RoG_BS_CA.dat 2 2 1002 >> MD${name2}_6.dat
    ./av_std-sel-region-column.sh RMSD_pro_noh.dat 2 2 1002 >> MD${name2}_7.dat
    ./av_std-sel-region-column.sh RMSD_pro_backbone.dat 2 2 1002 >> MD${name2}_8.dat
    ./av_std-sel-region-column.sh RMSD_pro_CA.dat 2 2 1002 >> MD${name2}_9.dat
    ./av_std-sel-region-column.sh RMSD_BS_noh.dat 2 2 1002 >> MD${name2}_10.dat
    ./av_std-sel-region-column.sh RMSD_BS_backbone.dat 2 2 1002 >> MD${name2}_11.dat
    ./av_std-sel-region-column.sh RMSD_BS_CA.dat 2 2 1002 >> MD${name2}_12.dat
cd ..
done

for name in $(ls -d ??/)
do
    name2=$(basename $name /)  
    cd $name
    rm MD*.dat
    ./av_std-sel-region-column.sh RoG_pro_noh.dat 2 2 1002 >> MD${name2}_1.dat
    ./av_std-sel-region-column.sh RoG_pro_backbone.dat 2 2 1002 >> MD${name2}_2.dat
    ./av_std-sel-region-column.sh RoG_pro_CA.dat 2 2 1002 >> MD${name2}_3.dat
    ./av_std-sel-region-column.sh RoG_BS_noh.dat 2 2 1002 >> MD${name2}_4.dat
    ./av_std-sel-region-column.sh RoG_BS_backbone.dat 2 2 1002 >> MD${name2}_5.dat
    ./av_std-sel-region-column.sh RoG_BS_CA.dat 2 2 1002 >> MD${name2}_6.dat
    ./av_std-sel-region-column.sh RMSD_pro_noh.dat 2 2 1002 >> MD${name2}_7.dat
    ./av_std-sel-region-column.sh RMSD_pro_backbone.dat 2 2 1002 >> MD${name2}_8.dat
    ./av_std-sel-region-column.sh RMSD_pro_CA.dat 2 2 1002 >> MD${name2}_9.dat
    ./av_std-sel-region-column.sh RMSD_BS_noh.dat 2 2 1002 >> MD${name2}_10.dat
    ./av_std-sel-region-column.sh RMSD_BS_backbone.dat 2 2 1002 >> MD${name2}_11.dat
    ./av_std-sel-region-column.sh RMSD_BS_CA.dat 2 2 1002 >> MD${name2}_12.dat
cd ..
done

for name in $(ls -d ???/)
do
    name2=$(basename $name /)  
    cd $name
    rm MD*.dat
    ./av_std-sel-region-column.sh RoG_pro_noh.dat 2 2 1002 >> MD${name2}_1.dat
    ./av_std-sel-region-column.sh RoG_pro_backbone.dat 2 2 1002 >> MD${name2}_2.dat
    ./av_std-sel-region-column.sh RoG_pro_CA.dat 2 2 1002 >> MD${name2}_3.dat
    ./av_std-sel-region-column.sh RoG_BS_noh.dat 2 2 1002 >> MD${name2}_4.dat
    ./av_std-sel-region-column.sh RoG_BS_backbone.dat 2 2 1002 >> MD${name2}_5.dat
    ./av_std-sel-region-column.sh RoG_BS_CA.dat 2 2 1002 >> MD${name2}_6.dat
    ./av_std-sel-region-column.sh RMSD_pro_noh.dat 2 2 1002 >> MD${name2}_7.dat
    ./av_std-sel-region-column.sh RMSD_pro_backbone.dat 2 2 1002 >> MD${name2}_8.dat
    ./av_std-sel-region-column.sh RMSD_pro_CA.dat 2 2 1002 >> MD${name2}_9.dat
    ./av_std-sel-region-column.sh RMSD_BS_noh.dat 2 2 1002 >> MD${name2}_10.dat
    ./av_std-sel-region-column.sh RMSD_BS_backbone.dat 2 2 1002 >> MD${name2}_11.dat
    ./av_std-sel-region-column.sh RMSD_BS_CA.dat 2 2 1002 >> MD${name2}_12.dat

cd ..
done

############# PART 3 : Secondary Structure Analysis + IP
# 8 DESCRIPTORS + 1 (isoelectric point)
# 
#

for name in $(ls -d ?/)
do
    name2=$(basename $name /)  
    cd $name
    awk 'NR==30{print $0}' Summary_${name2}.dat > SS_${name2}_1.dat
    awk 'NR==32{print $1}' Summary_${name2}.dat > SS_${name2}_2.dat
    awk 'NR==40{print $18}' Summary_${name2}.dat > IP_${name2}.dat
    cd ..
done

for name in $(ls -d ??/)
do
    name2=$(basename $name /)  
    cd $name
    awk 'NR==30{print $0}' Summary_${name2}.dat > SS_${name2}_1.dat
    awk 'NR==32{print $1}' Summary_${name2}.dat > SS_${name2}_2.dat
    awk 'NR==40{print $18}' Summary_${name2}.dat > IP_${name2}.dat
    cd ..
done

for name in $(ls -d ???/)
do
    name2=$(basename $name /)  
    cd $name
    awk 'NR==30{print $0}' Summary_${name2}.dat > SS_${name2}_1.dat
    awk 'NR==32{print $1}' Summary_${name2}.dat > SS_${name2}_2.dat
    awk 'NR==40{print $18}' Summary_${name2}.dat > IP_${name2}.dat
    cd ..
done
##
############### PART 4 : Biopython
###Molecular weight:
###Aromaticity: 
###Instability index (if > 40: unstable): 
###Gravy  (grand average of hydropathy): 
###% of hydrophobic a.a.: Glycine (G)  
###% of hydrophobic a.a.: Alanine (A)  
###% of hydrophobic a.a.: Valine (V)  
###% of hydrophobic a.a.: Leucine (L) 
###% of hydrophobic a.a.: Isoleucine (I) 
###% of hydrophobic a.a.: Proline (P)  
###% of hydrophobic a.a.: Phenilalanine (F) 
###% of hydrophobic a.a.: Methionine (M)  
###% of hydrophobic a.a.: Tryptophan (W)  
### 
###
##
for name in $(ls -d ???/)
do
    name2=$(basename $name /)  
    cd $name
    awk 'NR==29{print $3}' seq_features${name2}.dat > biopython_1.dat
    awk 'NR==30{print $2}' seq_features${name2}.dat > biopython_2.dat
    awk 'NR==31{print $7}' seq_features${name2}.dat > biopython_3.dat
    awk 'NR==32{print $6}' seq_features${name2}.dat > biopython_4.dat
    awk 'NR==34{print $7}' seq_features${name2}.dat > biopython_5.dat
    awk 'NR==35{print $7}' seq_features${name2}.dat > biopython_6.dat
    awk 'NR==36{print $7}' seq_features${name2}.dat > biopython_7.dat
    awk 'NR==37{print $7}' seq_features${name2}.dat > biopython_8.dat
    awk 'NR==38{print $7}' seq_features${name2}.dat > biopython_9.dat
    awk 'NR==39{print $7}' seq_features${name2}.dat > biopython_10.dat
    awk 'NR==40{print $7}' seq_features${name2}.dat > biopython_11.dat
    awk 'NR==41{print $7}' seq_features${name2}.dat > biopython_12.dat
    awk 'NR==42{print $7}' seq_features${name2}.dat > biopython_13.dat
    cd ..
done

for name in $(ls -d ??/)
do
    name2=$(basename $name /)  
    cd $name
    awk 'NR==29{print $3}' seq_features${name2}.dat > biopython_1.dat
    awk 'NR==30{print $2}' seq_features${name2}.dat > biopython_2.dat
    awk 'NR==31{print $7}' seq_features${name2}.dat > biopython_3.dat
    awk 'NR==32{print $6}' seq_features${name2}.dat > biopython_4.dat
    awk 'NR==34{print $7}' seq_features${name2}.dat > biopython_5.dat
    awk 'NR==35{print $7}' seq_features${name2}.dat > biopython_6.dat
    awk 'NR==36{print $7}' seq_features${name2}.dat > biopython_7.dat
    awk 'NR==37{print $7}' seq_features${name2}.dat > biopython_8.dat
    awk 'NR==38{print $7}' seq_features${name2}.dat > biopython_9.dat
    awk 'NR==39{print $7}' seq_features${name2}.dat > biopython_10.dat
    awk 'NR==40{print $7}' seq_features${name2}.dat > biopython_11.dat
    awk 'NR==41{print $7}' seq_features${name2}.dat > biopython_12.dat
    awk 'NR==42{print $7}' seq_features${name2}.dat > biopython_13.dat
    cd ..
done

for name in $(ls -d ?/)
do
    name2=$(basename $name /)  
    cd $name
    awk 'NR==29{print $3}' seq_features${name2}.dat > biopython_1.dat
    awk 'NR==30{print $2}' seq_features${name2}.dat > biopython_2.dat
    awk 'NR==31{print $7}' seq_features${name2}.dat > biopython_3.dat
    awk 'NR==32{print $6}' seq_features${name2}.dat > biopython_4.dat
    awk 'NR==34{print $7}' seq_features${name2}.dat > biopython_5.dat
    awk 'NR==35{print $7}' seq_features${name2}.dat > biopython_6.dat
    awk 'NR==36{print $7}' seq_features${name2}.dat > biopython_7.dat
    awk 'NR==37{print $7}' seq_features${name2}.dat > biopython_8.dat
    awk 'NR==38{print $7}' seq_features${name2}.dat > biopython_9.dat
    awk 'NR==39{print $7}' seq_features${name2}.dat > biopython_10.dat
    awk 'NR==40{print $7}' seq_features${name2}.dat > biopython_11.dat
    awk 'NR==41{print $7}' seq_features${name2}.dat > biopython_12.dat
    awk 'NR==42{print $7}' seq_features${name2}.dat > biopython_13.dat
    cd ..
done

#################### ALL TOGETHER ################################

for name in $(ls -d ?/)
do
    name2=$(basename $name /)  
    cd $name
    echo "$name2" > ID_sequence
    
    paste ID_sequence dataset_1.dat dataset_2.dat dataset_3.dat dataset_4.dat dataset_5.dat dataset_6.dat dataset_7.dat dataset_8.dat dataset_9.dat dataset_10.dat dataset_11.dat dataset_12.dat dataset_13.dat dataset_14.dat dataset_15.dat dataset_16.dat dataset_17.dat dataset_18.dat dataset_19.dat dataset_20.dat dataset_21.dat dataset_22.dat dataset_23.dat dataset_24.dat dataset_25.dat dataset_26.dat dataset_27.dat dataset_28.dat dataset_29.dat dataset_30.dat  dataset_31.dat dataset_32.dat dataset_33.dat dataset_34.dat dataset_35.dat dataset_36.dat dataset_37.dat dataset_38.dat dataset_39.dat dataset_40.dat dataset_41.dat dataset_42.dat MD${name2}_1.dat MD${name2}_2.dat MD${name2}_3.dat MD${name2}_4.dat MD${name2}_5.dat MD${name2}_6.dat MD${name2}_7.dat MD${name2}_8.dat MD${name2}_9.dat MD${name2}_10.dat MD${name2}_11.dat MD${name2}_12.dat SS_${name2}_1.dat SS_${name2}_2.dat IP_${name2}.dat biopython_1.dat biopython_2.dat biopython_3.dat biopython_4.dat biopython_5.dat biopython_6.dat biopython_7.dat biopython_8.dat biopython_9.dat biopython_10.dat biopython_11.dat biopython_12.dat biopython_13.dat> Dataset_${name2}_ok.dat
    cd ..
done

for name in $(ls -d ??/)
do
    name2=$(basename $name /)  
    cd $name
    echo "$name2" > ID_sequence
    
    paste ID_sequence dataset_1.dat dataset_2.dat dataset_3.dat dataset_4.dat dataset_5.dat dataset_6.dat dataset_7.dat dataset_8.dat dataset_9.dat dataset_10.dat dataset_11.dat dataset_12.dat dataset_13.dat dataset_14.dat dataset_15.dat dataset_16.dat dataset_17.dat dataset_18.dat dataset_19.dat dataset_20.dat dataset_21.dat dataset_22.dat dataset_23.dat dataset_24.dat dataset_25.dat dataset_26.dat dataset_27.dat dataset_28.dat dataset_29.dat dataset_30.dat  dataset_31.dat dataset_32.dat dataset_33.dat dataset_34.dat dataset_35.dat dataset_36.dat dataset_37.dat dataset_38.dat dataset_39.dat dataset_40.dat dataset_41.dat dataset_42.dat MD${name2}_1.dat MD${name2}_2.dat MD${name2}_3.dat MD${name2}_4.dat MD${name2}_5.dat MD${name2}_6.dat MD${name2}_7.dat MD${name2}_8.dat MD${name2}_9.dat MD${name2}_10.dat MD${name2}_11.dat MD${name2}_12.dat SS_${name2}_1.dat SS_${name2}_2.dat IP_${name2}.dat biopython_1.dat biopython_2.dat biopython_3.dat biopython_4.dat biopython_5.dat biopython_6.dat biopython_7.dat biopython_8.dat biopython_9.dat biopython_10.dat biopython_11.dat biopython_12.dat biopython_13.dat> Dataset_${name2}_ok.dat
    cd ..
done

for name in $(ls -d ???/)
do
    name2=$(basename $name /)  
    cd $name
    echo "$name2" > ID_sequence
    
    paste ID_sequence dataset_1.dat dataset_2.dat dataset_3.dat dataset_4.dat dataset_5.dat dataset_6.dat dataset_7.dat dataset_8.dat dataset_9.dat dataset_10.dat dataset_11.dat dataset_12.dat dataset_13.dat dataset_14.dat dataset_15.dat dataset_16.dat dataset_17.dat dataset_18.dat dataset_19.dat dataset_20.dat dataset_21.dat dataset_22.dat dataset_23.dat dataset_24.dat dataset_25.dat dataset_26.dat dataset_27.dat dataset_28.dat dataset_29.dat dataset_30.dat  dataset_31.dat dataset_32.dat dataset_33.dat dataset_34.dat dataset_35.dat dataset_36.dat dataset_37.dat dataset_38.dat dataset_39.dat dataset_40.dat dataset_41.dat dataset_42.dat MD${name2}_1.dat MD${name2}_2.dat MD${name2}_3.dat MD${name2}_4.dat MD${name2}_5.dat MD${name2}_6.dat MD${name2}_7.dat MD${name2}_8.dat MD${name2}_9.dat MD${name2}_10.dat MD${name2}_11.dat MD${name2}_12.dat SS_${name2}_1.dat SS_${name2}_2.dat IP_${name2}.dat biopython_1.dat biopython_2.dat biopython_3.dat biopython_4.dat biopython_5.dat biopython_6.dat biopython_7.dat biopython_8.dat biopython_9.dat biopython_10.dat biopython_11.dat biopython_12.dat biopython_13.dat> Dataset_${name2}_ok.dat
    cd ..
done

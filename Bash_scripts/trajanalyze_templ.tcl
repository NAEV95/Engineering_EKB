################################
#Parte 0: caricare la traiettoria
#################################

set outfile_ROG_pro_noh [open "RoG_pro_noh.dat" w]
set outfile_ROG_pro_backbone [open "RoG_pro_backbone.dat" w]
set outfile_ROG_pro_CA [open "RoG_pro_CA.dat" w]
set outfile_ROG_BS_noh [open "RoG_BS_noh.dat" w]
set outfile_ROG_BS_backbone [open "RoG_BS_backbone.dat" w]
set outfile_ROG_BS_CA [open "RoG_BS_CA.dat" w]
set outfile_RMSD_pro_noh [open "RMSD_pro_noh.dat" w]
set outfile_RMSD_pro_backbone [open "RMSD_pro_backbone.dat" w]
set outfile_RMSD_pro_CA [open "RMSD_pro_CA.dat" w]
set outfile_RMSD_BS_noh [open "RMSD_BS_noh.dat" w]
set outfile_RMSD_BS_backbone [open "RMSD_BS_backbone.dat" w]
set outfile_RMSD_BS_CA [open "RMSD_BS_CA.dat" w]

#struttura di riferimento, molid: 0
mol new ./protein_ok.pdb type pdb

set mol [mol new protein_ok.pdb type pdb waitfor all]
mol addfile md-pbc.trr type trr waitfor all

set pro_noh [atomselect 1 "noh protein"]
set pro_bb [atomselect 1 "noh protein and backbone"]
set pro_CA [atomselect 1 "noh protein and name CA"]
set BS_noh [atomselect 1 "noh protein and resid 41 89 164 182 185 187 206 207 208 218 and noh"]
set BS_bb [atomselect 1 "noh protein and resid 41 89 164 182 185 187 206 207 208 218 and backbone"]
set BS_CA [atomselect 1 "noh protein and resid 41 89 164 182 185 187 206 207 208 218 and name CA"]

set ref_pro_noh [atomselect 0 "noh protein"]
set ref_pro_bb [atomselect 0 "noh protein and backbone"]
set ref_pro_CA [atomselect 0 "noh protein and name CA"]
set ref_BS_noh [atomselect 0 "noh protein and resid 41 89 164 182 185 187 206 207 208 218 and noh"]
set ref_BS_bb [atomselect 0 "noh protein and resid 41 89 164 182 185 187 206 207 208 218 and backbone"]
set ref_BS_CA [atomselect 0 "noh protein and resid 41 89 164 182 185 187 206 207 208 218 and name CA"]

set pdbselection [atomselect 1 "protein"]

# Se si volesse usare il frame 0 della traiettoria come riferimento....
# use frame 0 for the reference
#set reference [atomselect 0 "protein" frame 0]
# the frame being compared
#set compare [atomselect 0 "protein"]

# Ciclo che effettua il lavoro: per ogni frame della traiettoria si fa l'allineamento, si calcola l'rmsd dalla struttura di riferimento e salva il frame relativo

set num_steps [molinfo $mol get numframes]
for {set frame 0} {$frame < $num_steps} {incr frame} {

    # Parte relativa al calcolo dei raggi di girazione, per cui non c'è bisogno di allineare nulla,
    # Serve solmanete la definizione della porzione della proteina su cui calcolarlo
    # R_g = m*N^(1/3)
    set rog_pro_noh [measure rgyr $pro_noh]
    set rog_pro_bb  [measure rgyr $pro_bb]
    set rog_pro_CA  [measure rgyr $pro_CA]
    set rog_BS_noh  [measure rgyr $BS_noh]
    set rog_BS_bb   [measure rgyr $BS_bb]
    set rog_BS_CA   [measure rgyr $BS_CA]
#    $compare frame $frame
    animate goto $frame
    
    puts $outfile_ROG_pro_noh  "$frame $rog_pro_noh"
    puts $outfile_ROG_pro_backbone  "$frame $rog_pro_bb"
    puts $outfile_ROG_pro_CA  "$frame $rog_pro_CA"
    puts $outfile_ROG_BS_noh  "$frame $rog_BS_noh"
    puts $outfile_ROG_BS_backbone  "$frame $rog_BS_bb"
    puts $outfile_ROG_BS_CA  "$frame $rog_BS_CA"

    
    set trans_mat [measure fit $pro_noh $ref_pro_noh]
    $pdbselection move $trans_mat
    set rmsd [measure rmsd $pro_noh $ref_pro_noh]
    puts $outfile_RMSD_pro_noh "$frame $rmsd"

    set trans_mat [measure fit $pro_bb $ref_pro_bb]
    $pdbselection move $trans_mat
    set rmsd [measure rmsd $pro_bb $ref_pro_bb]
    puts $outfile_RMSD_pro_backbone "$frame $rmsd"

    set trans_mat [measure fit $pro_CA $ref_pro_CA]
    $pdbselection move $trans_mat
    set rmsd [measure rmsd $pro_CA $ref_pro_CA]
    puts $outfile_RMSD_pro_CA "$frame $rmsd"

    ###############
    
    set trans_mat [measure fit $BS_noh $ref_BS_noh]
    $pdbselection move $trans_mat
    set rmsd [measure rmsd $BS_noh $ref_BS_noh]
    puts $outfile_RMSD_BS_noh "$frame $rmsd"

    set trans_mat [measure fit $BS_bb $ref_BS_bb]
    $pdbselection move $trans_mat
    set rmsd [measure rmsd $BS_bb $ref_BS_bb]
    puts $outfile_RMSD_BS_backbone "$frame $rmsd"

    set trans_mat [measure fit $BS_CA $ref_BS_CA]
    $pdbselection move $trans_mat
    set rmsd [measure rmsd $BS_CA $ref_BS_CA]
    puts $outfile_RMSD_BS_CA "$frame $rmsd"


}

close $outfile_ROG_pro_noh
close $outfile_ROG_pro_backbone
close $outfile_ROG_pro_CA 
close $outfile_ROG_BS_noh
close $outfile_ROG_BS_backbone 
close $outfile_ROG_BS_CA 
close $outfile_RMSD_pro_noh 
close $outfile_RMSD_pro_backbone 
close $outfile_RMSD_pro_CA 
close $outfile_RMSD_BS_noh 
close $outfile_RMSD_BS_backbone 
close $outfile_RMSD_BS_CA
      
quit

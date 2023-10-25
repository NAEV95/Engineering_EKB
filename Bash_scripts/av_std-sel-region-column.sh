#!/bin/bash
nargs=${#@}
if [ $nargs != 4 ]; then
    echo "usage: ./av_std-sel-region-column.sh file column-to-average init end"
    exit
fi
file=$1
column=$2
init=$3
end=$4
av=$(awk 'BEGIN{sum=0;count=0}{if (($1 ~ /[0-9]/) && (NR >= '${init}') && (NR <= '${end}')){count++;sum=sum+$'${column}'}}END{printf "%5.3f",sum/(count-1)}' $file | awk '{print $1}')
std=$(awk 'BEGIN{var=0;count=0}{if (($1 ~ /[0-9]/) && (NR >= '${init}') && (NR <= '${end}')){count++;var=var+($'${column}' - '${av}')^2}}END{var=var/(count-1); std=sqrt(var); printf "%5.3f\n",std}' $file | awk '{print $1}')
echo "$av $std" 

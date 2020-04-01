#!/bin/bash
#targets=( "Age" "Sex" )
targets=( "Age" )
memory=8G
n_cpu_cores=1
time=60
for target in "${targets[@]}"; do
		version=MI05A_${target}_${id_set}
		job_name="$version.job"
		out_file="../eo/$version.out"
		err_file="../eo/$version.err"
		sbatch --error=$err_file --output=$out_file --job-name=$job_name --mem-per-cpu=$memory -c $n_cpu_cores -t $time MI05A_Ensembles_predictions_generate_and_merge.sh $target
done

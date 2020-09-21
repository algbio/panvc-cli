#!/usr/bin/python3
import sys
import shutil
from pvc_tools import *
from datetime import datetime


#def paths_main():
#    PG_INDEX_DIR = sys.argv[1]
#    POS_DIR = sys.argv[2]
#    OUTPUT_DIR = sys.argv[3]
#    LOG_DIR = sys.argv[4]
#    paths(PG_INDEX_DIR, POS_DIR, OUTPUT_DIR, LOG_DIR)

def validate_sorted_file(input_filename):
    assert(Path(input_filename).is_file())
    prev = 0
    with open(input_filename, "r") as myfile:
        for line in myfile:
            number = int(line.rstrip())
            if (number < prev):
                print ("Error validating file: " + input_filename)
                print ("The following values are in the wrong order: " + str(prev) + " , " + str(number))
                exit(33)

def process_seq(seq,  POS_DIR, pgindex_dir, chr_id):
    msa_len = PVC_load_var("msa_len", pgindex_dir + "/"+ chr_id)
    read_len = PVC_load_var("read_len", POS_DIR)
    curr_pos_dir = POS_DIR + "/" + chr_id
    input_pos = curr_pos_dir + "/mapped_reads_to" + str(seq) + ".pos"
    input_gaps_prefix = pgindex_dir + "/" + chr_id + "/recombinant.n"  + str(seq) + ".gaps"
    curr_tmp_prefix = curr_pos_dir + "/tmp_light_heaviest_path." + str(seq)
    
    split_sort_command = " ".join([SPLIT_AND_SORT_BIN, input_pos, input_gaps_prefix, curr_tmp_prefix, str(msa_len), str(read_len)])
    call_or_die(split_sort_command)
    
    pileup_command = " ".join([PILEUP_BIN, curr_tmp_prefix])
    call_or_die(pileup_command)
    validate_sorted_file(curr_tmp_prefix + ".starts")
    validate_sorted_file(curr_tmp_prefix + ".ends")

def paths(pgindex_dir, POS_DIR, OUTPUT_DIR, LOG_DIR, debug):
    start = datetime.now()
    print(f"{start} Paths")

    assert(Path(HP_BIN).is_file())
    assert(Path(MATRIX_PRINT_BIN).is_file())

    output_fasta_all = OUTPUT_DIR + "/adhoc_reference_all_chrs.fasta"
    output_gapped_all = OUTPUT_DIR + "/adhoc_reference_all_chrs.aligned_to_ref"
    output_plain_all = OUTPUT_DIR + "/adhoc_reference_all_chrs.plain"

    assert(not Path(output_fasta_all).exists())
    assert(not Path(output_gapped_all).exists())
    assert(not Path(output_plain_all).exists())
    
    n_refs = PVC_load_var("n_refs", f"{pgindex_dir}/1") # FIXME: allow varying number of references per chromosome.
    chr_list = PVC_get_chr_list(pgindex_dir)
    n_chroms = len(chr_list)
    first_chr = chr_list[0]
    for chr_id in chr_list:
        sys.stderr.write("Processing chr " + chr_id + "\n")
        hp_log = LOG_DIR + "/heaviest_path_chr" + chr_id + ".log"
        curr_pos_dir = POS_DIR + "/" + chr_id
        msa_len = PVC_load_var("msa_len", pgindex_dir + "/"+ chr_id)
        curr_output_dir = OUTPUT_DIR + "/" + chr_id
        ensure_dir(curr_output_dir)
        output_prefix = curr_output_dir + "/adhoc_reference"
        ## Actual work:
        sum_files_list = curr_pos_dir + "/sum_files.txt"
        if (Path(sum_files_list).exists()):
            Path(sum_files_list).unlink()  ## We will append to this file, need to make sure it does not exist before.

        # rm sum_files_list
        for seq_id in range (1, n_refs+1):
            process_seq(seq_id,  POS_DIR, pgindex_dir, chr_id)
        
        for seq_id in range (1, n_refs+1):
            curr_tmp_prefix = curr_pos_dir + "/tmp_light_heaviest_path." + str(seq_id)
            with open(sum_files_list, "a") as myfile:
                assert(Path(curr_tmp_prefix + ".sums").is_file())
                myfile.write(curr_tmp_prefix + ".sums\n")
        matrix_pgm_output = LOG_DIR + "/scores_matrix.pgm"
        print_matrix_command = " ".join([MATRIX_PRINT_BIN, sum_files_list, str(n_refs), str(msa_len), matrix_pgm_output, ">", hp_log])
        #call_or_die(print_matrix_command)

        gaps_dir  = pgindex_dir + "/" + chr_id
        all_fasta_name = pgindex_dir + "/recombinant.all.fa"
        hp_command = " ".join([HP_BIN, sum_files_list, gaps_dir, all_fasta_name, str(chr_id), str(n_chroms), str(first_chr), str(n_refs), str(msa_len), output_prefix, ">>", hp_log])
        call_or_die(hp_command)
        ## Main work already done.
        output_gapped = curr_output_dir + "/adhoc_reference.aligned_to_ref"
        output_plain = curr_output_dir + "/adhoc_reference.plain"
        output_fasta = curr_output_dir + "/adhoc_reference.fasta"
  
        cat_command = " ".join(["cat", output_gapped, ">>", output_gapped_all])
        call_or_die(cat_command)
        
        assert(Path(output_gapped).is_file())
        assert(not Path(output_plain).is_file())
        assert(not Path(output_fasta).is_file())
        
        gap_f = open(output_gapped, "r")
        for line in gap_f:
            newline = line.replace('-','')
            with open(output_plain, "a") as tmp_file:
                tmp_file.write(newline + "\n")
            with open(output_plain_all, "a") as tmp_file:
                tmp_file.write(newline + "\n")
            with open(output_fasta, "a") as tmp_file:
                tmp_file.write(">adhoc_ref\n")
                tmp_file.write(newline + "\n")
            with open(output_fasta_all, "a") as tmp_file:
                tmp_file.write(">adhoc_ref_chr" +str(chr_id) + "\n")
                tmp_file.write(newline + "\n")

        gap_f.close()
        print("Adhoc-ref succesfully built!")
        if (not debug):
            cleanup_command = "rm " + curr_pos_dir + "/tmp_light_heaviest_path.*"
            call_or_die(cleanup_command)
    end = datetime.now()
    print(f"{end} Time taken (paths): {end - start}")
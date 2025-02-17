#!/usr/bin/python3

############################
###   DESCRIPTION HERE   ###
############################

# USAGE: python3 BLASTp_SwissProt_TriTrypDB.py \
#                    --seq Cleared_Linfantum_AUGUSTUS.aa \
#                    --swissprot uniprot_sprot.fasta \
#                    --tritrypdb TriTrypDB_proteins.fasta

"""---A AVENTURA VAI COMEÇAR-------------------------------------------------"""

import argparse
import subprocess
import logging
import sys
import re
import os
from venv import logger

'''---ARGUMENTS AND [--help / -help / -h]------------------------------------'''

def cli():
    parser = argparse.ArgumentParser(
        add_help=False,  # removes original [--help]
        description='''Scritp to run and parse output from Swissprot and other database [NR, EupathDB, Trembl],
        Please give at least one, through flags -nr, -spdb or -trbl   
        ''',
        epilog=""">>>> -nr, -spdb and -trbl are mutually exclusive arguments <<<<
        
    Poof, you're a sandwich!""", formatter_class=argparse.RawTextHelpFormatter
    )

    requiredNamed = parser.add_argument_group('required arguments')
    optionalNamed = parser.add_argument_group('optional arguments')

    # mandatory arguments
    #   type (default): string
    requiredNamed.add_argument(
        '-s', '--seq', dest='seq',
        metavar='[protein_file]',
        help=('non-redundant protein fasta file'
            + ' to be used by the BLASTp suite'),
        required=True
    )

    requiredNamed.add_argument(
        '-sp', '--swissprot', dest='spdb',
        metavar='[UniProt_SwissProt_database]',
        help='destination to /SwissProt/database',
        required=True
    )

    requiredNamed.add_argument(
        '-basename', dest='basename',
        metavar='[It\'s a boy, and will be called Jonas]',
        help='basename',
        required=True
    )

    #   type (default): string
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-trbl', '--Trembl', dest='trembl',
        metavar='[Trembl_database]',
        help='destination to Trembl database'
    )

    group.add_argument(
        '-spdb', '--specificdb', dest='specificdb',
        metavar='[SpecificDB_database]',
        help='destination to specific database, in EupathDB format',
    )

    group.add_argument(
        '-nr', '--nrdb', dest='nr',
        metavar='[NR_database]',
        help='destination to NR database',
    )

    optionalNamed.add_argument(
        '-id', '--identity', dest='id',
        metavar='', default=40,
        help=('Minimal identity to transfer annotation. If a query has results below this threshold '
            'it will be classified as hypothetical'
            + ' (default: 40)')
    )

    optionalNamed.add_argument(
        '-blastp', dest='blastp',
        metavar='/opt/blast/blastp',
        default="blastp",
        help='full path to blastp [if it`s in bin pass just "blastp"]',
        required=False
    )

    optionalNamed.add_argument(
        '-cov', '--coverage', dest='cov',
        metavar='', default=30,
        help=('Minimal coverage to analyse query result. Matches below this threshold '
            'will not be considered'
            + ' (default: 30)')
    )

    optionalNamed.add_argument(
        '-kw', '--keywords', dest='keywords',
        metavar='[\"hypothetical,unspecified,fragment'
                ',partial,unknown,fragemnt\"]', default=str("hypothetical,unspecified,fragment,"
                                                            "partial,unknown,fragemnt"),
        help=('Keywords to search for hypothetical annotations. Please, pass each word followed by comma,'
                +' whitout spaces')
    )

    optionalNamed.add_argument(
        '-pos', '--positivity', dest='pos',
        metavar='', default=60,
        help=('Minimal positivity to transfer annotation. If a query has results below this threshold '
            'it will be classified as hypothetical'
            + ' (default: 60)')
    )

    optionalNamed.add_argument(
        '-t', '--threads', dest='threads',
        metavar='', type=int, default=20,
        help='number of threads [int] (default: 20)'
    )

    optionalNamed.add_argument(
        '-max_target_seqs', dest='hsps',
        metavar='', type=int, default=10,
        help='max_target_seqs flag from blastp [int] (default: 10)'
    )

    optionalNamed.add_argument(
        '-evalue', dest='evalue',
        metavar='', type=float, default=0.00001,
        help='evalue flag from blastp [int] (default: 0.00001)'
    )

    # custom [--help] argument
    optionalNamed.add_argument(
        '-h', '-help', '--help',
        action='help',
        default=argparse.SUPPRESS,  # hidden argument
        help='It\'s going to be legen - wait for it - dary!'
    )

    optionalNamed.add_argument(
        '-customsep', dest='customsep',
        metavar='\\t \\s |', default="|",
        help=('Custom separator for specifiedDB when is not a pattern of NR/Trembl/Eupathdb\
            Default is Eupathdb pattern')
    )

    optionalNamed.add_argument(
        '-customcolumn', dest='customcolumn',
        metavar='', default=5, type=int,
        help=('Custom column that contains protein annotation for specifiedDB when is not a pattern of NR/Trembl/Eupathdb\
            Default is Eupathdb pattern')
    )

    return parser

class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        temp_linebuf = self.linebuf + buf
        self.linebuf = ''
        for line in temp_linebuf.splitlines(True):
            if line[-1] == '\n':
                self.logger.log(self.log_level, line.rstrip())
            else:
                self.linebuf += line

    def flush(self):
        if self.linebuf != '':
            self.logger.log(self.log_level, self.linebuf.rstrip())
        self.linebuf = ''


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    filename="SimilarityAnalysis.log",
    filemode='a'
)

stderr_logger = logging.getLogger('Blast')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl

# --------------------------------------------------------------------------

'''---SOFTWARE SETTINGS------------------------------------------------------'''

class hit:

    def __init__(self, desc, bitscore):
        self.desc = desc
        self.bitscore = bitscore

    def __lt__(self, other):
        return self.bitscore > other.bitscore


def blast(blastp, arq1, arq2, db, hsps, evalue, logger, threads):
    datab = str(db)
    fmt = str("\"6 qseqid sseqid sacc bitscore"
              + " evalue ppos pident qcovs stitle\"")

    command = f"{blastp} -query {arq1} -out {arq2}" \
                    f" -db {datab} -evalue {evalue}" \
                    f" -outfmt {fmt}" \
                    f" -max_target_seqs {hsps}" \
                    f" -num_threads {str(threads)}"
    logger.debug(command)
    subprocess.getoutput(command)


# Function to close log and quit AnnotaPipeline if some expected file/parameter cant be found
def log_quit(logger):
    logger.info("Exiting")
    logging.shutdown()
    sys.exit(1)


def temporary_query(arq):
    # temporary adding a line to the BLAST analysis
    #   so it accounts for the last query found by the BLAST algorithm
    try:
        temp = arq[-1].split("\t")
        del temp[0]
        temp.insert(0, "QueryTemp")
        arq.append("\t".join(temp))
        # Index error ocours when Interproscan returns no results, as consequence, arq is empty, and split empty file is not allowed
    except IndexError:
        arq.append("\t".join("QueryTemp"))


def check_query(full_line_list, coverage, word_list, id, pos, list_classification, list_annot, list_desc, description):
    if float(full_line_list[7]) > float(coverage):
        if not any(word.lower() in description.lower() for word in word_list):
            if float(full_line_list[5]) >= float(pos) and float(full_line_list[6]) >= float(id):
                # If annotation is strong, is considered as non_hypothetical
                list_classification.append("non_hypothetical")
                # Store desc and bitscore
                list_annot.append(hit(str(description), float(full_line_list[3])))
                list_desc.append(description)
            else:
                list_classification.append("hypothetical")
        else:
            list_classification.append("hypothetical")
    else:
        pass


# Function to check if file was generated. It helps if AnnotaPipeline crash
def check_file(file, logger):
    logger = logging.getLogger('Blast')
    if os.path.isfile(file) == 0:
        logger.error(f"File {str(file)} does not exist, please check command line for blastp execution")
        log_quit(logger)
    elif os.path.getsize(file) == 0:
        logger.error(f"File {str(file)} is empty, this is uncommon for a blastp search with a set of proteins")
        logger.warning("AnnotaPipeline can't go on with this uncertainty.")
        logger.warning("Check command Blast line execution to find out what happened")
        logger.info("Exiting")
        logging.shutdown()
        sys.exit(1)


def define_db(args, logger):
    # check dbtype to get pattern correctly
    if args.nr is not None:
        dbtype = "nr"
        secondary_db = args.nr
    elif args.trembl is not None:
        dbtype = "trembl"
        secondary_db = args.trembl
    elif args.specificdb is not None:
        dbtype = "specificdb"
        secondary_db = args.specificdb
    else:
        logger.error("Can't find any secondary database")
        sys.exit(1)
    return dbtype, secondary_db


# Get patten according to database
def get_pattern(query, dbtype, customsep, customcolumn, logger):
    if dbtype == "nr":
        # split line by \t > separate columns > each line becomes a list
        fields = query.split("\t")
        desc = fields[8]
        try:
            desc = re.search(r'\s(.*?)\s\[.*', desc).group(1)
        # if regex fail, catch annotation
        except AttributeError:
            desc = desc.replace("\n","")
        seqname = fields[0]
    elif dbtype == "trembl":
        fields = query.split("\t")
        title = fields[-1]  # get description
        title_split = title.split(" ", 1)[-1]  # get last part of description
        desc = title_split.split("OS=")[0].strip().rstrip()  # get only description
        seqname = fields[0]
    elif dbtype == "specificdb":
        fields = query.split("\t")
        # 8 is the column for annotaion in blast results
        description = fields[8].split(str(customsep))
        desc = description[int(customcolumn)].replace("transcript_product=", "")
        seqname=fields[0]
    else:
        logger.error("Wrong dbtype - exiting")
        sys.exit(1)

    return seqname, desc.strip(), fields


def parser_blast(basename, result_blast, identidade, positividade, cov, dbtype, keyword_list, customsep, customcolum):
    result_blast_file = open(str(result_blast), "r").read().splitlines()
    hyp = open(f"{str(basename)}_hypothetical_products.txt", "w")
    nhyp = open(f"{str(basename)}_annotated_products.txt", "a")
    all_anot = open(f"{str(basename)}_SpecifiedDB_annotations.txt", "w")
    # temporary adding a line
    #   so it accounts for the last query found by the BLAST analysis
    temporary_query(result_blast_file)
    # creating the lists and counter that will be used
    #   to make sure the script goes through each HSP in every query
    # it's important that these lists are set back to NULL
    #   and the counter is set to zero before we start
    old_id = result_blast_file[0].split("\t")  # recebe a primeira query para começar a contagem
    old_id = old_id[0]
    annots = []
    classification = []
    desc_list = []

    for query in result_blast_file:
        new_id, desc, fields = get_pattern(query, dbtype, customsep, customcolum, logger)
        # defining which file will receive each HSP depending on the counter number
        #   the script will write each HSP on its corresponding .txt file
        # IMPORTANT: the first time this loop runs it will add an empty line ("\n")
        #            to the first line of the hyp_file.txt
        if old_id != new_id:
            if "non_hypothetical" in ' '.join(classification):
                nhyp.write(f"{str(old_id)}\t")
                # Sort annotations by bitscore
                annots.sort()
                # Get best identity, first position of array
                nhyp.write(f"{str(annots[0].desc)}\n")
                all_anot.write(f"{old_id}\t{len(desc_list)} Annotation(s): [{';'.join(desc_list)}]\n")
            else:
                hyp.write(f"{str(old_id)}\n")
            # this just resets the count back to zero, before it starts again
            classification.clear()
            annots.clear()
            desc_list.clear()
            # check first query of new ID
            check_query(fields, cov, keyword_list, identidade, positividade, 
                        classification, annots, desc_list, desc)
        else:
            check_query(fields, cov, keyword_list, identidade, positividade, 
                        classification, annots, desc_list, desc)
        # saving the information that will be written in the .txt files
        old_id = new_id

    hyp.close()
    nhyp.close()
    all_anot.close()


def process_swiss(basename, protein_seq, swiss_out, identidade, positividade, cov, keyword_list):
    # --------------------------Parser ----------------------------------------------------
    swiss = open(str(swiss_out), "r").read().splitlines()

    nhyp = open(f"{str(basename)}_annotated_products.txt", "w")
    swiss_anot = open(f"{str(basename)}_SwissProt_annotations.txt", "w")
    # temporary adding a line
    #   so it accounts for the last query found by the BLAST analysis
    temporary_query(swiss)

    # creating the lists and counter that will be used
    #   to make sure the script goes through each HSP in every query
    # it's important that these lists are set back to NULL
    #   and the counter is set to zero before we start
    old_id = swiss[0].split("\t")  # recebe a primeira query para começar a contagem
    old_id = old_id[0]
    nhyp_list = []
    classification = []
    desc = []
    annots = []

    # loop starting and parsing preparation
    for query in swiss:
        # split line by \t > separate columns > each line becomes a list
        line_split = query.split("\t")
        title = line_split[-1]  # get description
        title_split = title.split(" ", 1)[-1]  # get last part of description
        description = title_split.split("OS=")[0].strip().rstrip()  # get only description
        new_id = line_split[0]
        # defining which file will receive each HSP depending on the counter number
        #   the script will write each HSP on its corresponding .txt file
        # IMPORTANT: the first time this loop runs it will add an empty line ("\n")
        #            to the first line of the hyp_file.txt
        if old_id != new_id:
            if "non_hypothetical" in ' '.join(classification):
                nhyp.write(f"{str(old_id)}\t")
                # Sort annotations by bitscore
                annots.sort()
                # Get best identity, first position of array
                nhyp.write(f"{str(annots[0].desc)}\n")

                nhyp_list.append(str(old_id))

                swiss_anot.write(f"{old_id}\t{len(desc)} Annotation(s): [{';'.join(desc)}]\n")

            desc.clear()
            classification.clear()
            annots.clear()
            # check first query of new ID
            check_query(line_split, cov, keyword_list, identidade, positividade,
                        classification, annots, desc, description)
        else:
            check_query(line_split, cov, keyword_list, identidade, positividade,
                        classification, annots, desc, description)
        # saving the information that will be written in the .txt files
        old_id = new_id

    # remove HSPs found by SwissProt from the original fasta_file input
    fasta = open(str(protein_seq), "r").read().split(">")

    for id_list in nhyp_list:
        for seq in fasta:
            if id_list in seq:
                fasta.remove(seq)

    new_fasta = open(f"{str(basename)}_BLASTp_AA_SwissProted.fasta", "w")
    new_fasta.write(">".join(fasta))
    new_fasta.close()
    swiss_anot.close()
    nhyp.close()


def no_hit(basename, blast6):

    # =============================== Parser sequences with no hit =============================
    # Get hit headers
    list_hit = set([line.strip().split()[0] for line in open(blast6, "r")])

    # Get all headers
    list_all = [
        line.strip().replace(">", "")
        for line in open(f"{str(basename)}_BLASTp_AA_SwissProted.fasta", "r")
        if line.startswith(">")
    ]

    no_hit_file = open(f"{str(basename)}_no_hit_products.txt", "w")
    for annotated in list_hit:
        if annotated in list_all:
            list_all.remove(annotated)
    if len(list_all) > 0:
        no_hit_file.write("\n".join(list_all) + "\n")
    no_hit_file.close()

    # =========================================================================================

def swiss_run(blastp, arq1, arq2, db, hsps, evalue, logger, threads):
    logger.info("Running BLAST against SwissProt")
    blast(blastp, arq1, arq2, db, hsps, evalue, logger, threads)
    logger.info("Running parser SwissProt")


def main():
    # arguments saved here
    parser = cli()
    args = parser.parse_args()
    # ----------------------- Create LogFile ------------------------------------
    logger = logging.getLogger('Blast')
    '''---Keywords-------------------------------------------------------------'''

    # defining the keywords that will be used
    #   to separate each HSP found in the BLAST output_file.txt:
    keyword_list = args.keywords.split(",")
    # ----------------------Redirect STDOUT and STDERR to logfile--------------
    dbtype, second_db = define_db(args, logger)
    # Run BLAST against swissprotDB
    swiss_out = f"{str(args.basename)}_BLASTp_AAvsSwissProt.outfmt6"
    process_swiss(args.basename, args.seq, swiss_out, args.id, args.pos, args.cov, keyword_list)
    # Secondary database
    odb_out_name = f"{str(args.basename)}_BLASTp_AAvsSpecifiedDB.outfmt6"
    logger.info(f"Running BLAST against {dbtype}")
    blast(blastp=args.blastp, arq1=f"{args.basename}_BLASTp_AA_SwissProted.fasta", arq2=odb_out_name, db=second_db, hsps=args.hsps, evalue=args.evalue, logger=logger, threads=args.threads)
    # check file for secondary database
    # -----------------------------
    check_file(odb_out_name, logger)
    # ------------------------------
    logger.info(f"Running parser {dbtype}")
    parser_blast(basename=args.basename, result_blast=odb_out_name, identidade=args.id, positividade=args.pos, cov=args.cov,dbtype=dbtype,keyword_list=keyword_list, customsep=args.customsep, customcolum=args.customcolum)
    logger.info("Parser blast done")
    # -------------No hit-----------
    logger.info(f"Identifying proteins with no hits in Swissprot and {dbtype} databases")
    no_hit(str(args.basename), odb_out_name)
    # ------------------------------
    logger.info("Blastp_parser is Finished")


if __name__ == '__main__':
    sys.exit(main())
#!/usr/bin/python3

import re
import logging
import os
import argparse
import sys

def cli():
    # ---------------Parser arguments ----------------
    parser = argparse.ArgumentParser(
        add_help=False,  # removes original [--help]
        description='''    
        Script to parser Interproscan, RPSblast and HMMer results.
        WARNING: Results from Coils, Gene3D and MobiDBLite won't be parsed
        ''',
        epilog="""And shall the hopeful words bring love inside your heart ...""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    requiredNamed = parser.add_argument_group('required arguments')
    optionalNamed = parser.add_argument_group('optional arguments')

    # mandatory arguments
    #   type (default): string
    requiredNamed.add_argument(
        '-ipr_annot', dest='ipr_annot',
        metavar='[InterProScan_Output_annotated.gff3]',
        help='InterProScan_Input',
        required=True
    )

    requiredNamed.add_argument(
        '-ipr_hyp', dest='ipr_hyp',
        metavar='[InterProScan_Output_hyphotetical.gff3]',
        help='InterProScan_Input',
        required=True
    )


    requiredNamed.add_argument(
        '-hmm', '--hmmscan', dest='hmm',
        metavar='[HMMSCAN_Output.txt]',
        help='HMMSCAN_Input',
        required=True
    )

    requiredNamed.add_argument(
        '-rpsblast', '--rpsblast', dest='rpsblast',
        metavar='[RPSblast_Output.txt]',
        help='RPSblast_Input',
        required=True
    )

    requiredNamed.add_argument(
        '-basename', '--basename', dest='basename',
        metavar='[It\'s a boy, and will be called Jonas]',
        help='basename',
        required=True
    )

    # custom [--help] argument
    optionalNamed.add_argument(
        '-h', '-help', '--help',
        action='help',
        default=argparse.SUPPRESS,  # hidden argument
        help='It\'s going to be legen - wait for it - dary!'
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
    filename="FunctionalAnnotation.log",
    filemode='a'
)

stderr_logger = logging.getLogger('Functional Annotation')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl

# --------------------------------------------------------------------------


def parser_interproscan(arq_entrada, arq_ipr, arq_saida):
    entrada = open(str(arq_entrada), "r").read().split("##FASTA")  # SPLITTING THE GFF3 FILE IN TWO CATEGORIES
    interp = entrada[0].split("##sequence-region")  # WE'LL BE USING ONLY THE FIRST PART OF THE GFF3 OUTPUT FILE
    del interp[0]
    ipr = open(str(arq_ipr), "a")
    output = open(str(arq_saida), "a")

    db_list = ["Coils", "Gene3D", "MobiDBLite"]

    # TREATING EACH QUERY, RETRIEVING THE INFORMATION THAT WILL BE WRITTEN ON THE FIRST OUTPUT FILE
    for seq_reg in interp:
        seq_reg = seq_reg.splitlines()
        for linha in seq_reg:
            if linha == seq_reg[0]:
                linha = linha.split(" ")
                del linha[0]
            elif linha == seq_reg[1]:  # IGNORING THE FIRST LINE ON EACH GROUP OF QUERIES, AS IT'S NON-INFORMATIVE
                pass
            else:
                ontology = str(None)
                anotation_db = str(None)
                name = str(None)
                interpro = str(None)
                linha = linha.split("\t")
                name_subject = linha[0]
                db = linha[1]
                if not any(unwanted in db for unwanted in db_list):
                    correct_db = db
                    anotation = linha[-1].split(";")
                    for query in anotation:
                        if "Ontology" in query:
                            ontology = query.replace('"', "").replace("Ontology_term=", "")
                        if "signature_" in query:
                            anotation_db = query.replace("signature_desc=", "")
                        if "Name" in query:
                            name = query.replace('"', "").replace("Name=", "")
                        if "Dbxref" in query:
                            interpro = query.replace('"', "").replace("Dbxref=", "")
                    ipr.write(f"{name_subject}\t{correct_db}\t{name}\t{anotation_db}\t{interpro}\t{ontology}\n")
                    output.write(f"{name_subject}\t{correct_db}\t{name}\t{anotation_db}\t{interpro}\t{ontology}\n")
    output.close()
    ipr.close()


def pfam_format(arq_entrada, arq_saida):
    input = open(str(arq_entrada), "r").read().splitlines()
    output = open(str(arq_saida), "w")
    del input[0:3] 
    del input[-10:]  
    for line in input:
        line = re.sub(r'\s+', ' ', line).split(" ")  
        aux = " ".join(line[18:]) 
        del line[18:]  
        line.append(aux) 
        output.write("\t".join(line) + "\n")
    output.close()


def parser_pfam(arq_entrada, arq_saida):
    input = open(str(arq_entrada), "r").read().splitlines()
    output = open(str(arq_saida), "a")
    for line in input:
        line = line.strip()
        line = line.split("\t")
        query = line[2]
        db = "Pfam"  # ESPECIFICALLY WRITING THIS, AS THERE ARE NO OTHER DBs ON THIS PART OF THE ANALYSIS
        ontologia = str(None)
        anotacao_db = line[-1]
        name = line[1]
        interpro = str(None)
        output.write(f"{query}\t{db}\t{name}\t{anotacao_db}\t{interpro}\t{ontologia}\n")
    output.close()


def parser_rpsblast(arq_entrada, arq_rps, arq_saida):
    input = open(str(arq_entrada), "r").read().splitlines()
    rps = open(str(arq_rps), "w")
    output = open(str(arq_saida), "a")
    for line in input:
        hit = line.split("\t")
        query = hit[0]
        db = "CDD"
        name = hit[1]  # Acesso_DB
        anotation = hit[-1]
        interpro = str(None)
        ontology = str(None)
        rps.write(f"{query}\t{db}\t{name}\t{anotation}\t{interpro}\t{ontology}\n")
        output.write(f"{query}\t{db}\t{name}\t{anotation}\t{interpro}\t{ontology}\n")
    output.close()
    rps.close()


def sort_arq(arq_entrada, arq_saida):
    hits = open(str(arq_entrada), "r")
    ordered = open(str(arq_saida), "w")
    ordered.write("ID\tDB\tDB_ACCESS\tDESCRIPTION\tIPR\tGO\n")
    lines = hits.readlines()
    lines.sort()
    for line in lines:
        ordered.write(str(line))
    ordered.close()


def main():
    parser=cli()
    # arguments saved here
    args = parser.parse_args()
    logger = logging.getLogger('Functional Annotation')
    # ------------ Hipothetical ---------------------------------------
    # Parse interproscan file
    parser_interproscan(args.ipr_hyp, f"InterProScan_Out_{args.basename}.tsv", f"Temp_{args.basename}.tsv")
    logger.info("InterProScan parser done")
    # Parse HMMer file
    pfam_format(args.hmm, f"Hmmscan_Out_{args.basename}.tsv")
    logger.info("Hmmscan format done")
    parser_pfam(f"Hmmscan_Out_{args.basename}.tsv", f"Temp_{args.basename}.tsv")
    logger.info("Hmmscan parser done")
    # Parse RPSblast file
    parser_rpsblast(args.rpsblast, f"RPSblast_Out_{args.basename}.tsv", f"Temp_{args.basename}.tsv")
    logger.info("RPSblast parser done")
    # Group and sort 
    sort_arq(f"Temp_{args.basename}.tsv", f"{args.basename}_Grouped_Hypothetical_Information.tsv")
    logger.info("Sorting queryes in files")

    # ------------ Annotated -----------------------------------------
    # Save annotated proteins in Interpro_Out
    parser_interproscan(args.ipr_annot, f"InterProScan_Out_{args.basename}.tsv", f"Temp_{args.basename}.tsv")
    # Cleaning the house
    os.system(f"rm Temp_{args.basename}.tsv")
    logger.info("Temporary file removed")
    logger.info("Functional Annotation step is completed")


if __name__ == '__main__':
    sys.exit(main())
#!/usr/bin/python3

##############################################
###   LOAD CONFIGURATION FROM .yaml FILE   ###
##############################################

# A AVENTURA VAI COMEÇAR -------------------------------------------------------

import yaml

# IMPORT CONFIG FILE -----------------------------------------------------------

with open("AnnotaPipeline.yaml", "r") as stream:
    try:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        print(exc)


# get element from list
#print(threads)

kallisto_section = config["kallisto"]
print(kallisto_section.get('rna-seq'))
#!/usr/bin/python3.5
 
#Author:        Sasan Bahadaran
#Date:          5/1/17
#Organization:  Commerce Data Service
#Description:   This is a utility class which contains functions
#for reading parameters from the various configuration files

import configparser

# read configuration parameters from config file
def getAppConfigParam(section, key):
    config = configparser.ConfigParser()
    config.read('app_config.ini')
    return config[section][key]

# construct page search key from config file params
def get_key_vals(wiki_lookup_key, val):
    val_key = ''
    for item in wiki_lookup_key['api_cols']:
        val_key += val[item]
    key = wiki_lookup_key['beg_val']+val_key+wiki_lookup_key['end_val']
    return key

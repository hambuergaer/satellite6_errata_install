#!/usr/bin/python
#
#############################################################################################
# Scriptname          : install_errata.py
# Scriptauthor        : Frank Reimer
# Creation date       : 2016-07-18
# License             : GPL v. 3
# Source              : https://github.com/hambuergaer/satellite6_errata_install
# Issues              : https://github.com/hambuergaer/satellite6_errata_install/issues
# 
#############################################################################################
#
# Description:
#
# This script helps you to install Red Hat errata packages on your content hosts depending
# on the lifecycle environment where a host is assigned to.
#
# If you don`t pass the option "--update-enhancement-errata" only security and bugfix errata
# will be applied to your hosts. 
#
# If you don`t pass the option "--update-host" you will only see a summary of applicabel 
# errata per host.
#
# If you pass the option "--write-log" a log file will be written in ".errata_update_logs".
#
#############################################################################################

import json
import sys
import csv
import shlex
import commands
import subprocess
import platform
import os.path
import string
import fileinput
from datetime import datetime
from optparse import OptionParser
from itertools import islice

current_date = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')

# Put a host to this list if applicable errata are present. Aftrewards an Ansible hostfile will be created.
# This can be used to reboot hosts after the Errata update is finished
update_host_via_ansible = []

# Logging class with different colors per type
class log:
	HEADER	= '\033[0;36m'
	ERROR	= '\033[1;31m'
	INFO	= '\033[0;32m'
	WARN	= '\033[1;33m'
	SUMM	= '\033[1;35m'
	END	= '\033[0m'

def verify_organization(organization):
	cmd_get_orgas = hammer_cmd + " --csv organization list"
	try:
		perform_cmd = subprocess.Popen(cmd_get_orgas, shell=True, stdout=subprocess.PIPE)
		organizations = perform_cmd.stdout.read()
		for line in  islice(organizations.strip().split("\n"), 1, None):	# print output without CSV header
			if organization in line:	
				return True
			else:
				return False

	except:
		print log.ERROR + "ERROR: did not find organization " + organization + log.END
		sys.exit(1)

def verify_lifecycle(lifecycle_environment):
	cmd_get_lifecycle = hammer_cmd + " --csv lifecycle-environment list --organization " + ORGANIZATION
	try:
		perform_cmd = subprocess.Popen(cmd_get_lifecycle, shell=True, stdout=subprocess.PIPE)
		lifecycle = perform_cmd.stdout.read()
		for line in islice(lifecycle.strip().split("\n"), 1, None):	# print output without CSV header
			if lifecycle_environment in line:	
				return True
				break

	except:
		print log.ERROR + "ERROR: did not find lifecycle environment " + lifecycle_environment + log.END

def get_trange(hostname):
	cmd_get_trange = hammer_cmd + " --csv host info --name " + hostname
	try:
		perform_cmd = subprocess.Popen(cmd_get_trange, shell=True, stdout=subprocess.PIPE)
		hostinfo = perform_cmd.stdout.read()
		for line in islice(hostinfo.strip().split("\n"), 1, None):	# print output without CSV header
			if TRANGE in line:	
				return True
				break

	except:
		print log.ERROR + "ERROR: your host seems not to be attached to trange " + TRANGE + log.END

def get_list_of_hosts_in_lifecycle_environment(lifecycle_environment):
	list_of_hosts = []
	cmd_get_list_of_hosts_in_lifecycle_environment = hammer_cmd + " --csv content-host list --lifecycle-environment "+ lifecycle_environment +" --organization " + ORGANIZATION
	try:
		perform_cmd = subprocess.Popen(cmd_get_list_of_hosts_in_lifecycle_environment, shell=True, stdout=subprocess.PIPE)
		get_hosts = perform_cmd.stdout.read()
		for line in islice(get_hosts.strip().split("\n"), 1, None):	# print output without CSV header
			list_of_hosts.append(line)
		return list_of_hosts

	except:
		print log.ERROR + "ERROR: did not find any host in lifecycle environment " + lifecycle_environment + log.END

def get_list_of_applicable_errata(hostname):
	list_of_errata = []
	if not UPDATE_ENHANCEMENT_ERRATA:
		cmd_get_list_of_errata = hammer_cmd + " --csv content-host errata list --content-host " + hostname + " --organization " + ORGANIZATION + " | grep -v enhancement "
	else:
		cmd_get_list_of_errata = hammer_cmd + " --csv content-host errata list --content-host " + hostname + " --organization " + ORGANIZATION
	try:
		perform_cmd = subprocess.Popen(cmd_get_list_of_errata, shell=True, stdout=subprocess.PIPE)
		errata = perform_cmd.stdout.read()
		for line in islice(errata.strip().split("\n"), 1, None):	# print output without CSV header
			list_of_errata.append(line)
		return list_of_errata

	except:
		print log.ERROR + "ERROR: did not find any errata for content host " + hostname + log.END

def update_errata_on_host(hostname):
	errata_ids = []
	for errata in get_list_of_applicable_errata(hostname):
                        errata_ids.append(errata.split(",")[1])
	list_of_errata_ids = str(errata_ids).strip('[]').replace(' ','').replace("'",'')
	cmd_update_errata_on_host = hammer_cmd + " content-host errata apply --content-host " + hostname + " --errata-ids " + list_of_errata_ids + " --organization " + ORGANIZATION
	try:
		perform_cmd = subprocess.Popen(cmd_update_errata_on_host, shell=True, stdout=subprocess.PIPE)
		install_errata = perform_cmd.stdout.read()

	except:
		print log.ERROR + "ERROR: was not able to update errata on host "  + hostname + log.END

def write_hosts_to_ansible_file():
	ansible_folder = os.environ['HOME']+"/ansible/"
	if not os.path.exists(ansible_folder):
        	os.makedirs(ansible_folder)
	filename = os.environ['HOME']+"/ansible/"+LIFECYCLE_ENVIRONMENT+"-"+TRANGE
	print filename
	with open(filename, 'a') as file:
		for line in update_host_via_ansible:
			print line
			file.write(line)


################################## OPTIONS PARSER AND VARIABLES ##################################

parser = OptionParser()
parser.add_option("--satellite-server", dest="sat6_fqdn", help="FQDN of Satellite - omit https://", metavar="SAT6_FQDN")
parser.add_option("--lifecycle-environment", dest="lifecycle_environment", help="Lifecycle environment should be one of dev/test/preprod/prod", metavar="LIFECYCLE_ENVIRONMENT")
parser.add_option("--organization", dest="organization", help="Satellite 6 organization", metavar="ENVIRONMENT")
parser.add_option("--update-host", dest="update_host", action="store_true", help="Update existing host")
parser.add_option("--write-log", dest="write_log", action="store_true", help="Write log file to .errata_update_logs")
#parser.add_option("--update-security-errata", dest="update_security_errata", action="store_true", help="Update security errata only")
#parser.add_option("--update-bugfix-errata", dest="update_bugfix_errata", action="store_true", help="Update bugfix errata only")
parser.add_option("--update-enhancement-errata", dest="update_enhancement_errata", action="store_true", help="Update enhancement errata only")
parser.add_option("--trange", dest="trange", help="Trange where you want to add your host [tr01 / tr02] ", metavar="TRANGE")
parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output")
(options, args) = parser.parse_args()

if not ( options.sat6_fqdn and options.lifecycle_environment and options.organization ):
    print log.ERROR + "You must specify at least Satellite fqdn, lifecycle environment and organization. See usage:\n" + log.END
    parser.print_help()
    print '\nExample usage: ./install_errata.py --satellite-server <your-satellite-server> --lifecycle-environment <dev/test/preprod/prod> --organization <your-organization> [--update-host] [--list-errata-per-host]'
    sys.exit(1)
else:
    if options.trange == "tr01" or options.trange == "tr02" :
	TRANGE=options.trange
    else:
	print log.ERROR + "ERROR: you need to define the trange where you want to assign your host. See usage." + log.END
	sys.exit(1)
    SAT6_FQDN = options.sat6_fqdn
    ORGANIZATION  = str(options.organization)
    LIFECYCLE_ENVIRONMENT = str(options.lifecycle_environment)
    hammer_cmd = str("/usr/bin/hammer ")

if options.verbose:
    VERBOSE=True
else:
    VERBOSE=False

if options.update_host:
    UPDATE_HOST=True
else:
    UPDATE_HOST=False
'''
if options.update_security_errata:
    UPDATE_SECURITY_ERRATA=True
else:
    UPDATE_SECURITY_ERRATA=False

if options.update_bugfix_errata:
    UPDATE_BUGFIX_ERRATA=True
else:
    UPDATE_BUGFIX_ERRATA=False
'''
if options.update_enhancement_errata:
    UPDATE_ENHANCEMENT_ERRATA=True
else:
    UPDATE_ENHANCEMENT_ERRATA=False

# Define errata update log file
if options.write_log:
    if not os.path.exists("errata_update_logs"):
	os.makedirs("errata_update_logs")
    sys.stdout = open("errata_update_logs/errata_update_summary_"+str(current_date) + ".log","w")

if VERBOSE:
    print log.SUMM + "### Verbose output ###" + log.END
    print "CLIENT FQDN - %s" % CLIENT_FQDN
    print "ORGANIZATION - %s" % ORGANIZATION

################################## MAIN ##################################

## Verify some needed parameters
if verify_organization(ORGANIZATION) and verify_lifecycle(LIFECYCLE_ENVIRONMENT):
	print log.SUMM + "Start date: " + log.END + current_date + "\n"
	if UPDATE_HOST:
		print log.SUMM + "Update hosts: " + log.END + "true \n"
	else:
		print log.SUMM + "Update hosts: " + log.END + "false \n"
		
	print log.INFO + "Theses are the hosts assigned to lifecycle environment " + log.SUMM + LIFECYCLE_ENVIRONMENT + log.INFO + " with their applicable errata:" + log.END + "\n"
	for host in get_list_of_hosts_in_lifecycle_environment(LIFECYCLE_ENVIRONMENT):
		if get_trange(host.split(",")[1]):
			print log.SUMM + "===> " + host.split(",")[1] + " <=== " + log.END
			print log.INFO + "Hostname : " + log.END + host.split(",")[1] + log.INFO + " Applicable errata: " + log.END + host.split(",")[2]
			for errata in get_list_of_applicable_errata(host.split(",")[1]):
				print log.INFO + "Errata ID: " + log.END + errata.split(",")[0] + log.INFO + " Errata Name: " + log.END + errata.split(",")[1] + log.INFO + " Errata Type: " + log.END + errata.split(",")[2] + log.INFO + " \t Description: " + log.END + errata.split(",")[3]
			if UPDATE_HOST and int(host.split(",")[2]) != 0:
				print log.INFO + "==> Start errata update now." + log.END
				update_errata_on_host(host.split(",")[1])
				update_host_via_ansible.append(host.split(",")[1])
				write_hosts_to_ansible_file()
			print "\n"
	

# Close log file
sys.stdout.close()

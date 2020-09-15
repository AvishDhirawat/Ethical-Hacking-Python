#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 8 July 2020

import subprocess
import optparse
import re
#import sys

def get_arguments():
    parser = optparse.OptionParser()
    parser.add_option("-i","--interface", dest = "interface", help = "Interface to change its MAC address")
    parser.add_option('-m', '--mode', dest="mode", help = "Managed or Monitor")
    (options, arguments) = parser.parse_args()

    if not options.interface:
        # Code to handle error
        parser.error("[-] Please specify an interface, use --help for more info")
    elif not options.mode:
        # Code to handle error
        parser.error("[-] Please specify the Wireless Mode, use --help for more info")

    return options
    #interface = options.interface
    #mode = options.mode
    #l = sys.argv
    #interface = l[1]
    #mode = l[2]

    #interface = input("Interface > ")
    #mode = input("New Mac > ")

def change_mode(interface,mode):
    print("[+] Changing Wireless Mode for "+ interface + " to "+ mode)

    #Simple but Vulnerable Method
    #subprocess.call("ifconfig "+ interface +" down", shell = "True")
    #subprocess.call("ifconfig "+ interface +" hw ether "+ mode, shell = "True")
    #subprocess.call("ifconfig "+ interface +" up", shell = "True")
    #subprocess.call("ifconfig "+ interface, shell = "True")

    #Non Vulnerable Method
    subprocess.call(['ifconfig', interface, 'down'])
    subprocess.call(['airmon-ng', 'check', 'kill'])
    #subprocess.call(['ifconfig', interface, 'hw', 'ether', mode])
    subprocess.call(['iwconfig', interface, 'mode', mode]) #change the mode to monitor
    subprocess.call(['ifconfig', interface, 'up'])
    subprocess.call(['service', 'NetworkManager', 'restart'])
    subprocess.call(['nmcli', 'networking', 'on'])
    #subprocess.call(['ifconfig', interface])

def get_current_mode(interface):
    iwconfig_result = subprocess.check_output(["iwconfig", interface])
    mode_search_result = re.search(r'Mode:[a-zA-z]*', str(iwconfig_result))
    curr_mode = mode_search_result.group(0).split(':')[1]
    return curr_mode

options = get_arguments()
current_mode = get_current_mode(options.interface)

print("Current Mode = "+ str(current_mode))

change_mode(options.interface, options.mode)

if get_current_mode(options.interface) == options.mode :
    print("[+] Wireless Mode was successfully changed to "+ get_current_mode(options.interface))
else:
    print("[-] Wireless Mode did not get changed.")

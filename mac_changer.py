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
    parser.add_option('-m', '--mac', dest="new_mac", help = "New MAC address")
    (options, arguments) = parser.parse_args()

    if not options.interface:
        # Code to handle error
        parser.error("[-] Please specify an interface, use --help for more info")
    elif not options.new_mac:
        # Code to handle error
        parser.error("[-] Please specify an new MAC, use --help for more info")

    return options
    #interface = options.interface
    #new_mac = options.new_mac
    #l = sys.argv
    #interface = l[1]
    #new_mac = l[2]

    #interface = input("Interface > ")
    #new_mac = input("New Mac > ")

def change_mac(interface,new_mac):
    print("[+] Changing MAC address for "+ interface + " to "+ new_mac)

    #Simple but Vulnerable Method
    #subprocess.call("ifconfig "+ interface +" down", shell = "True")
    #subprocess.call("ifconfig "+ interface +" hw ether "+ new_mac, shell = "True")
    #subprocess.call("ifconfig "+ interface +" up", shell = "True")
    #subprocess.call("ifconfig "+ interface, shell = "True")

    #Non Vulnerable Method
    subprocess.call(['ifconfig', interface, 'down'])
    subprocess.call(['ifconfig', interface, 'hw', 'ether', new_mac])
    #subprocess.call(['iwconfig', interface, 'mode', 'monitor']) #change the mode to monitor
    subprocess.call(['ifconfig', interface, 'up'])
    #subprocess.call(['ifconfig', interface])

def get_current_mac(interface):
        ifconfig_result = subprocess.check_output(["ifconfig", interface])
        #print(ifconfig_result)
        mac_address_search_result = re.search(r'\w\w:\w\w:\w\w:\w\w:\w\w:\w\w', str(ifconfig_result))

        if mac_address_search_result:
            #print(mac_address_search_result.group(0))
            return mac_address_search_result.group(0)
        else:
            print("[-] Could not read MAC address.")

options = get_arguments()
current_mac = get_current_mac(options.interface)
print("Current MAC = "+ str(current_mac))

change_mac(options.interface,options.new_mac)

current_mac = get_current_mac(options.interface)

if current_mac == options.new_mac:
    print("[+] MAC address was successfully changed to "+ current_mac)
else:
    print("[-] MAC address did not get changed.")

# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = """
    name: current_hosts 
    author: Emil Harvey (@ehharvey) <emil.h.harvey@outlook.com>
    version_added: "0.0.1"
    short_description: Creates a dynamic inventory from current hosts on TailScale.
    description: >-
        Creates a dynamic inventory from current hosts on TailScale.
    options:
        plugin:
            description: token that ensures this is a source file for the 'current_hosts' plugin.
            required: false
            choices: 
                - 'current_hosts'
                - "ehharvey.tailscale.current_hosts"
                - "tailscale.current_hosts"
        api_key:
            description: TailScale API key.
            required: false
        overwrite_ansible_host:
            description: Overwrite ansible_host with the IP address of the host.
            required: false
            default: false
            choices:
                - true
                - false
                - ipv4
                - ipv6
                - hostname
                - fqdn
        match_inventory_hostname:
            description: Match existing hosts with this vaiable, used to lookup fact in TailScale API.
            required: false
            default: "hostname"
             
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Literal, Tuple, Union
from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils._text import to_native
import requests

def get_hosts(api_key: str, 
              overwrite_ansible_host: Union[bool, 
                                            Literal["ip",
                                                    "ipv4",
                                                    "ipv6",
                                                    "hostname",
                                                    "fqdn"]] = False,
              match_inventory_hostname: str = "hostname") -> List[dict]:
    
    results = []
    
    devices_request = requests.get(
            url="https://api.tailscale.com/api/v2/tailnet/-/devices",
            headers={
                "Authorization": f"Bearer {api_key}"
                # "Authorization": f"Bearer tskey-api-kXX73L4CNTRL-SL7EZ8i7YibtkM9f5bAqfbzLahMLQjyn3"
            }
        )
        
    devices_json  = devices_request.json()

    for device in devices_json["devices"]:
        # check if the host is already in the inventory
        if match_inventory_hostname not in device:
            raise AnsibleParserError(f"match_inventory_hostname \
                                        '{match_inventory_hostname}' not found in device\n\
                                        device: {device}")

        
        ipv4_address = device["addresses"][0]
        ipv6_address = device["addresses"][1]
        hostname = device["hostname"]
        fqdn = device["name"]

        if overwrite_ansible_host == "ipv4":
            ansible_host = ipv4_address
        elif overwrite_ansible_host == "ipv6":
            ansible_host = ipv6_address
        elif overwrite_ansible_host == "hostname":
            ansible_host = hostname
        elif overwrite_ansible_host == "fqdn":
            ansible_host = fqdn

        # add ansible_host, if not false
        if overwrite_ansible_host:
            if not ansible_host:
                raise AnsibleParserError(f"INTERNAL ERROR: ansible_host is not set")
            
            device["ansible_host"] = ansible_host
        
        results.append(device)
    
    return results
        
    

class InventoryModule(BaseInventoryPlugin):
    NAME = "current_hosts"

    def verify_file(self, path):
        """return true/false if this is possibly a valid file for this plugin to consume"""
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path)

        config = self._read_config_data(path)
        overwrite_ansible_host = config.get("overwrite_ansible_host", False)
        match_inventory_hostname = config.get("match_inventory_hostname", "hostname")
        api_key = config.get("api_key")
        
        if not api_key:
            raise AnsibleParserError("api_key is required")

        devices = get_hosts(api_key=api_key,
                            overwrite_ansible_host=overwrite_ansible_host,
                            match_inventory_hostname=match_inventory_hostname)
        
        inventory.add_group("tailscale")

        for device in devices:
            
            if device[match_inventory_hostname] not in inventory.hosts:
                # add the host to the inventory if it does not exist
                inventory.add_host(device[match_inventory_hostname], "all")
            
 
            inventory.add_child("tailscale", device[match_inventory_hostname])
        
        
            # add all device facts under tailscale key
            inventory.set_variable(device[match_inventory_hostname], 
                                   "tailscale", 
                                   device)

            if overwrite_ansible_host:
                inventory.set_variable(device[match_inventory_hostname], 
                                       "ansible_host", 
                                       device["ansible_host"])
            



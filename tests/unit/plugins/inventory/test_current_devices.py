from plugins.inventory.current_devices import get_hosts
import os
from pathlib import Path


def test_test():
    # change working directory to this file's directory
    os.chdir(Path(__file__).parent)
    api_key = Path("ts-api-key.txt").read_text().strip()
    overwrite_ansible_host = "hostname"
    match_inventory_hostname = "hostname"

    results = get_hosts(api_key, overwrite_ansible_host, match_inventory_hostname)

    results_dict = {d["hostname"]: d["ansible_host"] for d in results}

    assert results_dict["l380-eharvey"] == "l380-eharvey"

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("HETZNER_API_TOKEN")
records_file = Path("records.txt")

def get_ips() -> dict[str,str]:
    """ requests.gets the current ips from icanhazip """
    ips:dict[str,str] = dict()
    try:
        res = requests.get(f"https://ipv4.icanhazip.com")
        ips["A"] = res.text.strip()
        res = requests.get(f"https://ipv6.icanhazip.com")
        ips["AAAA"] = res.text.strip()
        print(f"Current ipv4:{ips['A']}, ipv6:{ips['AAAA']}")
    except Exception as e:
        print(f"Error getting current ips: {e}")
    return ips

def get_records() -> list[str]:
    """ returns the contents of the records file """
    if not records_file.exists():
        print(f"Cant find {records_file}\nCreating empty template")
        with records_file.open("wt") as f:
            f.writelines([
                "# All listed records will be searched for and updated accordingly",
                "# mc.p1gn.com"
            ])
        return []

    records = []
    for line in records_file.open().readlines():
        if not line.startswith("#"):
            records.append(line.strip())
    return records

def get_zone_id(zone_name:str="p1gn.com") -> None | str:
    """ fetches the id of given zone, eg p1gn.com -> jQNNDrq6CH4jwxinvdE4g8 """
    try:
        response = requests.get(
            url="https://dns.hetzner.com/api/v1/zones",
            headers={"Auth-API-Token": TOKEN}
        )
    except Exception as e:
        print(f"Error fetching zones from {zone_name}: {e}")
        return

    try:
        if "message" in response.json():
            print(response.json()["message"])
            return

        for zone in response.json()["zones"]:
            if zone["name"] == zone_name:
                print(f"Got zone id for {zone_name}: {zone['id']}")
                return zone["id"]
    except Exception as e:
        print(f"Error parsing zones: {e}")

def get_record_id(record_name:str, zone_id:str) -> None | dict[str,str]:
    """ fetches the record id of given record, eg mc.p1gn.com -> d226c5615101de6d7b0d556687b0bc91 """
    try:
        response = requests.get(
            url="https://dns.hetzner.com/api/v1/records",
            params={"zone_id": zone_id},
            headers={"Auth-API-Token": TOKEN},
        )
    except Exception as e:
        print(f"Error getting record id: {e}")
        return

    try:
        records = dict()
        for record in response.json()["records"]:
            if record["name"] == record_name:
                records[record["id"]] = record["type"]
        print(f"Got record id(s) for {record_name}: {records}")
        return records
    except Exception as e:
        print(f"Error parsing record id ({record_name = }, {zone_id = }): {e}")

def update_record(record:str):
    """ updates the record while fetching all nessecerry info """
    # format record to record name and zone name
    record_name = record.split(".")[0]
    zone_name = ".".join(record.split(".")[1:])

    # get nessecerry data
    zone_id = get_zone_id(zone_name)
    if zone_id is None: return
    records = get_record_id(record_name, zone_id)
    ips = get_ips()
    if not records or not ips:return

    # put the right ips next to records
    records_with_values:dict[str, tuple[str,str]] = dict()
    for record_id, record_type in records.items():
        records_with_values[record_id] = record_type, ips[record_type]

    # send put request for all records
    for record_id, (record_type, value) in records_with_values:
        try:
            requests.put(
                url=f"https://dns.hetzner.com/api/v1/records/{record_id}",
                headers={
                    "Content-Type": "application/json",
                    "Auth-API-Token": TOKEN
                },
                data=json.dumps({
                    "value": value,
                    "ttl": 3600,
                    "type": record_type,
                    "name": record_name,
                    "zone_id": zone_id
                })
            )
            print(f"updated {record}/{record_type} to {value}")
        except:
            print(f"Error updating {record}")

def main():
    for record in get_records():
        update_record(record)

if __name__ == "__main__":
    main()

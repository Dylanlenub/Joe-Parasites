from pathlib import Path
from itertools import islice
import json
import sys

import methods

REPO_ROOT = Path(__file__).parent.parent
MC_INSTANCE_JSON = REPO_ROOT / "minecraftinstance.json"
MANIFEST_JSON = REPO_ROOT / "manifest.json"

def read_manifest():
    manifest = {}

    if MANIFEST_JSON.exists():
        with MANIFEST_JSON.open(encoding="utf-8") as f:
            manifest = json.load(f)

    return manifest

def fetch_files_data():
    files_data = []
    
    addons_data = methods.parse_instance_addons(MC_INSTANCE_JSON)
    for addon_name, addon_info in addons_data.items():
        files_data.append(dict(islice(addon_info.items(), 0, 4)))

    return files_data

def fetch_instance_data():
    instance_data = {}

    with MC_INSTANCE_JSON.open(encoding="utf-8") as f:
        instance_data = json.load(f)

    return instance_data

def increment_version(version, part="patch"):
    major, minor, patch = version.split(".")
    
    if part == "major":
        return f"{int(major)+1}.0.0"
    elif part == "minor":
        return f"{major}.{int(minor)+1}.0"
    else:
        return f"{major}.{minor}.{int(patch)+1}"

def write_manifest(update="patch"):
    files_data = fetch_files_data()
    instance_data = fetch_instance_data()
    old_manifest = read_manifest()

    old_version = old_manifest.get("version", "0.0.0")
    new_version = increment_version(old_version, update)

    print(f"Incremented manifest version from {old_version} to {new_version}")

    manifest = {
        "minecraft": {
            "version": instance_data.get("gameVersion"),
            "modLoaders": [
                {
                    "id": instance_data.get("baseModLoader").get("name"),
                    "primary": True
                }
            ],
            "recommendedRam": old_manifest.get("minecraft", {}).get("recommendedRam", instance_data.get("allocatedMemory"))
        },
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": old_manifest.get("name", ""),
        "version": new_version,
        "author": old_manifest.get("author", ""),
        "files": files_data,
        "overrides": "overrides"
    }

    MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

if __name__ == "__main__":
    write_manifest()
    
    print(f"Generated {MANIFEST_JSON.relative_to(REPO_ROOT)}\n")

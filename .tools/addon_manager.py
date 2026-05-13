from pathlib import Path
import subprocess
import zipfile
import hashlib
import json
import sys
import re

import methods

REPO_ROOT = Path(__file__).parent.parent
OVERRIDES_DIR = REPO_ROOT / "overrides"
MODS_DIR = OVERRIDES_DIR / "mods"
CONFIG_DIR = OVERRIDES_DIR / "config"
SHADERS_DIR = OVERRIDES_DIR / "shaderpacks"
RESOURCES_DIR = OVERRIDES_DIR / "resourcepacks"

MC_INSTANCE_JSON = REPO_ROOT / "minecraftinstance.json"
ADDONS_INFO_JSON = REPO_ROOT / "addonsinfo.json"

CF_HOST = "public"
PC_HOST = "local"
IGNORED_CONFIGS = [
    CONFIG_DIR / "forge.cfg",
    CONFIG_DIR / "forgeChunkLoading.cfg",
    CONFIG_DIR / "splash.properties"
]

MAX_OUTPUT_LENGTH = 80
HALF_OUTPUT_LENGTH = int(MAX_OUTPUT_LENGTH/2)

_print = print
def print(*args, indent=0, **kwargs):
    if args:
        first_statement = (" " * indent + str(args[0])).ljust(HALF_OUTPUT_LENGTH)
        remaining_statements = (" ".join(str(a) for a in args[1:]))#[:HALF_OUTPUT_LENGTH]
        
        _print(first_statement + remaining_statements, **kwargs)
    else:
        _print(**kwargs)

def load_addons_info():
    if not ADDONS_INFO_JSON.exists():
        return {}
    with open(ADDONS_INFO_JSON) as f:
        return json.load(f)

def save_addons_info(new_info):
    with open(ADDONS_INFO_JSON, "w") as f:
        json.dump(new_info, f, indent=2)

def sync_addons_info():
    print("Syncing addon info...")

    config_outdated = False
    json_changed = False

    current_info = load_addons_info()
    addons_data = methods.parse_instance_addons(MC_INSTANCE_JSON)
    addon_list = addons_data.keys()

    project_lookup = {info["projectID"]: name for name, info in current_info.items()}

    def log_new_addon(name, info):
        new_info = {}
        new_info["projectID"] = info["projectID"]
        new_info["fileID"] = info["fileID"]
        new_info["type"] = info["type"]
        
        if isinstance(info["projectID"], str):
            new_info["isLocal"] = True
        if info["type"] == "mod":
            new_info["configFiles"] = []
        new_info["associatedWith"] = []

        current_info[name] = new_info

    def compare_addon(name, info):
        nonlocal config_outdated
        nonlocal json_changed

        project_id = info["projectID"]
        file_id = info["fileID"]
        locality = PC_HOST if info.get("isLocal") else CF_HOST

        if project_id not in project_lookup:
            log_new_addon(name, info)
            print(f"Installed {locality} {info["type"]}:", f"{name}", indent=2)

            config_outdated = True
            json_changed = True
        else:
            current_name = project_lookup[project_id]
            current_file_id = current_info[current_name]["fileID"]

            action = None
            
            if current_name and current_name != name:
                action = "Renamed"
                current_info[name] = current_info.pop(current_name)
                
            if current_file_id and current_file_id != file_id:
                action = "Updated"
                current_info[name]["fileID"] = file_id
                
                config_outdated = True
            
            if action:
                print(f"{action} {locality} {info["type"]}:", f"{current_name} -> {name}", indent=2)

                if action == "Updated":
                    refresh_mod_config(current_info[name])

                json_changed = True

    def fetch_base_name(file_name):
        result = re.match(r'^[^a-zA-Z0-9]?([a-zA-Z]{2,}(?:[^a-zA-Z0-9](?!(?i:mc))[a-zA-Z]{2,})*)', file_name)
        result = result.group(1) if result else file_name
        return result

    # Compare saved addon data to latest addon data
    for latest_name, latest_info in addons_data.items():
        compare_addon(latest_name, latest_info)

    # Detect any local-only addons
    addon_files = [
        *MODS_DIR.glob('*.jar'), *MODS_DIR.glob('*.jar.disabled'),
        *RESOURCES_DIR.glob('*.zip'), *RESOURCES_DIR.glob('*.zip.disabled'),
        *SHADERS_DIR.glob('*.zip'), *SHADERS_DIR.glob('*.zip.disabled')
    ]
    full_addon_list = { methods.strip_extension(file): file for file in addon_files }

    for name, file in full_addon_list.items():
        if name not in addon_list:
            project_id = None
            file_id = None
            addon_type = None

            if file.parent == MODS_DIR:
                mod_info = None

                with zipfile.ZipFile(file) as jar:
                    if "mcmod.info" in jar.namelist():
                        raw_json = jar.read("mcmod.info").decode("utf-8", errors="replace")
                        raw_json = re.sub(r'[\r\n]+', " ", raw_json)
                        mod_info = json.loads(raw_json)[0]

                addon_type = "mod"
                project_id = mod_info["modid"]
                file_id = mod_info["version"]
            if file.parent == RESOURCES_DIR or file.parent == SHADERS_DIR:

                addon_type = "resourcepack" if file.parent == RESOURCES_DIR else "shaderpack"
                project_id = fetch_base_name(name)
                with open(file, "rb") as f:
                    file_id = hashlib.md5(f.read()).hexdigest()

            addon_info = {
                "projectID": project_id,
                "fileID": file_id,
                "type": addon_type
            }

            compare_addon(name, addon_info)

            #TODO: warn user about mods not in .gitignore if they are local only

    # Check for deleted addons
    missing_addons = {name: info for name, info in current_info.items() if name not in full_addon_list}
    for name, info in missing_addons.items():
        locality = PC_HOST if info.get("isLocal") else CF_HOST
        print(f"Deleted {locality} {info["type"]}:", f"{name}", indent=2)
        
        deleted_addon = current_info.pop(name)
        delete_addon_files(deleted_addon)

    if json_changed:
        save_addons_info(methods.natural_sort(current_info))
    
    print("Finished syncing addon info!\n")
    
    return config_outdated

def delete_addon_files(info):
    print("Deleting files for addon:", f"{info["projectID"]}", indent=4)
    
    association_patterns = info["associatedWith"]
    config_patterns = info.get("configFiles", [])

    association_files = methods.collect_file_matches(association_patterns, OVERRIDES_DIR)
    config_files = methods.collect_file_matches(config_patterns, CONFIG_DIR)

    files_to_delete = ( config_files | association_files )

    for file in files_to_delete:
        if file.exists():
            file.unlink()
            print("Deleted file:", f"{file.relative_to(OVERRIDES_DIR)}", indent=6)

    #TODO: Clean up empty directories

def check_mod_configs():
    print("Checking mod configs...")
    
    info_set = load_addons_info()
    all_config_files = [ path for path in CONFIG_DIR.rglob("*") if path.is_file() ]

    def build_file_map(pattern_bank, directory):
        file_map = dict()

        for name, info in info_set.items():
            if info["type"] != "mod":
                continue

            matched_files = set()
            patterns = info.get(pattern_bank, [])

            for pattern in patterns:
                matched = False

                if pattern.startswith(r"\!"):
                    for file in all_config_files:
                        if methods.match_file_pattern(pattern[1:], file, directory):
                            matched_files.add(file)
                            matched = True
                elif pattern.startswith("!"):
                    for file in all_config_files:
                        if methods.match_file_pattern(pattern[1:], file, directory):
                            matched_files.discard(file)
                            matched = True
                else:
                    for file in all_config_files:
                        if methods.match_file_pattern(pattern, file, directory):
                            matched_files.add(file)
                            matched = True

                if not matched:
                    print("WARNING: Bad file pattern!", f"\"{pattern}\" from {name}", indent=0)

            file_map[name] = sorted(matched_files)

        return file_map

    association_map = build_file_map("associatedWith", OVERRIDES_DIR)
    config_map = build_file_map("configFiles", CONFIG_DIR)

    tracked_files = sorted( set( file for file_list in [ *config_map.values(), *association_map.values(), IGNORED_CONFIGS ] for file in file_list ) )
    untracked_files = [ file for file in all_config_files if file not in tracked_files ]

    if len(untracked_files) > 0:
        print("WARNING: The following config files are not attributed to any mod!", indent=0)

        for file in untracked_files:
            print(f"{file.relative_to(CONFIG_DIR)}", indent=2)

        print("WARNING: Attribute these files to a mod or add them ignore list.", indent=0)

    #TODO: Give option for user to attribute files here
    
    print("Finished checking mod configs!\n")

    return len(untracked_files)

def refresh_mod_config(info):
    print("Refreshing config for mod:", f"{info["projectID"]}", indent=4)

    config_patterns = info.get("configFiles", [])
    config_files = methods.collect_file_matches(config_patterns, CONFIG_DIR)

    for file in config_files:
        if file.exists():
            file.unlink()
            print("Deleted file:", f"{file.relative_to(OVERRIDES_DIR)}", indent=6)

if __name__ == "__main__":
    #TODO: Check for any available addon updates
    
    attribute_files = check_mod_configs()

    if attribute_files and ADDONS_INFO_JSON.exists():
        _print(" ATTRIBUTE CONFIG FILES BEFORE CONTINUING ".center(MAX_OUTPUT_LENGTH, "="))
        sys.exit(1)
    
    refresh_config = sync_addons_info()

    if refresh_config:
        _print(" RESTART INSTANCE BEFORE CONTINUING ".center(MAX_OUTPUT_LENGTH, "="))
        sys.exit(1)

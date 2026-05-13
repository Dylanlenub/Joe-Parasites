from pathlib import Path
from fnmatch import fnmatch
import json
import re

def strip_extension(file):
    if isinstance(file, str):
        file = Path(file)

    name = file.name
    for ext in reversed(file.suffixes):
        if ext == ".disabled":
            name = name.removesuffix(ext)
        else:
            name = name.removesuffix(ext)
            break
    return name

def natural_sort(collection):
    def predicate(item):
        text = item[0] if isinstance(collection, dict) else item
        chunks = re.split(r'(\d+)', text)
        
        result = []
        for chunk in chunks:
            if chunk.isdigit():
                result.append(int(chunk))
            else:
                result.append(chunk.lower())
        return result

    if isinstance(collection, dict):
        return dict(sorted(collection.items(), key=predicate))
    else:
        return sorted(collection, key=predicate)

def parse_instance_addons(instanceFile):
    with open(instanceFile, encoding="utf-8") as f:
        data = json.load(f)

    addons = {}
    for addon in data["installedAddons"]:
        web_site = addon["webSiteURL"]
        main_author = addon["primaryAuthor"]
        addon_name = addon["name"]
        addon_type = addon["categorySection"]["path"].removesuffix("s")
        pack_required = addon.get("isEnabled", True)
        pack_locked = addon.get("isLocked", False)
        project_id = addon["installedFile"]["projectId"]
        file_name = addon["installedFile"]["fileNameOnDisk"]
        file_id = addon["installedFile"]["id"]

        base_name = strip_extension(file_name)
        addons[base_name] = {
            "projectID": project_id,
            "fileID": file_id,
            "required": pack_required,
            "isLocked": pack_locked,
            "webSite": web_site,
            "name": addon_name,
            "author": main_author,
            "type": addon_type
        }        
    return natural_sort(addons)

def match_file_pattern(pattern, file, root):
    relative = file.relative_to(root)
    parts = relative.parts

    if pattern.endswith("/"):
        pattern = pattern.rstrip("/")
        
        return any(fnmatch(str(Path(*parts[:i+1])), pattern) for i in range(len(parts)))

    if "/" in pattern:
        return fnmatch(str(relative), pattern)

    return any(fnmatch(part, pattern) for part in parts)

def collect_file_matches(patterns, root):
    matched = set()
    
    for pattern in patterns:
        negated = pattern.startswith("!")
        is_dir = pattern.endswith("/")
        
        pattern = pattern.replace(r"\!", "!")
        pattern = pattern[1:] if negated else pattern
        pattern = pattern.rstrip("/") if is_dir else pattern

        if is_dir:
            target_dir = root / pattern
            
            if negated:
                for path in list(matched):
                    if path.is_relative_to(target_dir):
                        matched.discard(path)
            else:
                for path in target_dir.rglob("*"):
                    if path.is_file():
                        matched.add(path)
        else:
            if negated:
                for path in list(matched):
                    if match_file_pattern(pattern, path, root):
                        matched.discard(path)
            else:
                for path in root.rglob("*"):
                    if path.is_file() and match_file_pattern(pattern, path, root):
                        matched.add(path)

    return matched

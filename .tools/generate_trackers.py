from pathlib import Path

import methods

REPO_ROOT = Path(__file__).parent.parent
OVERRIDES_DIR = REPO_ROOT / "overrides"
MODS_DIR = OVERRIDES_DIR / "mods"
SHADERS_DIR = OVERRIDES_DIR / "shaderpacks"
RESOURCES_DIR = OVERRIDES_DIR / "resourcepacks"

MODS_TRACKER = MODS_DIR / "modtracker.txt"
SHADERS_TRACKER = SHADERS_DIR / "shadertracker.txt"
RESOURCES_TRACKER = RESOURCES_DIR / "resourcetracker.txt"

def generate_tracker(path, directory, extension):
    files = [ *directory.glob(f'*{extension}'), *directory.glob(f'*{extension}.disabled') ]
    names = [ methods.strip_extension(file) for file in files ]
    
    with path.open("w", encoding="utf-8", newline="\r\n") as f:
        f.writelines(name + "\n" for name in methods.natural_sort(names))

    print(f"Generated {path.relative_to(OVERRIDES_DIR)}")

if __name__ == "__main__":
    generate_tracker(MODS_TRACKER, MODS_DIR, ".jar")
    generate_tracker(SHADERS_TRACKER, SHADERS_DIR, ".zip")
    generate_tracker(RESOURCES_TRACKER, RESOURCES_DIR, ".zip")

    # For a newline character
    print()

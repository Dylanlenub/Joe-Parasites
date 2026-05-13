from pathlib import Path
import subprocess
import shutil
import ctypes
import sys

if not ctypes.windll.shell32.IsUserAnAdmin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, sys.argv[0], None, 1)
    sys.exit()

REPO_ROOT = Path(__file__).parent.parent
CURSEFORGE_ROOT = Path.home() / "curseforge/minecraft/Instances"
INSTANCE_ROOT = None

DIRS = [ "mods", "config", "scripts", "shaderpacks", "resourcepacks" ]
MC_INSTANCE_JSON = "minecraftinstance.json"
OPTIONS_TXT = "options.txt"

GITHOOKS_DIR = REPO_ROOT / ".git/hooks"
HOOKS = [ "pre-commit" ]

print("Enter the path to instance:")
while not INSTANCE_ROOT:
    profileName = input(f"{CURSEFORGE_ROOT}\\")
    INSTANCE_ROOT = CURSEFORGE_ROOT / profileName
    if not INSTANCE_ROOT.is_dir():
        INSTANCE_ROOT = None
        print("Invalid path. Try again:")

# Create junctions to directories in curseforge instance
for pathName in DIRS:
    RepoDir = REPO_ROOT / "overrides" / pathName
    InstanceDir = INSTANCE_ROOT / pathName
    if not RepoDir.is_junction() and RepoDir.is_dir():
        shutil.rmtree(RepoDir)
    if not RepoDir.is_dir():
        print(f"Directory overrides/{pathName} was not found in repository, creating junction with instance's directory")
        subprocess.run(["mklink", "/J", RepoDir, InstanceDir], shell=True)

# Create soft link to minecraftinstance.json from curseforge instance
if not (REPO_ROOT / MC_INSTANCE_JSON).is_file():
    print(f"File {MC_INSTANCE_JSON} was not found in repository, creating soft link with instance's file")
    subprocess.run(["mklink", REPO_ROOT / MC_INSTANCE_JSON, INSTANCE_ROOT / MC_INSTANCE_JSON], shell=True)

# Move options.txt and create soft link in curseforge instance
if not (REPO_ROOT / "overrides" / OPTIONS_TXT).is_file():
    print(f"File {OPTIONS_TXT} was not found in repository, creating soft link with instance's file")
    shutil.move(INSTANCE_ROOT / OPTIONS_TXT, REPO_ROOT / "overrides")
    subprocess.run(["mklink", INSTANCE_ROOT / OPTIONS_TXT, REPO_ROOT / "overrides" / OPTIONS_TXT], shell=True)

# Install any hooks for git
for hook in HOOKS:
    hookPath = GITHOOKS_DIR / hook
    hookFile = REPO_ROOT / (".tools/" + hook + ".hook")
    if not hookPath.is_file() and hookFile.is_file():
        print(f"Installing {hook} hook in git")
        subprocess.run(["mklink", hookPath, hookFile], shell=True)

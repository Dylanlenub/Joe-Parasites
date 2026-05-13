from pathlib import Path
import json
import html

import methods

REPO_ROOT = Path(__file__).parent.parent
MC_INSTANCE_JSON = REPO_ROOT / "minecraftinstance.json"
MODLIST_HTML = REPO_ROOT / "modlist.html"

lines = []
lines.append("<ul>")

addons_data = methods.parse_instance_addons(MC_INSTANCE_JSON)
for addon_name, addon_info in addons_data.items():
    url = html.escape(addon_info["webSite"])
    name = html.escape(addon_info["name"])
    author = html.escape(addon_info["author"])

    lines.append(f'<li><a href="{url}">{name} (by {author})</a></li>')
lines.append("</ul>")

MODLIST_HTML.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8-sig"
)

print(f"Generated {MODLIST_HTML.relative_to(REPO_ROOT)}\n")

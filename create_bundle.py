import argparse
import plistlib
import re
import shutil
from pathlib import Path

PROJECT_NAME = "λKeyboard"
DIR_TEMPLATE = Path("template/Contents")
DIR_LAYOUT = Path("generated_layouts")
ICON_SRC = Path("assets/logos.icns")
BUNDLE_ID = "io.jazzz.keyboardlayout.logoskeyboard"

def output_path(version):
    return Path(f"build/{PROJECT_NAME}.bundle/Contents")

def load_layout_metadata():
    """Derive layout name → language from generated_layouts/{lang}/*.keylayout."""
    layouts = {}
    for keylayout in DIR_LAYOUT.glob("**/*.keylayout"):
        lang = keylayout.parent.name  # e.g. "fr", "en"
        name = keylayout.stem         # e.g. "λ - Canadian – CSA"
        layouts[name] = lang
    return layouts


def update_info_plist(layouts, version):
    plist_path = output_path(version) / "Info.plist"
    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)

    plist["CFBundleVersion"] = version

    # Remove old KLInfo entries
    for key in [k for k in plist if k.startswith("KLInfo_")]:
        del plist[key]

    # Add an entry for each generated layout
    for name, lang in layouts.items():
        slug = re.sub(r"[^a-z0-9]+", "", name.lower()).strip("-")
        plist[f"KLInfo_{name}"] = {
            "TICapsLockLanguageSwitchCapable": False,
            "TISIconIsTemplate": False,
            "TISInputSourceID": f"{BUNDLE_ID}.{slug}",
            "TISIntendedLanguage": lang,
        }

    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)


def build(version):

    DIR_OUTPUT = output_path(version)
    # Clean and copy template structure
    if DIR_OUTPUT.exists():
        shutil.rmtree(DIR_OUTPUT)
    shutil.copytree(DIR_TEMPLATE, DIR_OUTPUT)

    resources = DIR_OUTPUT / "Resources"

    if not resources.exists():
        resources.mkdir(parents=True, exist_ok=True)

    # Copy each generated keylayout + icon into the bundle
    for keylayout in DIR_LAYOUT.glob("**/*.keylayout"):
        name = keylayout.stem
        shutil.copy2(keylayout, resources / keylayout.name)
        shutil.copy2(ICON_SRC, resources / f"{name}.icns")

    # Update Info.plist with KLInfo entries and version
    layouts = load_layout_metadata()
    update_info_plist(layouts, version)

    print(f"Bundle v{version} built at {DIR_OUTPUT.parent}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="Bundle version tag (e.g. 1.0)")
    args = parser.parse_args()
    build(args.version)

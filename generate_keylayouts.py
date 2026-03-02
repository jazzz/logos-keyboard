from pathlib import Path
import re
import tomllib
import xml.etree.ElementTree as ET



DIR_BASE_LAYOUT = Path("base_layouts")
DIR_OUTPUT = Path("generated_layouts")

def load_substitution_map(path="bindings.toml"):
    with open(path, "rb") as f:
        data = tomllib.load(f)

    default_code = data.get("default", [{}])[0].get("code")
    sub_map = {}
    for layout_name, entries in data.items():
        if layout_name == "default":
            continue
        code = entries[0].get("code", default_code)
        if code is not None:
            sub_map[layout_name] = code

    return sub_map, default_code

def substitute_key_bind(keylayout, code, binding):
    key_map = get_option_mapping(keylayout)
    key = key_map.find(f'key[@code="{code}"]')
    key.set('output', binding)

## Navigate to the keyMap with the index that corresponds to <modifier keys="anyOption"/>
def get_option_mapping(root):
    modifier_map = root.find('.//modifierMap')
    for key_map_select in modifier_map.findall('keyMapSelect'):
        for modifier in key_map_select.findall('modifier'):
            if modifier.get('keys') == 'anyOption':
                index = key_map_select.get('mapIndex')
                return root.find(f'.//keyMapSet/keyMap[@index="{index}"]')
    return None



def base_keylayouts():
    return list(DIR_BASE_LAYOUT.glob("**/*.keylayout"))


def scrub_illegal_chars(content):
    """Replace all numeric character references with placeholders that survive ET parsing."""
    def placeholder(m):
        val = m.group(1)
        code = int(val[1:], 16) if val[0] in 'xX' else int(val)
        return f'__UNICODECHAR_{code:04X}__'
    content = re.sub(r'&#(x[0-9A-Fa-f]+|[0-9]+);', placeholder, content)
    return content

## Returns Parsed Keylayout.
def load(path):

    with open(path, 'r') as f:
        content = f.read()

    content = scrub_illegal_chars(content)
    return ET.fromstring(content), path.name.rsplit('.',1)[0]


def restore_control_char_refs(xml_str):
    """Restore placeholders and re-encode literal control characters as &#xNNNN; references."""
    xml_str = re.sub(r'__UNICODECHAR_([0-9A-F]{4})__', lambda m: f'&#x{m.group(1)};', xml_str)
    def encode_literal(m):
        return f'&#x{ord(m.group()):04X};'
    xml_str = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', encode_literal, xml_str)
    return xml_str


def write_file(path, root):
    ET.indent(root, space='    ')
    xml_str = ET.tostring(root, encoding='unicode')
    xml_str = restore_control_char_refs(xml_str)
    xml_str = re.sub(r' />', '/>', xml_str)
    preamble = '<?xml version="1.1" encoding="UTF-8"?>\n<!DOCTYPE keyboard SYSTEM "file://localhost/System/Library/DTDs/KeyboardLayout.dtd">\n'
    with open(path, 'w', encoding='UTF-8') as f:
        f.write(preamble + xml_str)

if __name__ == "__main__":

    (code_map, default_code) = load_substitution_map()

    for file in base_keylayouts():
        k, name = load(file)
        lang = file.parent.name  # e.g. "en", "fr"
        print(name)

        k.set('name', f'λ - {name}')
        bind = code_map.get(name) if name in code_map else default_code
        substitute_key_bind(k,bind,'λ')

        out_dir = DIR_OUTPUT / lang
        out_dir.mkdir(parents=True, exist_ok=True)
        write_file(out_dir / f"λ - {name}.keylayout", k)
        

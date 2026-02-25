"""JMX XML patching for Backend Listener and other elements.

Patches a JMX file in-place (writing to output_path) before launching JMeter.
The original JMX is never modified — a patched copy is written to the result dir.
"""
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


def patch_jmx(jmx_path: Path, patches: dict, output_path: Path) -> Path:
    """Patch JMX XML elements and write to output_path.

    Currently supports:
    - BackendListener: patches string properties matching patch keys
      (e.g. influxdbUrl, application, measurement, testTitle, runId)

    Args:
        jmx_path: Path to the original JMX file.
        patches: Dict of {property_name: new_value} to apply.
        output_path: Where to write the patched JMX.

    Returns:
        output_path on success.
    """
    if not patches:
        return output_path

    tree = ET.parse(str(jmx_path))
    root = tree.getroot()
    patched = False

    # Patch BackendListener elements
    for listener in root.iter("BackendListener"):
        patched |= _patch_element_props(listener, patches)

    # Patch elementProp children (some BackendListener configs nest under elementProp)
    for elem_prop in root.iter("elementProp"):
        patched |= _patch_element_props(elem_prop, patches)

    if patched:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="unicode", xml_declaration=True)

    return output_path


def _patch_element_props(element: ET.Element, patches: dict) -> bool:
    """Patch stringProp children of an element where name matches a patch key."""
    changed = False
    for prop in element.findall(".//stringProp"):
        name = prop.get("name", "")
        # Match both bare name and qualified name (e.g. "influxdbUrl" or "backend_influxdb.influxdbUrl")
        for patch_key, patch_value in patches.items():
            if name == patch_key or name.endswith("." + patch_key):
                prop.text = str(patch_value)
                changed = True
    return changed


def extract_backend_listener_props(jmx_path: Path) -> list[dict]:
    """Extract all Backend Listener properties from a JMX file.

    Returns a list of dicts, one per BackendListener found, each containing
    the string properties as key-value pairs.
    """
    if not jmx_path.exists():
        return []

    try:
        tree = ET.parse(str(jmx_path))
    except ET.ParseError:
        return []

    results = []
    for listener in tree.getroot().iter("BackendListener"):
        props = {}
        for string_prop in listener.iter("stringProp"):
            name = string_prop.get("name", "")
            value = string_prop.text or ""
            if name:
                props[name] = value
        if props:
            results.append(props)
    return results


def extract_csv_data_set_configs(jmx_path: Path) -> list[dict]:
    """Extract CSV Data Set Config elements from a JMX file.

    Returns a list of dicts with filename, variableNames, delimiter, etc.
    """
    if not jmx_path.exists():
        return []

    try:
        tree = ET.parse(str(jmx_path))
    except ET.ParseError:
        return []

    results = []
    for config in tree.getroot().iter("CSVDataSet"):
        props = {}
        for string_prop in config.iter("stringProp"):
            name = string_prop.get("name", "")
            value = string_prop.text or ""
            if name:
                # Simplify qualified names: "CSVDataSet.filename" -> "filename"
                short_name = name.split(".")[-1] if "." in name else name
                props[short_name] = value
        if props:
            results.append(props)
    return results

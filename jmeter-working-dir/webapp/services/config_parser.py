import json
import shutil
from pathlib import Path


def load_project_config(config_path: Path) -> dict:
    """Load project.json and return as dict."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_project_config(config_path: Path, data: dict) -> None:
    """Save dict to project.json."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def auto_detect_project(config_path: Path) -> dict:
    """Scan parent directory for known project folders and generate project.json."""
    app_dir = config_path.parent
    project_root = app_dir.parent

    config = {
        "name": project_root.name,
        "project_root": "..",
        "jmeter_path": "",
        "paths": {
            "jmx_dir": "",
            "config_dir": "",
            "config_properties": "",
            "results_dir": "",
            "test_data_dir": "",
            "scripts_dirs": [],
            "slaves_file": "",
        },
    }

    # Auto-detect known directories
    known_jmx_dirs = ["test_plan", "script/jmeter", "scripts/jmeter"]
    for d in known_jmx_dirs:
        if (project_root / d).is_dir():
            config["paths"]["jmx_dir"] = d
            break

    if (project_root / "config").is_dir():
        config["paths"]["config_dir"] = "config"

    if (project_root / "config.properties").is_file():
        config["paths"]["config_properties"] = "config.properties"

    # Read results_dir from config.properties if available (single source of truth)
    props_path = project_root / "config.properties"
    if props_path.exists():
        props = read_config_properties(props_path)
        if props.get("results_dir"):
            config["paths"]["results_dir"] = props["results_dir"]
    if not config["paths"]["results_dir"]:
        known_results_dirs = ["results", "result"]
        for d in known_results_dirs:
            if (project_root / d).is_dir():
                config["paths"]["results_dir"] = d
                break

    known_data_dirs = ["test_data", "data", "testdata"]
    for d in known_data_dirs:
        if (project_root / d).is_dir():
            config["paths"]["test_data_dir"] = d
            break

    scripts_dirs = []
    for d in ["bin", "utils", "scripts"]:
        if (project_root / d).is_dir():
            scripts_dirs.append(d)
    config["paths"]["scripts_dirs"] = scripts_dirs

    if (project_root / "slaves.txt").is_file():
        config["paths"]["slaves_file"] = "slaves.txt"

    # Detect JMeter
    config["jmeter_path"] = detect_jmeter_path()

    save_project_config(config_path, config)
    return config


def detect_jmeter_path() -> str:
    """Try to find JMeter in PATH or common install locations."""
    # Check PATH first
    jmeter = shutil.which("jmeter")
    if jmeter:
        return str(Path(jmeter).resolve())

    jmeter_bat = shutil.which("jmeter.bat")
    if jmeter_bat:
        return str(Path(jmeter_bat).resolve())

    # Common Windows install locations
    common_paths = [
        Path("C:/apache-jmeter-5.6.3/bin/jmeter.bat"),
        Path("C:/apache-jmeter-5.6.2/bin/jmeter.bat"),
        Path("C:/apache-jmeter-5.6.1/bin/jmeter.bat"),
        Path("C:/apache-jmeter-5.6/bin/jmeter.bat"),
        Path("C:/apache-jmeter-5.5/bin/jmeter.bat"),
        Path("C:/Program Files/apache-jmeter/bin/jmeter.bat"),
    ]
    for p in common_paths:
        if p.exists():
            return str(p)

    # Common Linux/Mac locations
    linux_paths = [
        Path("/opt/apache-jmeter/bin/jmeter"),
        Path("/usr/local/bin/jmeter"),
        Path.home() / "apache-jmeter" / "bin" / "jmeter",
    ]
    for p in linux_paths:
        if p.exists():
            return str(p)

    return ""


def resolve_path(project_config: dict, key: str) -> Path:
    """Resolve a relative path from project.json to absolute path."""
    app_dir = Path(__file__).resolve().parent.parent
    project_root = (app_dir / project_config["project_root"]).resolve()
    rel_path = project_config["paths"].get(key, "")
    if not rel_path:
        return project_root
    return (project_root / rel_path).resolve()


def get_project_root(project_config: dict) -> Path:
    """Get the absolute project root path."""
    app_dir = Path(__file__).resolve().parent.parent
    return (app_dir / project_config["project_root"]).resolve()


# --- Config file parsers ---

def read_config_properties(path: Path) -> dict:
    """Parse Java .properties file to ordered dict."""
    props = {}
    if not path.exists():
        return props
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()
    return props


def write_config_properties(path: Path, data: dict, comments: list[str] | None = None) -> None:
    """Write dict back to .properties file."""
    with open(path, "w", encoding="utf-8") as f:
        if comments:
            for c in comments:
                f.write(f"# {c}\n")
            f.write("\n")
        for key, value in data.items():
            f.write(f"{key}={value}\n")


def read_json_config(path: Path) -> dict:
    """Read a JSON config file."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_config(path: Path, data: dict) -> None:
    """Write dict to JSON config file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_slaves_file(path: Path) -> list[str]:
    """Parse slaves file to list of IPs (ignoring comments and blanks).
    Delegates to read_slaves() for backward compatibility."""
    return [s["ip"] for s in read_slaves(path)]


def write_slaves_file(path: Path, ips: list[str]) -> None:
    """Write list of IPs as JSON slave objects (all enabled)."""
    slaves = [{"ip": ip, "enabled": True} for ip in ips]
    write_slaves(path, slaves)


def read_slaves(path: Path) -> list[dict]:
    """Read slaves file. Supports both JSON format and plain text (auto-migrates).
    Returns list of {"ip": "x.x.x.x", "enabled": True/False}."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    # Try JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return [{"ip": s.get("ip", s) if isinstance(s, dict) else s,
                      "enabled": s.get("enabled", True) if isinstance(s, dict) else True}
                    for s in data if (s.get("ip") if isinstance(s, dict) else s)]
    except (json.JSONDecodeError, ValueError):
        pass
    # Fall back to plain text (one IP per line)
    slaves = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            slaves.append({"ip": line, "enabled": True})
    # Auto-migrate to JSON
    if slaves:
        write_slaves(path, slaves)
    return slaves


def get_active_slaves(path: Path) -> list[str]:
    """Return list of enabled slave IPs only."""
    return [s["ip"] for s in read_slaves(path) if s.get("enabled", True)]


def write_slaves(path: Path, slaves: list[dict]) -> None:
    """Write slave objects to file as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(slaves, f, indent=2, ensure_ascii=False)


def parse_jmeter_properties_catalog(path: Path) -> list[dict]:
    """Parse jmeter.properties file to extract a catalog of all properties.

    Returns list of {"key": str, "default": str, "description": str, "category": str}.
    Reads both commented-out (#key=value) and active (key=value) properties.
    Categories are detected from section header comments like '#---...'.
    """
    if not path.exists():
        return []

    catalog = []
    current_category = "General"
    description_lines = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            # Detect section headers: lines like "#----" preceded by "# Section Name"
            if stripped.startswith("#") and stripped.replace("#", "").replace("-", "").strip() == "":
                # This is a separator line like "#-----------"
                # Check if the previous description line is a category name
                if description_lines:
                    candidate = description_lines[-1].strip()
                    # Category names are short, title-like, no '=' or '/' or digits at start
                    # Skip file header noise like "THIS FILE SHOULD NOT BE MODIFIED"
                    if (candidate and "=" not in candidate and len(candidate) < 80
                            and not candidate[0].isdigit()
                            and "/" not in candidate
                            and "SHOULD NOT" not in candidate
                            and "should not" not in candidate):
                        current_category = candidate
                        description_lines = []
                continue

            # Collect comment lines as potential descriptions
            if stripped.startswith("#"):
                content = stripped.lstrip("#").strip()
                # Skip license headers, empty comments, and URLs
                if content and not content.startswith("Licensed to") and not content.startswith("http://") and not content.startswith("https://"):
                    # Check if this is a commented-out property: #key=value
                    if "=" in content and not content.startswith(" "):
                        key, _, value = content.partition("=")
                        key = key.strip()
                        value = value.strip()
                        # Valid JMeter property keys: no spaces, look like identifiers
                        # Must contain dots or underscores (e.g. server.rmi.ssl.disable)
                        # Skip: examples (prefix=Namespace), short words (ns=...), URLs
                        is_property_key = (
                            key
                            and " " not in key
                            and not key.startswith("Example")
                            and not key.startswith("//")
                            and not key.startswith("See ")
                            and ("." in key or "_" in key)
                        )
                        if is_property_key:
                            desc = " ".join(description_lines[-3:]) if description_lines else ""
                            catalog.append({
                                "key": key,
                                "default": value,
                                "description": desc,
                                "category": current_category,
                            })
                            description_lines = []
                            continue
                    description_lines.append(content)
                continue

            # Active (uncommented) property: key=value
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip()
                if key:
                    desc = " ".join(description_lines[-3:]) if description_lines else ""
                    catalog.append({
                        "key": key,
                        "default": value,
                        "description": desc,
                        "category": current_category,
                    })
                    description_lines = []
                continue

            # Blank line — reset description buffer
            if not stripped:
                description_lines = []
                continue

    return catalog

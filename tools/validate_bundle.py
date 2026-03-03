import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("Error: jsonschema package required. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
BUNDLES_DIR = PROJECT_ROOT / "bundles"


def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_bundle(bundle_path: Path) -> tuple[list[str], list[str]]:

    errors: list[str] = []
    warnings: list[str] = []

    manifest_path = bundle_path / "bundle_manifest.json"
    if not manifest_path.exists():
        return (["bundle_manifest.json not found"], [])

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return ([f"bundle_manifest.json is invalid JSON: {e}"], [])

    try:
        manifest_schema = load_schema("bundle_manifest")
        jsonschema.validate(manifest, manifest_schema)
    except jsonschema.ValidationError as e:
        errors.append(f"bundle_manifest.json schema violation: {e.message}")
    except FileNotFoundError as e:
        errors.append(str(e))

    files = manifest.get("files", {})
    for role, filename in files.items():
        filepath = bundle_path / filename
        if not filepath.exists():
            errors.append(f"Missing file '{role}': {filename}")

    tickets_file = files.get("tickets")
    if tickets_file and (bundle_path / tickets_file).exists():
        tickets_path = bundle_path / tickets_file
        try:
            with open(tickets_path, encoding="utf-8") as f:
                tickets_data = json.load(f)
            tickets_schema = load_schema("tickets")
            jsonschema.validate(tickets_data, tickets_schema)
        except json.JSONDecodeError as e:
            errors.append(f"tickets file invalid JSON: {e}")
        except jsonschema.ValidationError as e:
            errors.append(f"tickets schema violation: {e.message}")

    metrics_file = files.get("metrics_snapshot")
    if metrics_file and (bundle_path / metrics_file).exists():
        metrics_path = bundle_path / metrics_file
        try:
            with open(metrics_path, encoding="utf-8") as f:
                metrics_data = json.load(f)
            metrics_schema = load_schema("metrics_snapshot")
            jsonschema.validate(metrics_data, metrics_schema)
        except json.JSONDecodeError as e:
            errors.append(f"metrics_snapshot invalid JSON: {e}")
        except jsonschema.ValidationError as e:
            errors.append(f"metrics_snapshot schema violation: {e.message}")

    docs_dir = manifest.get("docs_dir")
    if docs_dir:
        docs_path = bundle_path / docs_dir
        if not docs_path.is_dir():
            warnings.append(f"docs_dir '{docs_dir}' not found or not a directory")

    return (errors, warnings)


def main() -> int:
    if len(sys.argv) < 2:
        bundle_id = "sample_01"
        print(f"Usage: python validate_bundle.py <bundle_id>")
        print(f"Using default: {bundle_id}\n")
    else:
        bundle_id = sys.argv[1]

    bundle_path = BUNDLES_DIR / bundle_id
    if not bundle_path.is_dir():
        print(f"Error: Bundle not found: {bundle_path}")
        return 1

    errors, warnings = validate_bundle(bundle_path)

    for w in warnings:
        print(f"Warning: {w}")
    for e in errors:
        print(f"Error: {e}")

    if errors:
        print("\nValidation FAILED")
        return 1

    if warnings:
        print("\nValidation OK (with warnings)")
    else:
        print("\nValidation OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
SiteWise Terraform Generator

Generates AWSCC Terraform configurations from Ignition JSON definitions.
Handles both UDT (model) and UNS (asset) JSON formats.

Usage:
    python generate_sitewise_tf.py --input <json_file> --output <tf_file> --site <site_name>
"""

import argparse
import json
import sys
import os
from pathlib import Path


# --- Data Type Mapping ---
IGNITION_TO_SITEWISE_TYPE = {
    "Int1": "INTEGER",
    "Int2": "INTEGER",
    "Int4": "INTEGER",
    "Int8": "INTEGER",
    "Float4": "DOUBLE",
    "Float8": "DOUBLE",
    "Boolean": "BOOLEAN",
    "String": "STRING",
    "DateTime": "STRING",
}


class GeneratorError(Exception):
    """Custom exception for generator errors with meaningful messages."""
    pass


def validate_json_file(filepath: str) -> dict:
    """Validate and parse a JSON file with clear error messages."""
    if not os.path.exists(filepath):
        raise GeneratorError(f"Input file not found: {filepath}")

    if not filepath.endswith(".json"):
        raise GeneratorError(f"Input file must be .json: {filepath}")

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise GeneratorError(
            f"Invalid JSON in {filepath}: {e.msg} at line {e.lineno}, column {e.colno}"
        )

    if not isinstance(data, dict):
        raise GeneratorError(f"JSON root must be an object, got {type(data).__name__}")

    return data


def validate_model_json(data: dict) -> None:
    """Validate UDT/model JSON structure."""
    if "name" not in data:
        raise GeneratorError("Model JSON missing required field: 'name'")
    if "tagType" not in data:
        raise GeneratorError("Model JSON missing required field: 'tagType'")
    if "tags" not in data:
        raise GeneratorError("Model JSON missing required field: 'tags'")
    if not isinstance(data["tags"], list):
        raise GeneratorError("'tags' must be a list")


def validate_asset_json(data: dict) -> None:
    """Validate UNS/asset JSON structure."""
    if "name" not in data:
        raise GeneratorError("Asset JSON missing required field: 'name'")
    if "tagType" not in data:
        raise GeneratorError("Asset JSON missing required field: 'tagType'")


def sanitize_tf_name(name: str) -> str:
    """Convert a name to a valid Terraform resource identifier."""
    sanitized = name.replace(" ", "_").replace("-", "_").replace("/", "_")
    sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    return sanitized.lower()


def strip_version_suffix(filename: str) -> str:
    """Strip version suffix from a filename to get the base model name.

    Handles patterns like:
      fridge_version_xyz.json  → fridge
      fridge_version_2.json    → fridge
      fridge_v1_0.json         → fridge
      MixingUDT_V1_0.json      → MixingUDT
      plain_name.json          → plain_name (no version detected, return as-is)

    The convention is: {base_name}_version_{x} or {base_name}_v{x}_{y}
    """
    import re

    # Remove .json extension
    name = filename.rsplit(".json", 1)[0] if filename.endswith(".json") else filename

    # Try patterns from most specific to least:
    # pattern: name_version_xyz or name_Version_xyz
    match = re.match(r'^(.+?)_[Vv]ersion_\w+$', name)
    if match:
        return match.group(1)

    # pattern: name_V1_0 or name_v1_0 (version with major_minor)
    match = re.match(r'^(.+?)_[Vv]\d+_\d+$', name)
    if match:
        return match.group(1)

    # pattern: name_v1 or name_V1 (simple version number)
    match = re.match(r'^(.+?)_[Vv]\d+$', name)
    if match:
        return match.group(1)

    # No version suffix detected — return the full name
    return name


def derive_output_filename(input_path: str, gen_type: str) -> str:
    """Derive the output TF filename from the input JSON filename.

    For models: strips version suffix so versioned inputs always overwrite
    the same TF file (Terraform sees it as an update, not a new resource).

    For assets: uses the input filename directly (no versioning concern).
    """
    basename = os.path.basename(input_path)

    if gen_type == "models":
        base_name = strip_version_suffix(basename)
        return f"{base_name}.tf"
    else:
        name_without_ext = basename.rsplit(".json", 1)[0] if basename.endswith(".json") else basename
        return f"{name_without_ext}.tf"


def build_property_alias(path: str) -> str:
    """Build a property alias from the tag hierarchy path.

    Format: /{tag_hierarchy}/{tag_name}
    Example: /EdgeData/ProductionData/GoodPartsCounter
    """
    if path.startswith("/"):
        return path
    return f"/{path}"


def extract_properties(tags: list, path: str = "") -> list:
    """Recursively extract properties from UDT tag hierarchy."""
    properties = []

    for tag in tags:
        tag_type = tag.get("tagType", "")
        tag_name = tag.get("name", "")
        current_path = f"{path}/{tag_name}" if path else tag_name

        if tag_type == "AtomicTag":
            data_type = tag.get("dataType", "String")
            sitewise_type = IGNITION_TO_SITEWISE_TYPE.get(data_type, "STRING")
            properties.append({
                "name": current_path,
                "data_type": sitewise_type,
                "alias": build_property_alias(current_path),
            })
        elif tag_type == "Folder" and "tags" in tag:
            properties.extend(extract_properties(tag["tags"], current_path))

    return properties


def find_udt_types(data: dict, path: str = "") -> list:
    """Find all UdtType definitions in the JSON hierarchy."""
    udt_types = []

    if data.get("tagType") == "UdtType":
        udt_types.append({"name": data["name"], "path": path, "data": data})
        return udt_types

    for tag in data.get("tags", []):
        tag_name = tag.get("name", "")
        current_path = f"{path}/{tag_name}" if path else tag_name
        udt_types.extend(find_udt_types(tag, current_path))

    return udt_types


def generate_model_tf(data: dict) -> str:
    """Generate Terraform for SiteWise asset models from UDT JSON."""
    validate_model_json(data)

    udt_types = find_udt_types(data)
    if not udt_types:
        raise GeneratorError("No UdtType definitions found in JSON")

    tf_blocks = []
    tf_blocks.append('# Auto-generated by generate_sitewise_tf.py')
    tf_blocks.append('# Do not edit manually — changes will be overwritten')
    tf_blocks.append('')

    for udt in udt_types:
        properties = extract_properties(udt["data"].get("tags", []))
        if not properties:
            print(f"  Warning: UDT '{udt['name']}' has no properties, skipping")
            continue

        # Sort properties alphabetically to prevent Terraform drift
        properties.sort(key=lambda p: p["name"])

        resource_name = sanitize_tf_name(udt["name"])
        tf_blocks.append(f'resource "awscc_iotsitewise_asset_model" "{resource_name}" {{')
        tf_blocks.append(f'  asset_model_name = "{udt["name"]}"')
        tf_blocks.append('')
        tf_blocks.append('  asset_model_properties = [')

        for prop in properties:
            tf_blocks.append('    {')
            tf_blocks.append(f'      name      = "{prop["name"]}"')
            tf_blocks.append(f'      data_type = "{prop["data_type"]}"')
            tf_blocks.append('      type = {')
            tf_blocks.append('        measurement = {}')
            tf_blocks.append('      }')
            tf_blocks.append('    },')

        tf_blocks.append('  ]')
        tf_blocks.append('}')
        tf_blocks.append('')

    return "\n".join(tf_blocks)


def generate_asset_tf(data: dict, site: str) -> str:
    """Generate Terraform for SiteWise assets from UNS JSON."""
    validate_asset_json(data)

    tf_blocks = []
    tf_blocks.append('# Auto-generated by generate_sitewise_tf.py')
    tf_blocks.append('# Do not edit manually — changes will be overwritten')
    tf_blocks.append(f'# Site: {site}')
    tf_blocks.append('')

    instances = find_asset_instances(data)
    if not instances:
        raise GeneratorError(f"No UdtInstance definitions found in JSON for site '{site}'")

    for instance in instances:
        resource_name = sanitize_tf_name(f"{site}_{instance['name']}")
        tf_blocks.append(f'resource "awscc_iotsitewise_asset" "{resource_name}" {{')
        tf_blocks.append(f'  asset_name     = "{site}/{instance["name"]}"')
        tf_blocks.append(f'  asset_model_id = "" # TODO: reference deployed model ID')

        # Generate asset_properties with aliases from instance tags
        instance_properties = extract_properties(instance.get("data", {}).get("tags", []))
        if instance_properties:
            # Sort alphabetically to prevent Terraform drift
            instance_properties.sort(key=lambda p: p["name"])
            tf_blocks.append('')
            tf_blocks.append('  asset_properties = [')
            for prop in instance_properties:
                tf_blocks.append('    {')
                tf_blocks.append(f'      alias      = "{prop["alias"]}"')
                tf_blocks.append(f'      logical_id = "{sanitize_tf_name(prop["name"])}_property"')
                tf_blocks.append('    },')
            tf_blocks.append('  ]')

        tf_blocks.append('}')
        tf_blocks.append('')

    return "\n".join(tf_blocks)


def find_asset_instances(data: dict, path: str = "") -> list:
    """Find all UdtInstance definitions in the JSON hierarchy."""
    instances = []

    if data.get("tagType") == "UdtInstance":
        instances.append({
            "name": data["name"],
            "path": path,
            "type_id": data.get("typeId", ""),
            "data": data,
        })
        return instances

    for tag in data.get("tags", []):
        tag_name = tag.get("name", "")
        current_path = f"{path}/{tag_name}" if path else tag_name
        instances.extend(find_asset_instances(tag, current_path))

    return instances


def main():
    parser = argparse.ArgumentParser(description="Generate SiteWise Terraform from Ignition JSON")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output .tf file or output directory")
    parser.add_argument("--site", required=True, help="Site name (or 'global' for models)")
    parser.add_argument("--type", choices=["models", "assets"], help="Override type detection")
    args = parser.parse_args()

    try:
        # Validate input
        print(f"Validating input: {args.input}")
        data = validate_json_file(args.input)

        # Determine type
        gen_type = args.type
        if not gen_type:
            if args.site == "global" or "UdtType" in json.dumps(data):
                gen_type = "models"
            else:
                gen_type = "assets"

        print(f"Generating {gen_type} Terraform for site: {args.site}")

        # Determine output path
        output_path = args.output
        if os.path.isdir(output_path) or not output_path.endswith(".tf"):
            # Output is a directory — derive filename from input
            output_dir = output_path
            output_filename = derive_output_filename(args.input, gen_type)
            output_path = os.path.join(output_dir, output_filename)
            print(f"  Output filename derived: {output_filename}")
        else:
            output_dir = os.path.dirname(output_path)

        # For models, log version stripping if applicable
        if gen_type == "models":
            input_basename = os.path.basename(args.input)
            stripped = strip_version_suffix(input_basename)
            if stripped != input_basename.rsplit(".json", 1)[0]:
                print(f"  Version detected: {input_basename} → base name: {stripped}")

        # Generate
        if gen_type == "models":
            validate_model_json(data)
            tf_content = generate_model_tf(data)
        else:
            validate_asset_json(data)
            tf_content = generate_asset_tf(data, args.site)

        # Write output
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(tf_content)

        print(f"Generated: {output_path}")
        print(f"  Type: {gen_type}")
        print(f"  Site: {args.site}")

    except GeneratorError as e:
        print(f"::error::Generator failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"::error::Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

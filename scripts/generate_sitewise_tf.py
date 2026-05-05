#!/usr/bin/env python3
"""
Simplified SiteWise Terraform generator for demo purposes.

Reads an Ignition JSON file and generates a dummy AWSCC Terraform
configuration to demonstrate the automation pipeline.

Production version will generate real awscc_iotsitewise_asset_model
resources with full property mapping and alphabetical sorting.

Usage:
    python generate_sitewise_tf.py --input file.json --output models.tf --site waterford
"""

import argparse
import json
import re
import sys
from pathlib import Path


def sanitize_tf(name):
    """Convert a name to a valid Terraform resource name."""
    s = re.sub(r"[^A-Za-z0-9]", "_", name)
    return re.sub(r"_+", "_", s).strip("_").lower()


def extract_models(data):
    """Extract UDT type names from Ignition JSON."""
    models = []

    def walk(node):
        if node.get("tagType") == "UdtType":
            models.append(node.get("name", "unknown"))
        for child in node.get("tags", []):
            walk(child)

    walk(data)
    return models


def extract_assets(data):
    """Extract UDT instance names from Ignition JSON."""
    assets = []

    def walk(node):
        if node.get("tagType") == "UdtInstance":
            assets.append({
                "name": node.get("name", "unknown"),
                "typeId": node.get("typeId", ""),
            })
        for child in node.get("tags", []):
            walk(child)

    walk(data)
    return assets


def generate_model_tf(models, site):
    """Generate Terraform for asset models."""
    lines = [
        f"# Auto-generated SiteWise models for {site}",
        f"# Generated from Ignition UDT JSON — do not edit manually",
        f"# Models: {len(models)}",
        "",
    ]

    for model_name in sorted(models):
        tf_name = sanitize_tf(model_name)
        lines.extend([
            f'resource "awscc_iotsitewise_asset_model" "{tf_name}" {{',
            f'  asset_model_name        = "{model_name}"',
            f'  asset_model_description = "From Ignition UDT: {model_name}"',
            "",
            "  # Properties would be generated from UDT definition",
            "  # Sorted alphabetically to prevent Terraform drift",
            "",
            "  asset_model_properties = [",
            "    # Production: full property list from Ignition UDT export",
            "  ]",
            "}",
            "",
        ])

    return "\n".join(lines)


def generate_asset_tf(assets, site):
    """Generate Terraform for assets."""
    lines = [
        f"# Auto-generated SiteWise assets for {site}",
        f"# Generated from site hierarchy JSON — do not edit manually",
        f"# Assets: {len(assets)}",
        "",
    ]

    for asset in assets:
        tf_name = sanitize_tf(asset["name"])
        model_ref = sanitize_tf(asset["typeId"].rsplit("/", 1)[-1]) if asset["typeId"] else "unknown"
        lines.extend([
            f'resource "awscc_iotsitewise_asset" "{tf_name}" {{',
            f'  asset_name     = "{asset["name"]}"',
            f'  asset_model_id = awscc_iotsitewise_asset_model.{model_ref}.asset_model_id',
            "}",
            "",
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate SiteWise Terraform from Ignition JSON")
    parser.add_argument("--input", required=True, help="Path to Ignition JSON file")
    parser.add_argument("--output", required=True, help="Output .tf file path")
    parser.add_argument("--site", required=True, help="Site name")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())

    # Detect type based on content
    models = extract_models(data)
    assets = extract_assets(data)

    if models:
        tf_content = generate_model_tf(models, args.site)
        print(f"Generated {len(models)} model resources", file=sys.stderr)
    elif assets:
        tf_content = generate_asset_tf(assets, args.site)
        print(f"Generated {len(assets)} asset resources", file=sys.stderr)
    else:
        print("No models or assets found in JSON", file=sys.stderr)
        tf_content = f"# No SiteWise resources found in input for {args.site}\n"

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(tf_content)
    print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()

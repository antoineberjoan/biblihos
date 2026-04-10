"""
Biblihos — Validation des fichiers YAML contre les schémas JSON Schema.

Usage :
    python scripts/validate.py schemas/scpi.yaml data/scpi/
    python scripts/validate.py schemas/retraite.yaml data/retraite/
    python scripts/validate.py schemas/scpi.yaml data/scpi/corum/origin.yaml
"""

import sys
import pathlib
import yaml
import jsonschema


def load_yaml(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def collect_targets(target_path: pathlib.Path) -> list[pathlib.Path]:
    """Retourne la liste des fichiers YAML à valider."""
    if target_path.is_file():
        return [target_path]
    return sorted(target_path.rglob("*.yaml"))


def validate(schema_path: pathlib.Path, target: pathlib.Path) -> list[str]:
    """Valide un fichier YAML contre un schéma. Retourne la liste des erreurs."""
    schema = load_yaml(schema_path)
    data = load_yaml(target)

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))

    return [
        f"{'.'.join(str(part) for part in error.path) or '(racine)'}: {error.message}"
        for error in errors
    ]


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python scripts/validate.py <schema.yaml> <data-path>")
        sys.exit(1)

    schema_path = pathlib.Path(sys.argv[1])
    target_path = pathlib.Path(sys.argv[2])

    if not schema_path.exists():
        print(f"Erreur : schéma introuvable — {schema_path}")
        sys.exit(1)

    if not target_path.exists():
        print(f"Erreur : cible introuvable — {target_path}")
        sys.exit(1)

    targets = collect_targets(target_path)

    # Ignorer les README.md et les schémas eux-mêmes
    targets = [
        target for target in targets
        if target.suffix == ".yaml" and "schemas" not in target.parts
    ]

    if not targets:
        print("Aucun fichier YAML à valider.")
        sys.exit(0)

    total = len(targets)
    failures = 0

    for target in targets:
        errors = validate(schema_path, target)
        if errors:
            failures += 1
            print(f"\n❌ {target}")
            for error in errors:
                print(f"   • {error}")
        else:
            print(f"✓ {target}")

    print(f"\n{'─' * 60}")
    print(f"{total - failures}/{total} fichiers valides", end="")
    if failures:
        print(f" — {failures} erreur(s)")
        sys.exit(1)
    else:
        print()


if __name__ == "__main__":
    main()

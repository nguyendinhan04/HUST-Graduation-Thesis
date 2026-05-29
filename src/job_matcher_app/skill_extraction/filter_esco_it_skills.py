from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_ESCO_DIR = Path(
    r"C:\Users\AN\Downloads\ESCO dataset - v1.2.1 - classification - en - csv"
)
DEFAULT_READY_DATA_DIR = Path("data/ready_data")
OUTPUT_DATE = "20260528"

INCLUDE_BROADER_PATTERNS = (
    "software and applications development",
    "computer programming",
    "programming computer systems",
    "web programming",
    "database and network design",
    "database management systems",
    "use databases",
    "manage database",
    "query languages",
    "data extraction, transformation and loading",
    "managing, gathering and storing digital data",
    "accessing and analysing digital data",
    "store digital data and systems",
    "digital data",
    "ict data",
    "ict systems",
    "ict project management",
    "information and communication technologies",
    "computer systems",
    "computer technology",
    "computer use",
    "working with computers",
    "resolving computer problems",
    "protecting ict devices",
    "penetration testing",
    "firewall",
    "software configuration management",
    "digital game creation systems",
)

EXCLUDE_BROADER_PATTERNS = (
    "audio-visual",
    "office equipment",
    "radio equipment",
    "communications equipment",
    "electrical",
    "electronic",
    "precision equipment",
    "computer aided design",
    "control machinery",
    "marketing",
    "advertising",
    "financial",
    "library",
    "archival",
    "medical",
    "artistic",
    "print",
    "photographic",
    "creating visual displays",
    "wooden and metal components",
)


@dataclass(frozen=True)
class EscoSkill:
    skill_name: str
    concept_uri: str
    skill_type: str
    reuse_level: str
    broader_concepts: str
    description: str
    alt_labels: tuple[str, ...]


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_key(value: str | None) -> str:
    return normalize_text(value).casefold()


def split_broader_concepts(value: str | None) -> list[str]:
    return [normalize_text(part) for part in str(value or "").split("|") if normalize_text(part)]


def split_alt_labels(value: str | None) -> list[str]:
    labels: list[str] = []
    for part in re.split(r"\s*(?:\||\r?\n)\s*", str(value or "")):
        label = normalize_text(part)
        if label:
            labels.append(label)
    return labels


def concept_matches(concept: str, patterns: Iterable[str]) -> bool:
    concept_key = concept.casefold()
    return any(pattern.casefold() in concept_key for pattern in patterns)


def is_it_data_skill(row: dict[str, str]) -> bool:
    concepts = split_broader_concepts(row.get("broaderConceptPT"))
    if not concepts:
        return False

    has_include = any(concept_matches(concept, INCLUDE_BROADER_PATTERNS) for concept in concepts)
    if not has_include:
        return False

    has_exclude = any(concept_matches(concept, EXCLUDE_BROADER_PATTERNS) for concept in concepts)
    if has_exclude:
        return any(
            concept_matches(concept, INCLUDE_BROADER_PATTERNS)
            and not concept_matches(concept, EXCLUDE_BROADER_PATTERNS)
            for concept in concepts
        )

    return True


def is_valid_alias(canonical: str, alias: str) -> bool:
    alias = normalize_text(alias)
    if not alias:
        return False
    if normalize_key(alias) == normalize_key(canonical):
        return False
    if len(alias) > 80:
        return False
    if len(alias.split()) > 8:
        return False
    return True


def read_esco_it_skills(esco_csv_path: Path) -> tuple[int, list[EscoSkill], list[dict[str, str]]]:
    filtered: list[EscoSkill] = []
    excluded_samples: list[dict[str, str]] = []

    with esco_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        total = 0
        seen: set[str] = set()

        for row in reader:
            total += 1
            skill_name = normalize_text(row.get("preferredLabel"))
            if not skill_name:
                continue

            if not is_it_data_skill(row):
                if len(excluded_samples) < 30:
                    excluded_samples.append(row)
                continue

            key = normalize_key(skill_name)
            if key in seen:
                continue
            seen.add(key)

            filtered.append(
                EscoSkill(
                    skill_name=skill_name,
                    concept_uri=normalize_text(row.get("conceptUri")),
                    skill_type=normalize_text(row.get("skillType")),
                    reuse_level=normalize_text(row.get("reuseLevel")),
                    broader_concepts=" | ".join(split_broader_concepts(row.get("broaderConceptPT"))),
                    description=normalize_text(row.get("description")),
                    alt_labels=tuple(split_alt_labels(row.get("altLabels"))),
                )
            )

    return total, filtered, excluded_samples


def read_existing_skills(path: Path) -> list[str]:
    skills: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "name" not in (reader.fieldnames or []):
            raise ValueError(f"{path} must contain a 'name' column")
        for row in reader:
            name = normalize_text(row.get("name"))
            if name:
                skills.append(name)
    return skills


def read_existing_aliases(path: Path) -> list[dict[str, str]]:
    aliases: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"canonical", "alias", "score"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        for row in reader:
            canonical = normalize_text(row.get("canonical"))
            alias = normalize_text(row.get("alias"))
            score = normalize_text(row.get("score")) or "1.0"
            if canonical and alias:
                aliases.append({"canonical": canonical, "alias": alias, "score": score})
    return aliases


def write_esco_filtered(path: Path, skills: list[EscoSkill]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "skill_name",
                "concept_uri",
                "skill_type",
                "reuse_level",
                "broader_concepts",
                "description",
            ],
        )
        writer.writeheader()
        for skill in skills:
            writer.writerow(
                {
                    "skill_name": skill.skill_name,
                    "concept_uri": skill.concept_uri,
                    "skill_type": skill.skill_type,
                    "reuse_level": skill.reuse_level,
                    "broader_concepts": skill.broader_concepts,
                    "description": skill.description,
                }
            )


def write_merged_skills(path: Path, skills: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["skill_name"])
        writer.writeheader()
        for skill_name in skills:
            writer.writerow({"skill_name": skill_name})


def write_aliases(path: Path, aliases: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["canonical", "alias", "score"])
        writer.writeheader()
        writer.writerows(aliases)


def merge_skills(
    existing_skills: list[str],
    existing_aliases: list[dict[str, str]],
    esco_skills: list[EscoSkill],
) -> tuple[list[str], dict[str, str], int, int]:
    merged: list[str] = []
    canonical_by_key: dict[str, str] = {}

    for skill_name in existing_skills:
        key = normalize_key(skill_name)
        if key in canonical_by_key:
            continue
        canonical_by_key[key] = skill_name
        merged.append(skill_name)

    alias_canonical_added = 0
    for row in existing_aliases:
        canonical = normalize_text(row["canonical"])
        key = normalize_key(canonical)
        if not canonical or key in canonical_by_key:
            continue
        canonical_by_key[key] = canonical
        merged.append(canonical)
        alias_canonical_added += 1

    esco_added = 0
    for skill in esco_skills:
        key = normalize_key(skill.skill_name)
        if key in canonical_by_key:
            continue
        canonical_by_key[key] = skill.skill_name
        merged.append(skill.skill_name)
        esco_added += 1

    return merged, canonical_by_key, alias_canonical_added, esco_added


def merge_aliases(
    existing_aliases: list[dict[str, str]],
    esco_skills: list[EscoSkill],
    canonical_by_key: dict[str, str],
) -> tuple[list[dict[str, str]], int]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for row in existing_aliases:
        canonical = canonical_by_key.get(normalize_key(row["canonical"]), row["canonical"])
        alias = normalize_text(row["alias"])
        if not is_valid_alias(canonical, alias):
            continue
        key = (normalize_key(canonical), normalize_key(alias))
        if key in seen:
            continue
        seen.add(key)
        merged.append({"canonical": canonical, "alias": alias, "score": row["score"]})

    added = 0
    for skill in esco_skills:
        canonical = canonical_by_key[normalize_key(skill.skill_name)]
        for alias in skill.alt_labels:
            if not is_valid_alias(canonical, alias):
                continue
            key = (normalize_key(canonical), normalize_key(alias))
            if key in seen:
                continue
            seen.add(key)
            merged.append({"canonical": canonical, "alias": alias, "score": "1.0"})
            added += 1

    return merged, added


def validate_outputs(merged_skills: list[str], aliases: list[dict[str, str]]) -> None:
    if any(not normalize_text(skill) for skill in merged_skills):
        raise ValueError("Merged skills contains empty skill_name")

    duplicate_skills = len({normalize_key(skill) for skill in merged_skills}) != len(merged_skills)
    if duplicate_skills:
        raise ValueError("Merged skills contains duplicate skill_name values")

    long_skills = [skill for skill in merged_skills if len(skill) > 255]
    if long_skills:
        raise ValueError(f"Merged skills contains names longer than 255 chars: {long_skills[:5]}")

    skill_keys = {normalize_key(skill) for skill in merged_skills}
    missing_canonicals = [
        row["canonical"]
        for row in aliases
        if normalize_key(row["canonical"]) not in skill_keys
    ]
    if missing_canonicals:
        raise ValueError(f"Alias canonical values missing from skills: {missing_canonicals[:10]}")

    alias_matches_canonical = [
        row
        for row in aliases
        if normalize_key(row["canonical"]) == normalize_key(row["alias"])
    ]
    if alias_matches_canonical:
        raise ValueError(f"Aliases matching canonical found: {alias_matches_canonical[:10]}")


def build_outputs(esco_dir: Path, ready_data_dir: Path) -> None:
    esco_csv_path = esco_dir / "digitalSkillsCollection_en.csv"
    existing_skills_path = ready_data_dir / "skills_202605092254.csv"
    existing_aliases_path = ready_data_dir / "skill_aliases.csv"

    for path in (esco_csv_path, existing_skills_path, existing_aliases_path):
        if not path.exists():
            raise FileNotFoundError(str(path))

    total_esco_rows, esco_skills, excluded_samples = read_esco_it_skills(esco_csv_path)
    existing_skills = read_existing_skills(existing_skills_path)
    existing_aliases = read_existing_aliases(existing_aliases_path)

    merged_skills, canonical_by_key, alias_canonical_skill_added, esco_skill_added = merge_skills(
        existing_skills,
        existing_aliases,
        esco_skills,
    )
    merged_aliases, esco_alias_added = merge_aliases(existing_aliases, esco_skills, canonical_by_key)

    validate_outputs(merged_skills, merged_aliases)

    ready_data_dir.mkdir(parents=True, exist_ok=True)
    filtered_path = ready_data_dir / f"esco_it_skills_filtered_{OUTPUT_DATE}.csv"
    merged_skills_path = ready_data_dir / f"merged_skills_with_esco_it_{OUTPUT_DATE}.csv"
    merged_aliases_path = ready_data_dir / f"skill_aliases_with_esco_it_{OUTPUT_DATE}.csv"

    write_esco_filtered(filtered_path, esco_skills)
    write_merged_skills(merged_skills_path, merged_skills)
    write_aliases(merged_aliases_path, merged_aliases)

    print("ESCO IT/data skill export completed")
    print(f"esco_digital_rows={total_esco_rows}")
    print(f"esco_filtered_rows={len(esco_skills)}")
    print(f"existing_skill_rows={len(existing_skills)}")
    print(f"alias_canonical_skill_rows_added={alias_canonical_skill_added}")
    print(f"esco_new_skill_rows={esco_skill_added}")
    print(f"merged_skill_rows={len(merged_skills)}")
    print(f"existing_alias_rows={len(existing_aliases)}")
    print(f"esco_new_alias_rows={esco_alias_added}")
    print(f"merged_alias_rows={len(merged_aliases)}")
    print(f"filtered_csv={filtered_path}")
    print(f"merged_skills_csv={merged_skills_path}")
    print(f"merged_aliases_csv={merged_aliases_path}")

    print("\nIncluded samples:")
    for skill in esco_skills[:30]:
        print(f"- {skill.skill_name} [{skill.broader_concepts}]")

    print("\nExcluded samples:")
    for row in excluded_samples[:30]:
        print(
            "- "
            f"{normalize_text(row.get('preferredLabel'))} "
            f"[{' | '.join(split_broader_concepts(row.get('broaderConceptPT')))}]"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter ESCO digital skills to ICT/data skills and merge them with local skill CSVs."
    )
    parser.add_argument("--esco-dir", type=Path, default=DEFAULT_ESCO_DIR)
    parser.add_argument("--ready-data-dir", type=Path, default=DEFAULT_READY_DATA_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_outputs(args.esco_dir, args.ready_data_dir)


if __name__ == "__main__":
    main()

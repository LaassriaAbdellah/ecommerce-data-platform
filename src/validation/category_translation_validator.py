"""Category translation quality and independent Products coverage indicators."""

from pathlib import Path
import json

import pandas as pd

from src.validation.common import (
    check_required_columns, check_missing_ids, check_duplicate_ids,
)
from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"
PT = "product_category_name"
EN = "product_category_name_english"
REQUIRED_COLUMNS = [PT, EN]


def validate_category_translation(translations: pd.DataFrame, products: pd.DataFrame):
    """Preserve rows/values; conflicting and duplicate-key rules are exclusive.

    Conflicting: every row of a nonblank PT key with >1 distinct nonblank EN.
    Duplicate: every occurrence of a repeated nonblank PT key not conflicting.
    Missing fields are separate issues; blank keys never count as duplicates.
    Comparisons are exact; normalization is used only for writing indicators.
    """
    check_required_columns(translations, REQUIRED_COLUMNS)
    check_required_columns(products, [PT])
    missing_pt = check_missing_ids(translations, PT)
    missing_en = check_missing_ids(translations, EN)
    usable = translations.loc[~missing_pt & ~missing_en, REQUIRED_COLUMNS]
    english_per_key = usable.groupby(PT)[EN].nunique()
    conflicting_keys = english_per_key[english_per_key.gt(1)].index
    conflicting = ~missing_pt & translations[PT].isin(conflicting_keys)
    rules = {
        "missing_product_category_name": missing_pt,
        "missing_product_category_name_english": missing_en,
        "duplicate_product_category_name": (
            check_duplicate_ids(translations, PT) & ~missing_pt & ~conflicting
        ),
        "conflicting_category_translation": conflicting,
    }
    result, report = apply_quality_rules(
        translations, rules, entity_name="category_translation"
    )

    missing_product_category = check_missing_ids(products, PT)
    untranslated = ~missing_product_category & ~products[PT].isin(usable[PT])
    untranslated_counts = products.loc[untranslated, PT].value_counts()
    unused = usable.loc[~usable[PT].isin(products.loc[~missing_product_category, PT]), PT]
    portuguese_per_english = usable.groupby(EN)[PT].nunique()
    shared_english = portuguese_per_english[portuguese_per_english.gt(1)].index
    shared_pairs = usable.loc[usable[EN].isin(shared_english)].drop_duplicates()
    report["business_indicators"] = {
        "untranslated_distinct_categories": int(len(untranslated_counts)),
        "untranslated_product_rows": int(untranslated.sum()),
        "untranslated_products_by_category": {
            str(category): int(count) for category, count in untranslated_counts.items()
        },
        "products_without_category_rows": int(missing_product_category.sum()),
        "unused_translated_distinct_categories": int(unused.nunique()),
        "unused_translated_categories": sorted(unused.unique().tolist()),
        "shared_english_distinct_labels": int(len(shared_english)),
        "shared_english_categories": {
            str(label): sorted(group[PT].tolist())
            for label, group in shared_pairs.groupby(EN)
        },
        "products_on_conflicting_categories_rows": int(
            products[PT].isin(conflicting_keys).sum()
        ),
    }
    writing = {}
    for col, absent in [(PT, missing_pt), (EN, missing_en)]:
        text = translations.loc[~absent, col].astype("string")
        normalized = (text.str.casefold().str.normalize("NFKD")
            .str.replace(r"[\u0300-\u036f]", "", regex=True)
            .str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_"))
        keys = pd.DataFrame({"source": text, "key": normalized})
        variant_counts = keys.groupby("key").source.nunique()
        variant_keys = variant_counts[variant_counts.gt(1)].index
        writing[col] = {
            "variant_groups": int(len(variant_keys)),
            "variants": {
                str(key): sorted(group.source.unique().tolist())
                for key, group in keys.loc[keys.key.isin(variant_keys)].groupby("key")
            },
            "outer_whitespace_rows": int(text.ne(text.str.strip()).sum()),
            "unusual_slug_rows": int(
                (~text.str.fullmatch("[a-z0-9]+(?:_[a-z0-9]+)*", na=False)).sum()
            ),
        }
    report["writing_indicators"] = writing
    report["rule_semantics"] = {
        "unit": "Rule counts are source rows, including every involved occurrence. review_rows counts each row once; quality_issue_count counts independent rules.",
        "exclusive_key_rules": "A present PT key with >1 distinct present EN flags all its rows as conflicting only. Otherwise repeated present PT keys flag duplicate only. Exact source comparisons, no trimming/case folding.",
        "missing": "Null/empty/whitespace fields are missing. Missing PT keys excluded from duplicate/conflict. Missing EN is an independent issue even in a conflicting group.",
        "english": "EN is not required to be unique across PT keys.",
        "coverage": "A present Products category has coverage if at least one complete PT/EN pair exists. Conflicting coverage is reported separately, never resolved. Missing Products categories excluded from untranslated counts.",
        "writing": "Exploratory casefold/NFKD/remove accents/nonalphanumeric to underscore/strip border underscores. No source correction; variants and coverage never affect quality.",
    }
    return result, report


def main():
    translations = pd.read_csv(DATA_DIR / "product_category_name_translation.csv")
    products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv", usecols=[PT])
    result, report = validate_category_translation(translations, products)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_DIR / "category_translation_validated.csv", index=False)
    with (OUTPUT_DIR / "category_translation_quality_report.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

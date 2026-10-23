
import json

import pandas as pd


def apply_quality_rules(
    df: pd.DataFrame,
    rules: dict[str, pd.Series],
    entity_name: str,
):
    """
    Applique les résultats des règles de validation.

    Chaque règle est une série booléenne :
        True  = anomalie détectée
        False = aucune anomalie détectée

    Retourne :
        - DataFrame avec indicateurs de qualité
        - Rapport de validation
    """

    result = df.copy()

    # Construire le tableau des anomalies
    checks = pd.DataFrame(index=result.index)

    for rule_name, mask in rules.items():
        if not isinstance(mask, pd.Series):
            raise TypeError(
                f"La règle '{rule_name}' doit être une Series."
            )

        if not mask.index.equals(result.index):
            raise ValueError(
                f"Index incompatible pour la règle '{rule_name}'."
            )

        if not pd.api.types.is_bool_dtype(mask.dtype):
            raise TypeError(
                f"La règle '{rule_name}' doit être booléenne."
            )

        checks[rule_name] = mask.fillna(False).astype(bool)

    # Nombre d'anomalies par ligne
    result["quality_issue_count"] = checks.sum(axis=1)

    # Statut de qualité
    result["quality_status"] = "valid"

    result.loc[
        result["quality_issue_count"] > 0,
        "quality_status"
    ] = "review"

    # Motifs d'anomalie
    result["quality_issues"] = [
        json.dumps(
            checks.columns[row.to_numpy()].tolist(),
            ensure_ascii=False,
        )
        for _, row in checks.iterrows()
    ]

    # Rapport générique
    report = {
        "entity": entity_name,
        "total_rows": int(len(result)),
        "valid_rows": int(
            result["quality_status"].eq("valid").sum()
        ),
        "review_rows": int(
            result["quality_status"].eq("review").sum()
        ),
        "anomalies_by_rule": {
            name: int(count)
            for name, count in checks.sum().items()
        },
    }

    return result, report

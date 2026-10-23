
import pandas as pd


def check_required_columns(df, required_columns):
    """Vérifie que toutes les colonnes obligatoires existent."""
    missing = set(required_columns) - set(df.columns)

    if missing:
        raise ValueError(
            f"Colonnes obligatoires manquantes : {sorted(missing)}"
        )


def check_missing_ids(df, column):
    """Détecte les identifiants absents ou vides."""
    values = df[column].astype("string")

    return (
        values.isna()
        | values.str.strip().eq("").fillna(False)
    )


def check_duplicate_ids(df, column):
    """Détecte les identifiants dupliqués."""
    return df[column].duplicated(keep=False)


def check_invalid_dates(df, date_columns):
    """
    Convertit les dates et détecte les valeurs non convertibles.

    Retourne un DataFrame converti et un dictionnaire
    contenant les règles de validation.
    """
    result = df.copy()
    rules = {}

    for column in date_columns:
        original = result[column]
        converted = pd.to_datetime(original, errors="coerce")

        rules[f"invalid_{column}"] = (
            original.notna() & converted.isna()
        )

        result[column] = converted

    return result, rules

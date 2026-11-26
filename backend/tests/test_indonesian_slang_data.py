from ruangkampus.services.indonesian_slang_data import (
    dataset_manifest,
    extract_slang_hints,
    load_slang_examples,
    load_slang_lexicon,
    load_slang_normalization_map,
    merge_slang_normalization_map,
)


def test_bundled_slang_dataset_matches_its_versioned_manifest():
    manifest = dataset_manifest()
    lexicon = load_slang_lexicon()
    mapping = load_slang_normalization_map()
    examples = load_slang_examples()

    assert manifest["schema_version"] == "1.0.0"
    assert len(lexicon["entries"]) == 313
    assert len(mapping) == 269
    assert len(examples) == 35


def test_dataset_map_is_additive_and_legacy_mapping_wins_conflicts():
    merged = merge_slang_normalization_map({"gue": "aku", "gua": "aku", "lau": "kamu"})
    dataset = load_slang_normalization_map()

    assert len(merged) >= len(dataset)
    assert merged["gue"] == "aku"
    assert merged["gua"] == "aku"
    assert merged["lau"] == "kamu"
    assert merged["gmn"] == "bagaimana"


def test_contextual_slang_is_hinted_but_not_added_to_safe_exact_map():
    mapping = load_slang_normalization_map()
    hints = extract_slang_hints("Wkwk, gaskeun cari ruang; aku lagi mager.")

    assert "gas" not in mapping
    assert "spill" not in mapping
    assert "teh" not in mapping
    assert "sa" not in mapping
    assert {"wkwk", "gaskeun", "mager"}.issubset({item["headword"] for item in hints})


def test_single_short_regional_token_is_not_assumed_to_be_dialect():
    hints = extract_slang_hints("Sa mau cari ruangan.")
    assert "sa" not in {item["headword"] for item in hints}


def test_regional_hints_require_corroborating_terms_from_same_region():
    hints = extract_slang_hints("Sa tra jadi ke kampus.")
    words = {item["headword"] for item in hints}
    assert {"sa", "tra"}.issubset(words)


def test_hint_extraction_is_bounded():
    assert len(extract_slang_hints("wkwk gaskeun mager banget", limit=50)) <= 8

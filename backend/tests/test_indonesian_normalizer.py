import pytest

from ruangkampus.schemas import AssistantNormalizationResult
from ruangkampus.services.indonesian_normalizer import (
    find_positive_catalog_values,
    find_positive_facility_filters,
    is_negated_phrase,
    normalize_indonesian_message,
)


NORMALIZATION_CASES = [
    ("gmn", "bagaimana"),
    ("gimana", "bagaimana"),
    ("ga", "tidak"),
    ("gak", "tidak"),
    ("nggak", "tidak"),
    ("enggak", "tidak"),
    ("engga", "tidak"),
    ("lg", "lagi"),
    ("lagi", "lagi"),
    ("yg", "yang"),
    ("dmn", "di mana"),
    ("dpt", "dapat"),
    ("bs", "bisa"),
    ("bgt", "banget"),
    ("utk", "untuk"),
    ("krn", "karena"),
    ("sm", "sama"),
    ("mo", "mau"),
    ("pengen", "ingin"),
    ("cariin", "cari"),
    ("nyari", "mencari"),
    ("nugas", "mengerjakan tugas"),
    ("pinjem", "meminjam"),
    ("minjem", "meminjam"),
    ("dipake", "digunakan"),
    ("pake", "pakai"),
    ("ruangn", "ruangan"),
    ("kosng", "kosong"),
    ("fasilits", "fasilitas"),
    ("proyektorr", "proyektor"),
    ("reservsi", "reservasi"),
    ("BROOO", "bro"),
    ("ruanggg", "ruang"),
    ("kosonggg", "kosong"),
    ("tolonggg", "tolong"),
    ("makasihhh", "makasih"),
    ("proyektorr", "proyektor"),
    ("donggg", "dong"),
    ("wkwkwk", "wkwk"),
    ("hehehehe", "hehe"),
    ("ruangannnn", "ruangan"),
    ("kelasssss", "kelas"),
    ("kosooooong", "kosong"),
    ("tolooong", "tolong"),
    ("BRO", "bro"),
    ("KAK", "kak"),
    ("RUANGAN", "ruangan"),
    ("FTII", "ftii"),
    ("PROYEKTOR", "proyektor"),
    ("WIFI", "wifi"),
    ("Halo, Kak!", "halo kak"),
    ("ADA RUANGAN KOSONG???", "ada ruangan kosong"),
    ("  ruang   rapat  ", "ruang rapat"),
    ("mau, pinjem ruangan!!!", "mau meminjam ruangan"),
    ("kelas yg lg ga dipake", "kelas yang lagi tidak digunakan"),
    ("gmn cara reservasi?", "bagaimana cara reservasi"),
    ("Cariin tempat buat nugas dong.", "cari tempat buat mengerjakan tugas dong"),
    ("Ruang FTII yg kosong jam 2 ada?", "ruang ftii yang kosong jam 2 ada"),
    ("Mau pinjem ruangan buat rapat.", "mau meminjam ruangan buat rapat"),
    ("Saya tidak mau ruangan ber-AC.", "saya tidak mau ruangan ber-ac"),
    ("Jangan cari ruangan dengan proyektor.", "jangan cari ruangan dengan proyektor"),
    ("Bukan fakultas teknik tetapi fakultas ekonomi.", "bukan fakultas teknik tetapi fakultas ekonomi"),
    ("Tidak perlu ruangan besar.", "tidak perlu ruangan besar"),
    ("Saya tidak ingin melakukan reservasi.", "saya tidak ingin melakukan reservasi"),
    ("Cari ruang dengan fasilitas wifi, bukan proyektor.", "cari ruang dengan fasilitas wifi bukan proyektor"),
    ("Bro ada ruang kosong nggak?", "bro ada ruang kosong tidak"),
    ("Cariin tempat buat nugas dong", "cari tempat buat mengerjakan tugas dong"),
    ("Ada kelas yg lg ga dipake?", "ada kelas yang lagi tidak digunakan"),
    ("Mau pinjem ruangan buat rapat", "mau meminjam ruangan buat rapat"),
    ("Ruang FTII yg kosong jam 2 ada", "ruang ftii yang kosong jam 2 ada"),
    ("Gmn cara reservasi", "bagaimana cara reservasi"),
    ("Ruangn kosng ada ga", "ruangan kosong ada tidak"),
    ("Wkwkwk kamu robot ya", "wkwk kamu robot ya"),
    ("Saya tidak ingin ruangan yang ada AC", "saya tidak ingin ruangan yang ada ac"),
    ("Jangan cari ruangan dengan proyektor", "jangan cari ruangan dengan proyektor"),
    ("Bukan fakultas teknik, tetapi fakultas ekonomi", "bukan fakultas teknik tetapi fakultas ekonomi"),
    ("Cari ruang dengan fasilitas wifi bukan proyektor", "cari ruang dengan fasilitas wifi bukan proyektor"),
    ("Halo, saya ingin mencari ruangan rapat.", "halo saya ingin mencari ruangan rapat"),
    ("Selamat pagi, apakah ada ruang kelas?", "selamat pagi apakah ada ruang kelas"),
    ("Saya ingin ruangan untuk 20 orang.", "saya ingin ruangan untuk 20 orang"),
    ("Tolong carikan ruangan di Gedung A.", "tolong carikan ruangan di gedung a"),
    ("Apakah ruang laboratorium tersedia?", "apakah ruang laboratorium tersedia"),
    ("Saya butuh ruangan untuk presentasi.", "saya butuh ruangan untuk presentasi"),
    ("Mohon informasi fasilitas ruangan.", "mohon informasi fasilitas ruangan"),
    ("Saya ingin meminjam ruang untuk diskusi.", "saya ingin meminjam ruang untuk diskusi"),
    ("Ada ruangan untuk seminar mahasiswa?", "ada ruangan untuk seminar mahasiswa"),
    ("Tolong jangan carikan ruangan yang ada AC.", "tolong jangan carikan ruangan yang ada ac"),
    ("Tidak ada kebutuhan proyektor.", "tidak ada kebutuhan proyektor"),
    ("Bukan ruang kelas, melainkan laboratorium.", "bukan ruang kelas melainkan laboratorium"),
    ("Saya hanya membutuhkan wifi.", "saya hanya membutuhkan wifi"),
    ("Tanpa pendingin ruangan, jika memungkinkan.", "tanpa pendingin ruangan jika memungkinkan"),
    ("Kecuali ruangan yang berada di lantai satu.", "kecuali ruangan yang berada di lantai satu"),
    ("I need a meeting room untuk 10 people.", "i need a meeting room untuk 10 people"),
    ("Cari meeting room dengan projector.", "cari meeting room dengan projector"),
    ("Butuh room untuk brainstorming.", "butuh room untuk brainstorming"),
    ("Please carikan ruang untuk discussion.", "please carikan ruang untuk discussion"),
    ("Ada classroom yang kosong tomorrow?", "ada classroom yang kosong tomorrow"),
    ("wifi projector sound system", "wifi projector sound system"),
    ("Ruang R-101 di Gedung A", "ruang r-101 di gedung a"),
    ("Ruang RK-FTII-101", "ruang rk-ftii-101"),
    ("Jadwal 2026-11-30 jam 09:00-11:00", "jadwal 2026-11-30 jam 09:00-11:00"),
    ("Tanggal 2026-12-01 pukul 13.30 sampai 15.00", "tanggal 2026-12-01 pukul 13.30 sampai 15.00"),
    ("Room A.2/101", "room a.2/101"),
    ("FTII-02", "ftii-02"),
    ("Bro, kak, dong, nih", "bro kak dong nih"),
    ("WKWKWK ada ruang?", "wkwk ada ruang"),
    ("Hehehe, saya mau tanya", "hehe saya mau tanya"),
    ("Tolong dong cariin ruang", "tolong dong cari ruang"),
    ("Kak, ada kelas yang kosong?", "kak ada kelas yang kosong"),
    ("Brooo, saya butuh ruang", "bro saya butuh ruang"),
    ("Hai kak, mau tanya fasilitas", "hai kak mau tanya fasilitas"),
    ("Permisi dong, ada ruangan?", "permisi dong ada ruangan"),
    ("Makasih ya, infonya", "makasih ya infonya"),
    ("Tidak, bukan, jangan, tanpa, kecuali, hanya", "tidak bukan jangan tanpa kecuali hanya"),
    ("jangan jangan cari ruangan", "jangan jangan cari ruangan"),
    ("bukan fakultas teknik tetapi fakultas ekonomi", "bukan fakultas teknik tetapi fakultas ekonomi"),
    ("wifi bukan proyektor", "wifi bukan proyektor"),
    ("proyektor tanpa whiteboard", "proyektor tanpa whiteboard"),
    ("ruangan tidak ber-ac", "ruangan tidak ber-ac"),
    ("kelas jangan dekat jalan", "kelas jangan dekat jalan"),
    ("tidak perlu ruangan besar", "tidak perlu ruangan besar"),
    ("saya tidak ingin melakukan reservasi", "saya tidak ingin melakukan reservasi"),
    ("hanya untuk rapat kecil", "hanya untuk rapat kecil"),
    ("Reservasi untuk 25 peserta pada 2026-12-02", "reservasi untuk 25 peserta pada 2026-12-02"),
    ("Meeting jam 10:00-12:00 di R-201", "meeting jam 10:00-12:00 di r-201"),
    ("Room code RK-FTII-201 jangan diubah", "room code rk-ftii-201 jangan diubah"),
    ("Kelas A-101, bukan kelas A-102", "kelas a-101 bukan kelas a-102"),
    ("Butuh 12 pax untuk workshop", "butuh 12 pax untuk workshop"),
    ("ruang multimedia untuk 30 people", "ruang multimedia untuk 30 people"),
    ("gedung Ahmad Dahlan hari senin", "gedung ahmad dahlan hari senin"),
    ("fakultas FTII dan fasilitas wifi", "fakultas ftii dan fasilitas wifi"),
    ("Ruang Komputer Dasar lantai 2", "ruang komputer dasar lantai 2"),
    ("tanpa AC tetapi dengan wifi", "tanpa ac tetapi dengan wifi"),
    ("jangan pakai projector", "jangan pakai projector"),
    ("bukan ruang rapat melainkan ruang kelas", "bukan ruang rapat melainkan ruang kelas"),
    ("hanya ruangan kecil untuk diskusi", "hanya ruangan kecil untuk diskusi"),
    ("tolong carikan jadwal untuk besok", "tolong carikan jadwal untuk besok"),
    ("ada ruangan hari Jumat?", "ada ruangan hari jumat"),
    ("Cari ruangan di gedung A untuk 8 orang", "cari ruangan di gedung a untuk 8 orang"),
    ("saya mau ruang rapat tanpa proyektor", "saya mau ruang rapat tanpa proyektor"),
    ("jangan memilih fakultas teknik", "jangan memilih fakultas teknik"),
    ("bukan FTII, tetapi FKIP", "bukan ftii tetapi fkip"),
    ("wifi, projector, and whiteboard", "wifi projector and whiteboard"),
    ("hello, can you find ruang rapat?", "hello can you find ruang rapat"),
    ("jam 09.00 hingga 10.30", "jam 09.00 hingga 10.30"),
    ("09:00-10:00", "09:00-10:00"),
    ("2026-12-31", "2026-12-31"),
    ("A-1/B.2", "a-1/b.2"),
    ("Cari lagi ruangan.", "cari lagi ruangan"),
    ("Ada ruangan kosong lagi?", "ada ruangan kosong lagi"),
]


@pytest.mark.parametrize(("raw_text", "expected"), NORMALIZATION_CASES)
def test_normalization_golden_cases(raw_text, expected):
    result = normalize_indonesian_message(raw_text)

    assert isinstance(result, AssistantNormalizationResult)
    assert result.raw_text == raw_text
    assert result.normalized_text == expected
    assert isinstance(result.tokens, list)
    assert isinstance(result.normalized_tokens, list)
    assert isinstance(result.filler_tokens, list)
    assert isinstance(result.corrections, list)
    assert isinstance(result.unknown_tokens, list)
    assert all(item.confidence is None for item in result.corrections)


def test_normalization_golden_set_has_at_least_one_hundred_cases():
    assert len(NORMALIZATION_CASES) >= 100


def test_raw_message_and_parser_message_are_both_retained():
    result = normalize_indonesian_message("BROOO, tolong cariin ruangn kosong dong")

    assert result.raw_text == "BROOO, tolong cariin ruangn kosong dong"
    assert result.normalized_text == "bro tolong cari ruangan kosong dong"
    assert result.parser_text == "cari ruangan kosong"
    assert {"bro", "tolong", "dong"}.issubset(set(result.filler_tokens))
    assert {item.correction_type for item in result.corrections} >= {
        "REPEATED_CHARACTER", "SLANG_ABBREVIATION", "STATIC_TYPO"
    }


def test_negation_and_restriction_words_are_preserved_for_the_next_parser_stage():
    samples = (
        ("Saya tidak mau ruangan ber-AC.", "tidak"),
        ("Bukan fakultas teknik, tetapi fakultas ekonomi.", "bukan"),
        ("Jangan cari ruangan yang menggunakan proyektor.", "jangan"),
        ("Ruangan tanpa AC.", "tanpa"),
        ("Pilih semua fasilitas kecuali proyektor.", "kecuali"),
        ("Saya hanya membutuhkan wifi.", "hanya"),
    )

    for sample, required_token in samples:
        result = normalize_indonesian_message(sample)
        assert required_token in result.normalized_tokens


def test_only_symbols_and_whitespace_are_cleaned_without_inventing_tokens():
    for sample in ("!!!???", "   ...   ", "###"):
        result = normalize_indonesian_message(sample)
        assert result.normalized_text == ""
        assert result.parser_text == ""
        assert result.tokens == []


def test_room_codes_and_date_time_tokens_are_not_reduced_as_repeated_characters():
    result = normalize_indonesian_message("RK-FTII-111 2026-11-30 09:00-11:00")

    assert result.normalized_tokens == ["rk-ftii-111", "2026-11-30", "09:00-11:00"]


def test_dynamic_typo_correction_uses_only_observed_catalog_vocabulary():
    catalog = {
        "faculties": [{"value": "FTII", "source_values": ["FTII"]}],
        "buildings": [{"value": "Gedung Ahmad Dahlan", "source_values": ["Gedung Ahmad Dahlan"]}],
        "facilities": [{"canonical_name": "projector", "source_values": ["Projector"], "aliases": ["projector", "proyektor"]}],
        "rooms": [{
            "room_name": "Laboratorium Komputer Dasar",
            "room_code": "RK-FTII-101",
            "faculty": "FTII",
            "building": "Gedung Ahmad Dahlan",
            "floor": "2",
            "location_description": "Dekat lobby",
            "facilities": ["Projector"],
        }],
    }
    result = normalize_indonesian_message("laboratorum di FTII", catalog)

    assert result.normalized_tokens[:2] == ["laboratorium", "di"]
    correction = next(item for item in result.corrections if item.original_token == "laboratorum")
    assert correction.normalized_token == "laboratorium"
    assert correction.correction_type == "DOMAIN_TYPO"
    assert correction.source == "catalog.domain_vocabulary"
    assert correction.confidence is None


def test_ambiguous_dynamic_typo_is_not_corrected():
    from ruangkampus.services.indonesian_normalizer import _dynamic_typo_candidate

    assert _dynamic_typo_candidate("fakultaa", {"fakultas", "fakultab"}) is None


def test_positive_catalog_matching_ignores_negated_faculty_and_keeps_contrast_clause():
    entries = [
        {"value": "Fakultas Teknik", "source_values": ["Fakultas Teknik"]},
        {"value": "Fakultas Ekonomi", "source_values": ["Fakultas Ekonomi"]},
    ]

    values = find_positive_catalog_values(
        "bukan fakultas teknik tetapi fakultas ekonomi",
        entries,
    )

    assert values == ["Fakultas Ekonomi"]


def test_catalog_matching_does_not_resolve_multiple_positive_faculties():
    entries = [
        {"value": "FTII", "source_values": ["FTII"]},
        {"value": "FKIP", "source_values": ["FKIP"]},
    ]

    assert find_positive_catalog_values("FTII atau FKIP", entries) == ["FKIP", "FTII"]


def test_facility_filtering_uses_only_catalogued_positive_terms():
    catalog = {
        "facilities": [
            {"canonical_name": "projector", "source_values": ["Projector"], "aliases": ["projector", "proyektor"]},
            {"canonical_name": "wifi", "source_values": ["WiFi"], "aliases": ["wifi", "internet"]},
        ]
    }

    assert find_positive_facility_filters("wifi, bukan proyektor", catalog) == ["wifi"]
    assert find_positive_facility_filters("jangan cari proyektor", catalog) == []
    assert find_positive_facility_filters("butuh proyektor", catalog) == ["projector"]


def test_phrase_negation_is_overridden_by_a_later_contrast():
    message = "tidak mau AC tetapi perlu wifi"
    ac_start = message.index("AC")
    wifi_start = message.index("wifi")

    assert is_negated_phrase(message, ac_start) is True
    assert is_negated_phrase(message, wifi_start) is False



def test_unknown_catalogue_facility_is_filtered_by_its_observed_label_without_canonicalizing():
    catalog = {
        "facilities": [
            {
                "canonical_name": None,
                "display_name": "CCTV",
                "source_values": ["CCTV"],
                "aliases": [],
            }
        ]
    }

    assert find_positive_facility_filters("butuh CCTV", catalog) == ["CCTV"]
    assert find_positive_facility_filters("jangan gunakan CCTV", catalog) == []



def test_hanya_is_a_positive_restriction_not_a_negative_facility_clause():
    catalog = {
        "facilities": [
            {"canonical_name": "wifi", "source_values": ["WiFi"], "aliases": ["wifi", "internet"]}
        ]
    }

    assert find_positive_facility_filters("saya hanya membutuhkan wifi", catalog) == ["wifi"]


def test_air_conditioner_in_a_negated_phrase_is_not_a_positive_filter():
    catalog = {
        "facilities": [
            {
                "canonical_name": "air conditioner",
                "source_values": ["AC"],
                "aliases": ["ac", "air conditioner", "pendingin"],
            }
        ]
    }

    assert find_positive_facility_filters(
        "saya tidak ingin ruangan yang ada AC",
        catalog,
    ) == []


def test_facility_alias_not_observed_in_catalog_is_not_promoted_to_canonical():
    assert find_positive_facility_filters(
        "butuh proyektor",
        {"facilities": []},
    ) == []

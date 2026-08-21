"""RAM module_type and storage interface compatibility hard-gates."""

from __future__ import annotations

from matching import (
    MatchStatus,
    ModuleType,
    ProductCategory,
    StorageInterface,
    build_profile_from_query,
    extract_module_type,
    extract_storage_interface,
    match_listing,
)

_RAM_UDIMM_QUERY = "Kingston Fury DDR5 UDIMM KF560"
_RAM_UDIMM_TITLE = "Kingston Fury DDR5 UDIMM KF560 32GB desktop memory"
_STORAGE_NVME_QUERY = "Samsung 990 Pro 4TB NVMe"
_STORAGE_NVME_TITLE = "Samsung 990 Pro 4TB NVMe M.2 SSD"


def test_ram_query_extracts_udimm_and_ram_category() -> None:
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    assert profile.category is ProductCategory.RAM
    assert profile.module_type is ModuleType.UDIMM
    assert profile.storage_interface is StorageInterface.UNKNOWN


def test_ram_query_extracts_rdimm_from_ecc_registered() -> None:
    profile = build_profile_from_query("Kingston Fury ECC Registered DDR5 KF560")
    assert profile.category is ProductCategory.RAM
    assert profile.module_type is ModuleType.RDIMM


def test_ram_query_extracts_sodimm() -> None:
    profile = build_profile_from_query("Crucial DDR5 32GB SO-DIMM CT32")
    assert profile.module_type is ModuleType.SODIMM


def test_unspecified_ram_query_is_unknown_module_type() -> None:
    profile = build_profile_from_query("Kingston Fury DDR5 KF560")
    assert profile.category is ProductCategory.RAM
    assert profile.module_type is ModuleType.UNKNOWN


def test_matching_udimm_listing_confirms() -> None:
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    result = match_listing(profile, _RAM_UDIMM_TITLE)
    assert result.status is MatchStatus.CONFIRMED
    assert result.reason == "model token match"


def test_rdimm_listing_rejected_against_udimm_profile() -> None:
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    result = match_listing(
        profile,
        "Kingston Fury DDR5 RDIMM KF560 ECC Registered 32GB",
    )
    assert result.status is MatchStatus.REJECTED
    assert result.reason == "module type mismatch"


def test_unknown_listing_module_type_is_review() -> None:
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    result = match_listing(profile, "Kingston Fury DDR5 KF560 32GB")
    assert result.status is MatchStatus.REVIEW
    assert result.reason == "unknown module type"


def test_unspecified_ram_profile_never_assumes_udimm() -> None:
    profile = build_profile_from_query("Kingston Fury DDR5 KF560")
    result = match_listing(profile, "Kingston Fury DDR5 KF560 32GB UDIMM")
    assert result.status is MatchStatus.REVIEW
    assert result.reason == "unknown module type"


def test_structured_extra_wins_over_title_for_module_type() -> None:
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    result = match_listing(
        profile,
        _RAM_UDIMM_TITLE,
        extra={"module_type": "RDIMM"},
    )
    assert result.status is MatchStatus.REJECTED
    assert result.reason == "module type mismatch"
    assert extract_module_type(_RAM_UDIMM_TITLE, extra={"moduleType": "SODIMM"}) is (
        ModuleType.SODIMM
    )


def test_ram_kit_is_not_excluded() -> None:
    """A 2x16GB RAM kit is the product, not a CPU+mobo bundle."""
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    result = match_listing(profile, f"{_RAM_UDIMM_TITLE} kit 2x16GB")
    assert result.status is MatchStatus.CONFIRMED
    assert not any(term == "kit" for term in profile.excluded_terms)


def test_ram_full_system_terms_are_rejected() -> None:
    profile = build_profile_from_query(_RAM_UDIMM_QUERY)
    laptop = match_listing(profile, f"Laptop {_RAM_UDIMM_TITLE}")
    assert laptop.status is MatchStatus.REJECTED
    assert laptop.reason.startswith("excluded term:")

    kit = match_listing(profile, f"Aufrüstkit {_RAM_UDIMM_TITLE}")
    assert kit.status is MatchStatus.REJECTED
    assert kit.reason.startswith("excluded term:")

    ssd = match_listing(profile, f"{_RAM_UDIMM_TITLE} SSD 1TB")
    assert ssd.status is MatchStatus.REJECTED
    assert ssd.reason.startswith("excluded term:")


def test_storage_query_extracts_nvme() -> None:
    profile = build_profile_from_query(_STORAGE_NVME_QUERY)
    assert profile.category is ProductCategory.STORAGE
    assert profile.storage_interface is StorageInterface.NVME
    assert profile.module_type is ModuleType.UNKNOWN


def test_matching_nvme_listing_confirms() -> None:
    profile = build_profile_from_query(_STORAGE_NVME_QUERY)
    result = match_listing(profile, _STORAGE_NVME_TITLE)
    assert result.status is MatchStatus.CONFIRMED


def test_sata_listing_rejected_against_nvme_profile() -> None:
    profile = build_profile_from_query(_STORAGE_NVME_QUERY)
    result = match_listing(profile, "Samsung 990 Pro 4TB SATA SSD")
    assert result.status is MatchStatus.REJECTED
    assert result.reason == "storage interface mismatch"


def test_unknown_listing_interface_is_review_when_profile_specifies() -> None:
    profile = build_profile_from_query(_STORAGE_NVME_QUERY)
    result = match_listing(profile, "Samsung 990 Pro 4TB SSD")
    assert result.status is MatchStatus.REVIEW
    assert result.reason == "unknown storage interface"


def test_unspecified_storage_profile_does_not_gate_interface() -> None:
    profile = build_profile_from_query("Samsung 990 Pro 4TB SSD")
    assert profile.category is ProductCategory.STORAGE
    assert profile.storage_interface is StorageInterface.UNKNOWN
    sata = match_listing(profile, "Samsung 990 Pro 4TB SATA SSD")
    nvme = match_listing(profile, "Samsung 990 Pro 4TB NVMe SSD")
    assert sata.status is MatchStatus.CONFIRMED
    assert nvme.status is MatchStatus.CONFIRMED


def test_usb_enclosure_interface() -> None:
    assert extract_storage_interface("Samsung T7 4TB USB-C") is StorageInterface.USB
    assert extract_storage_interface("NVMe enclosure USB 4TB") is StorageInterface.USB


def test_cpu_profile_is_unaffected() -> None:
    profile = build_profile_from_query("AMD Ryzen 9 9950X3D")
    assert profile.category is ProductCategory.OTHER
    assert profile.module_type is ModuleType.UNKNOWN
    result = match_listing(
        profile,
        "Procesador AMD Ryzen 9 9950X3D 16 núcleos 32 hilos 4.3 GHz socket AM5",
    )
    assert result.status is MatchStatus.CONFIRMED

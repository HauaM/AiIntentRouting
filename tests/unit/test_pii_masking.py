from intent_routing.security.pii import mask_pii


def test_masks_korean_resident_registration_number() -> None:
    assert mask_pii("주민번호 900101-1234567 확인") == "주민번호 900101-1****** 확인"


def test_masks_business_registration_number() -> None:
    assert mask_pii("사업자번호 123-45-67890") == "사업자번호 123-45-*****"


def test_masks_mobile_phone_number() -> None:
    assert mask_pii("전화 010-1234-5678") == "전화 010-****-5678"

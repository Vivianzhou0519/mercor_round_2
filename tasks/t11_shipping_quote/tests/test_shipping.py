from shipping import quote


def test_light_parcel_short_leg():
    assert quote(0.8, 120) == 4.59


def test_band_boundary_at_one_kilo():
    assert quote(1.0, 0) == 4.50


def test_middle_band_with_multiplier():
    assert quote(2.5, 450) == 7.83


def test_heavy_band_is_flat():
    assert quote(12.5, 0) == 12.00


def test_over_twenty_kilos_charges_part_kilos():
    assert quote(22.4, 150) == 14.08


def test_long_haul_surcharge_applies_past_a_thousand():
    assert quote(22.4, 1500) == 23.94


def test_exactly_a_thousand_is_not_long_haul():
    assert quote(5.0, 1000) == 8.70

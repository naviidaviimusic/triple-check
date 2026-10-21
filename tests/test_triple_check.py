from triple_check.domains import tequila


def cell(answers=None):
    answers = answers or {}

    def fake_ask(prompt, model, system=None, max_tokens=500):
        for key, text in answers.items():
            if key in (system or "") or key == model:
                return text
        return ""
    return tequila.make_cell(ask=fake_ask)


def test_confirms_correct_numbers():
    rep = cell().facts.check_text(
        "A mature plant gives about 8 bottles per plant; Patron sells roughly 3 million cases a year.")
    status = {v["key"]: v["status"] for v in rep["verdicts"]}
    assert status == {"bottles_per_plant": "CONFIRMED", "brand_patron_cases": "CONFIRMED"}
    assert rep["numeric_accuracy"] == 1.0


def test_catches_bad_arithmetic():
    # a real local-model mistake this protocol caught: 14 kg of agave per liter
    rep = cell().facts.check_text("It takes 14 kg per liter of tequila.")
    assert rep["counts"]["DISPUTED"] == 1
    assert rep["disputed"][0]["key"] == "agave_kg_per_liter"


def test_magnitude_guard_and_units():
    # "8 bottles" must not be checked against Patron's 3,000,000 cases,
    # and "750 ml" is a size, not a count
    rep = cell().facts.check_text("Patron bottles 8 of them in a 750 ml bottle.")
    assert all(v["key"] != "brand_patron_cases" for v in rep["verdicts"])


def test_scale_words():
    rep = cell().facts.check_text("Casamigos ships 4 million cases.")
    assert rep["verdicts"][0]["claimed"] == 4_000_000


def test_close_band():
    assert cell().facts.cross_check("maturity_years", 9)["status"] == "CLOSE"     # outside 6-8, within 30%
    assert cell().facts.cross_check("maturity_years", 20)["status"] == "DISPUTED"
    assert cell().facts.cross_check("terroir", 5)["status"] == "NO_ANCHOR"


def test_supply_chain_math():
    sc = tequila.supply_chain(4_000_000)
    assert sc["liters_per_year"] == 36_000_000
    assert sc["bottles_per_year"] == 48_000_000
    assert sc["agave_tonnes_per_year"] == 252_000
    assert sc["standing_acres_in_production"] == 35_000
    assert tequila.supply_chain(4_000_000, density_per_acre=2000)["standing_acres_in_production"] == 21_000


def test_calculator_triggers():
    assert "36,000,000 L" in tequila.supply_calculator("How many acres to match Casamigos?")
    assert "VERIFIED" in tequila.supply_calculator("how much land to produce 2 million cases")
    assert tequila.supply_calculator("what does reposado mean?") == ""


def test_routing():
    c = cell()
    assert c.route("best soil and harvest timing for agave plants") == "farming"
    assert c.route("Casamigos brand sales and margin") == "business"


def test_full_protocol_flags_dispute_and_lowers_confidence():
    c = cell({"agronomist": "Plants take 7 years and give 8 bottles per plant.",
              "industry analyst": "Casamigos sells 4 million cases; it takes 14 kg per liter.",
              "llama3.2": "One figure is off."})
    r = c.triple_check("How many acres to match Casamigos volume?")
    assert r["verified_calculation"] and r["lead_answer"].startswith("[Casamigos")
    assert r["n_disputed"] == 1
    assert r["confidence"] != "HIGH"
    assert r["verification"]["business"]["independent_note"] == "One figure is off."


def test_all_confirmed_is_high():
    c = cell({"agronomist": "Agave matures in 7 years.",
              "industry analyst": "Patron sells 3 million cases."})
    r = c.triple_check("tell me about agave")
    assert (r["confidence"], r["n_disputed"]) == ("HIGH", 0)


def test_sizes_skipped_rates_checked():
    f = cell().facts
    assert f.check_text("we ship 5,000 acres worth, 750 ml bottles")["n_claims"] == 0
    assert f.check_text("about 7 kg/l of agave")["verdicts"][0]["status"] == "CONFIRMED"

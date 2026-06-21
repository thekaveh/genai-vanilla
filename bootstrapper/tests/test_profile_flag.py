import start


def test_cli_declares_profile():
    names = [p.name for p in start.main.params]
    assert "profile" in names


def test_profile_choices():
    opt = next(p for p in start.main.params if p.name == "profile")
    assert set(opt.type.choices) == {"default", "prod"}

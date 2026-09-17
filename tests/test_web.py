from ncaa_rankings.web.utils import slugify, subdivision


def test_slugify_handles_punctuation_and_apostrophes():
    assert slugify("Hawai'i") == "hawai-i"
    assert slugify("Miami (OH)") == "miami-oh"


def test_subdivision_normalization():
    assert subdivision("fbs") == "FBS"
    assert subdivision("FCS") == "FCS"
    assert subdivision("ii") == "II"

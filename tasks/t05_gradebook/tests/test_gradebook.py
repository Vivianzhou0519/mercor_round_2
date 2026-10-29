from gradebook import summary


def test_summary():
    scores = [88, 92, 41, 60, 75, 58]
    assert summary(scores) == {
        "mean": 69.0,
        "median": 67.5,
        "highest": 92,
        "lowest": 41,
        "passing": 4,
    }

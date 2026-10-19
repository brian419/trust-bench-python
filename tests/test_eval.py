from eval import compare_answers
from eval import calculate_accuracy

def test_identical_answers():
    assert compare_answers("Paris", "Paris")

def test_wrong_answers():
    assert not compare_answers("Paris", "London")

def test_case_insensitive():
    assert compare_answers("Paris", "PARIS")

def test_whitespace_normalization():
    assert compare_answers("Tokyo", " Tokyo ")


# calculate_accuracy

def test_all_passed():
    assert round(calculate_accuracy(3,0),2) == 100.00

def test_all_failed():
    assert round(calculate_accuracy(0,3),2) == 0.00

def test_half_passed():
    assert round(calculate_accuracy(1,1),2) == 50.00

def test_mixed_result():
    assert round(calculate_accuracy(2,1),2) == 66.67

def test_no_tests():
    assert calculate_accuracy(0,0) is None
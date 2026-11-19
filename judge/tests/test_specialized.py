from judge.specialized import extract_result, structured_match


def test_extracts_structured_result_after_user_output():
    assert extract_result("debug\n__EKLAVYA_RESULT__{\"rows\":[[1]]}\n") == {"rows": [[1]]}


def test_structured_tolerance_is_recursive():
    assert structured_match([[-1.000000001, 1]], [[-1, 1.0]], 1e-8)
    assert not structured_match([[1.1]], [[1.0]], 1e-8)

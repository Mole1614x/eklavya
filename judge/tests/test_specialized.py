from judge.specialized import evaluate_answer, extract_result, structured_match


def test_extracts_structured_result_after_user_output():
    assert extract_result("debug\n__EKLAVYA_RESULT__{\"rows\":[[1]]}\n") == {"rows": [[1]]}


def test_structured_tolerance_is_recursive():
    assert structured_match([[-1.000000001, 1]], [[-1, 1.0]], 1e-8)
    assert not structured_match([[1.1]], [[1.0]], 1e-8)


def test_numerical_and_multiple_choice_answers_are_typed():
    assert extract_result(evaluate_answer("numerical", "4.0000001").output) == 4.0000001
    assert extract_result(evaluate_answer("multiple_choice", "P(A) × P(B)").output) == "P(A) × P(B)"
    assert evaluate_answer("numerical", "four").verdict == "WRONG_ANSWER"

from pathlib import Path

from judge.specialized import RUNNERS


def test_ai_runner_validates_tensor_contracts_and_argument_types():
    source = (Path(RUNNERS) / "ai_runner.py").read_text()
    assert 'torch.tensor(value, dtype=torch.float32, requires_grad=True)' in source
    assert "result.shape != arguments[0].shape" in source
    assert "np.asarray(value)" in source

from src.retry import with_retry


def test_retry_eventually_succeeds():
    state = {"count": 0}

    def flaky():
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    out, errors = with_retry(flaky, retries=2, base_delay=0.0)
    assert out == "ok"
    assert len(errors) == 2


def test_retry_returns_none_after_exhaustion():
    def always_fail():
        raise RuntimeError("hard-fail")

    out, errors = with_retry(always_fail, retries=1, base_delay=0.0)
    assert out is None
    assert len(errors) == 2

"""CLI argument-range validation for start.py worker-count flags.

``--spark-workers`` (1-8) and ``--ray-worker-count`` (0-64) mirror the
wizard's SecondaryNumberInput clamps. An out-of-range value must exit with
click's conventional usage-error code 2 — not the masked "unexpected error"
exit 1 the catch-all handler used to produce before main() learned to
re-raise click.ClickException ahead of the generic handler.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from start import main


@pytest.mark.parametrize("value", ["0", "9", "-1", "99"])
def test_spark_workers_out_of_range_exits_2(value):
    result = CliRunner().invoke(main, ["--spark-workers", value])
    assert result.exit_code == 2
    assert "spark-workers must be in 1-8" in result.output


@pytest.mark.parametrize("value", ["-1", "65", "99"])
def test_ray_worker_count_out_of_range_exits_2(value):
    result = CliRunner().invoke(main, ["--ray-worker-count", value])
    assert result.exit_code == 2
    assert "ray-worker-count must be in 0-64" in result.output

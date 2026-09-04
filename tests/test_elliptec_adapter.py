from qozy.hardware.base import PositionerAdapter
from qozy.hardware.elliptec_adapter import ElliptecAdapter
from qozy.hardware.simulator import SimulatorStage


def test_construct_does_not_require_elliptec_installed() -> None:
    # elliptec is imported lazily inside connect(), so just building the
    # adapter must never require the vendor package or a serial port.
    adapter = ElliptecAdapter(port="/dev/ttyUSB0", address="0")
    assert adapter.port == "/dev/ttyUSB0"


def test_simulator_stage_matches_positioner_adapter_shape() -> None:
    stage = SimulatorStage()
    assert isinstance(stage, PositionerAdapter)
    stage.connect()
    stage.home()
    assert stage.get_angle() == 0.0
    assert stage.set_angle(45.0) == 45.0
    assert stage.get_angle() == 45.0

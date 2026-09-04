from __future__ import annotations

import sys
import types

import pytest

from qozy.hardware.manager import HardwareManager
from qozy.hardware.timetagger_adapter import TimeTaggerAdapter
from qozy.hardware.timetagger_network import NetworkTimeTagger


def test_network_backend_requires_address() -> None:
    with pytest.raises(ValueError, match="server address"):
        NetworkTimeTagger("")


def test_hardware_manager_starts_with_connected_simulator() -> None:
    manager = HardwareManager()
    assert manager.backend == "simulator"
    assert manager.connected

    manager.disconnect()
    assert not manager.connected


def test_network_adapter_uses_network_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []

    class FakeTagger:
        pass

    fake_tagger = FakeTagger()
    fake_module = types.SimpleNamespace(
        createTimeTaggerNetwork=lambda addresses: (
            calls.append(("network", addresses)) or fake_tagger
        ),
        freeTimeTagger=lambda tagger: calls.append(("free", tagger)),
    )
    monkeypatch.setitem(sys.modules, "TimeTagger", fake_module)

    adapter = TimeTaggerAdapter("tagger.example:41101")
    adapter.connect()
    adapter.disconnect()

    assert calls == [
        ("network", ["tagger.example:41101"]),
        ("free", fake_tagger),
    ]


def test_hardware_manager_has_connected_simulator_stages() -> None:
    manager = HardwareManager()
    assert manager.stage_connected == {"alice": True, "bob": True}
    assert manager.stage_angle("alice") == 0.0
    assert manager.stage_angle("bob") == 0.0

    assert manager.move_stage("alice", 22.5) == 22.5
    assert manager.stage_angle("alice") == 22.5

    assert manager.home_stage("alice") == 0.0


def test_hardware_manager_rejects_stage_reconfiguration_while_connected() -> None:
    manager = HardwareManager()
    with pytest.raises(RuntimeError, match="Disconnect the Alice"):
        manager.select_stage("alice", "elliptec", "/dev/ttyUSB0", "0")

    manager.disconnect_stage("alice")
    manager.select_stage("alice", "elliptec", "/dev/ttyUSB0", "0")
    assert manager.stage_backends["alice"] == "elliptec"
    assert manager.stage_ports["alice"] == "/dev/ttyUSB0"
    assert manager.stage_addresses["alice"] == "0"

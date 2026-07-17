from pathlib import Path
import shutil

from engine.application import generate_report

from tests.test_builder import (
    FIXTURES,
    _write_combined_config_entries,
    _write_combined_entity_registry,
)


def _create_config_dir(config_dir: Path) -> None:
    storage = config_dir / ".storage"
    storage.mkdir(parents=True)
    _write_combined_entity_registry(storage / "core.entity_registry")
    _write_combined_config_entries(storage / "core.config_entries")
    shutil.copyfile(
        FIXTURES / "core.device_registry.sample",
        storage / "core.device_registry",
    )
    shutil.copyfile(
        FIXTURES / "automations.sample.yaml",
        config_dir / "automations.yaml",
    )
    shutil.copyfile(
        FIXTURES / "scripts.sample.yaml",
        config_dir / "scripts.yaml",
    )


def test_generate_report_end_to_end(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _create_config_dir(config_dir)

    private_dir = tmp_path / "private"
    public_dir = tmp_path / "public"
    result = generate_report(
        config_dir=config_dir,
        entity_id="sensor.pulse_elpris",
        private_output_dir=private_dir,
        public_output_dir=public_dir,
        language="sv-SE",
    )

    assert result.summary.startswith("sensor.pulse_elpris:")
    assert "Direkta barn" in result.report_text
    assert result.private_file.exists()
    assert result.private_debug_file.exists()
    assert result.private_latest_file.exists()
    assert result.public_url == (
        "/local/entity_dependency_engine/sensor_pulse_elpris.txt"
    )
    assert (public_dir / "sensor_pulse_elpris.txt").exists()
    assert "Entity Dependency Report" in result.debug_text

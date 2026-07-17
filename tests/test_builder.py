from pathlib import Path
import json

from engine.builder import BuildPaths, GraphBuilder


FIXTURES = Path(__file__).parent / "fixtures"


def _write_combined_entity_registry(target: Path) -> None:
    payload = json.loads(
        (FIXTURES / "core.entity_registry.sample").read_text(
            encoding="utf-8"
        )
    )

    payload["data"]["entities"].extend(
        [
            {
                "entity_id": "binary_sensor.elpris_under_medel",
                "id": "template_entity_1",
                "unique_id": "template-1",
                "platform": "template",
                "config_entry_id": "template_entry_1",
                "device_id": None,
                "name": "Elpris under medel",
                "original_name": "Elpris under medel",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "sensor.kost_el_kop",
                "id": "template_entity_2",
                "unique_id": "template-2",
                "platform": "template",
                "config_entry_id": "template_entry_2",
                "device_id": None,
                "name": "Kost el köp",
                "original_name": "Kost el köp",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "input_number.elskatt_kop",
                "id": "helper_1",
                "unique_id": "helper-1",
                "platform": "input_number",
                "config_entry_id": None,
                "device_id": None,
                "name": "Elskatt köp",
                "original_name": "Elskatt köp",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "automation.test_automation",
                "id": "automation_entity_1",
                "unique_id": "1001",
                "platform": "automation",
                "config_entry_id": None,
                "device_id": None,
                "name": "Test automation",
                "original_name": "Test automation",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "binary_sensor.motion",
                "id": "motion_1",
                "unique_id": "motion-1",
                "platform": "test",
                "config_entry_id": None,
                "device_id": None,
                "name": "Motion",
                "original_name": "Motion",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "light.test",
                "id": "light_1",
                "unique_id": "light-1",
                "platform": "test",
                "config_entry_id": None,
                "device_id": None,
                "name": "Test light",
                "original_name": "Test light",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "script.test_script",
                "id": "script_entity_1",
                "unique_id": "script-test-script",
                "platform": "script",
                "config_entry_id": None,
                "device_id": None,
                "name": "Test script",
                "original_name": "Test script",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "script.child_script",
                "id": "script_entity_2",
                "unique_id": "script-child-script",
                "platform": "script",
                "config_entry_id": None,
                "device_id": None,
                "name": "Child script",
                "original_name": "Child script",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "input_number.brightness",
                "id": "helper_brightness",
                "unique_id": "helper-brightness",
                "platform": "input_number",
                "config_entry_id": None,
                "device_id": None,
                "name": "Brightness",
                "original_name": "Brightness",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "input_boolean.enable_extra",
                "id": "helper_enable_extra",
                "unique_id": "helper-enable-extra",
                "platform": "input_boolean",
                "config_entry_id": None,
                "device_id": None,
                "name": "Enable extra",
                "original_name": "Enable extra",
                "labels": [],
                "aliases": []
            },
            {
                "entity_id": "switch.extra",
                "id": "switch_extra",
                "unique_id": "switch-extra",
                "platform": "test",
                "config_entry_id": None,
                "device_id": None,
                "name": "Extra switch",
                "original_name": "Extra switch",
                "labels": [],
                "aliases": []
            }
        ]
    )

    target.write_text(json.dumps(payload), encoding="utf-8")


def _write_combined_config_entries(target: Path) -> None:
    entries = []

    for filename in (
        "core.config_entries.sample",
        "core.config_entries.templates.sample",
        "core.config_entries.utility_meter.sample",
        "core.config_entries.derivative.sample",
        "core.config_entries.min_max.sample",
        "core.config_entries.history_stats.sample",
        "core.config_entries.integration.sample",
        "core.config_entries.threshold.sample",
    ):
        payload = json.loads(
            (FIXTURES / filename).read_text(encoding="utf-8")
        )
        entries.extend(payload["data"]["entries"])

    target.write_text(
        json.dumps(
            {
                "version": 1,
                "minor_version": 1,
                "key": "core.config_entries",
                "data": {"entries": entries},
            }
        ),
        encoding="utf-8",
    )


def _builder(tmp_path: Path) -> GraphBuilder:
    entity_registry = tmp_path / "core.entity_registry"
    device_registry = tmp_path / "core.device_registry"
    config_entries = tmp_path / "core.config_entries"
    automations = tmp_path / "automations.yaml"
    scripts = tmp_path / "scripts.yaml"

    _write_combined_entity_registry(entity_registry)

    device_registry.write_text(
        (FIXTURES / "core.device_registry.sample").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    _write_combined_config_entries(config_entries)

    automations.write_text(
        (FIXTURES / "automations.sample.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    scripts.write_text(
        (FIXTURES / "scripts.sample.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    return GraphBuilder(
        BuildPaths(
            entity_registry=entity_registry,
            device_registry=device_registry,
            config_entries=config_entries,
            automations=automations,
            scripts=scripts,
        )
    )


def test_builder_returns_complete_result(tmp_path: Path) -> None:
    result = _builder(tmp_path).build()

    assert result.graph.node_count >= 16
    assert result.graph.edge_count >= 12
    assert result.statistics.total_nodes == result.graph.node_count
    assert result.statistics.total_edges == result.graph.edge_count


def test_builder_creates_structural_relations(tmp_path: Path) -> None:
    result = _builder(tmp_path).build()
    graph = result.graph

    assert "device:device_sun" in graph.children(
        "sensor.sun_next_dawn"
    )
    assert "config_entry:entry_sun" in graph.children(
        "sensor.sun_next_dawn"
    )


def test_builder_creates_functional_relations(tmp_path: Path) -> None:
    result = _builder(tmp_path).build()
    graph = result.graph

    assert "binary_sensor.elpris_under_medel" in graph.children(
        "sensor.pulse_elpris"
    )
    assert "automation.test_automation" in graph.children(
        "binary_sensor.motion"
    )
    assert "light.test" in graph.children(
        "automation.test_automation"
    )
    assert "script.test_script" in graph.children(
        "input_number.brightness"
    )
    assert "light.test" in graph.children(
        "script.test_script"
    )
    assert "script.child_script" in graph.children(
        "script.test_script"
    )


def test_builder_tracks_parser_statistics(tmp_path: Path) -> None:
    result = _builder(tmp_path).build()

    assert result.statistics.parser_nodes["entity_registry"] == 13
    assert result.statistics.parser_nodes["device_registry"] == 2
    assert result.statistics.parser_edges["gui_templates"] >= 1
    assert result.statistics.parser_edges["automations"] >= 2
    assert result.statistics.parser_edges["scripts"] >= 3

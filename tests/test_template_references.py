from engine.parsers.template_references import (
    extract_template_references,
)


def test_extract_recognized_function_references() -> None:
    refs = extract_template_references(
        "{{ states('sensor.a') }} "
        "{{ state_attr(\"sensor.b\", 'x') }} "
        "{{ is_state('binary_sensor.c', 'on') }} "
        "{{ expand('group.d') }}"
    )

    assert refs.certain == frozenset(
        {"sensor.a", "sensor.b", "binary_sensor.c", "group.d"}
    )


def test_extract_direct_states_reference() -> None:
    refs = extract_template_references(
        "{{ states.sensor.pulse_elpris.state }}"
    )

    assert refs.certain == frozenset({"sensor.pulse_elpris"})
    assert refs.probable == frozenset()


def test_plain_reference_is_probable() -> None:
    refs = extract_template_references(
        "{{ some_macro('sensor.hidden_reference') }}"
    )

    assert refs.certain == frozenset()
    assert refs.probable == frozenset({"sensor.hidden_reference"})


def test_long_dotted_expression_does_not_create_fragments() -> None:
    refs = extract_template_references(
        "{{ states.sensor.pulse_elpris.attributes.avg_price }}"
    )

    assert refs.certain == frozenset({"sensor.pulse_elpris"})
    assert refs.probable == frozenset()

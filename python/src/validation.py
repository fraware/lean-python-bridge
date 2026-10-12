import jsonschema

matrix_model_schema_v1 = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "integer"},
        "matrix": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "integer"}},
        },
        "model": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "version": {"type": "string"}},
            "required": ["name", "version"],
        },
    },
    "required": ["schema_version", "matrix", "model"],
}

matrix_model_schema_v2 = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "integer"},
        "matrix": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "integer"}},
        },
        "model": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "author": {"type": "string"},
            },
            "required": ["name", "version"],
        },
    },
    "required": ["schema_version", "matrix", "model"],
}


def validate_matrix_model(payload: dict) -> None:
    version = payload.get("schema_version", 1)
    if version == 1:
        jsonschema.validate(instance=payload, schema=matrix_model_schema_v1)
    elif version == 2:
        jsonschema.validate(instance=payload, schema=matrix_model_schema_v2)
    else:
        raise ValueError(f"Unsupported schema version: {version}")


def load_schemas() -> dict[str, dict]:
    """Return the supported, versioned matrix-model JSON schemas."""
    return {"v1": matrix_model_schema_v1, "v2": matrix_model_schema_v2}

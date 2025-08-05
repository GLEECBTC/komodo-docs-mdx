from typing import Dict, Any, List, TypedDict, Optional

class EnhancedJSONSchema(TypedDict, total=False):
    """
    A TypedDict for our enhanced JSON schema properties, allowing for more specific type checking.
    """
    type: str
    description: str
    default: Any
    ref: str
    items: Dict[str, Any]

def openapi_property(
    type: str = "object",
    description: Optional[str] = None,
    default: Optional[Any] = None,
    ref: Optional[str] = None,
    example: Optional[Any] = None,
    enum: Optional[List[str]] = None
) -> EnhancedJSONSchema:
    """
    Creates a standard OpenAPI property dictionary with optional fields.
    """
    prop: EnhancedJSONSchema = {'type': type}
    if description:
        prop['description'] = description
    if default is not None:
        prop['default'] = default
    if ref:
        prop['$ref'] = ref
        # OpenAPI spec says if $ref is present, other properties are ignored.
        # So we can remove the type if a ref is present.
        if 'type' in prop:
            del prop['type']
    if example:
        prop['example'] = example
    if enum:
        prop['enum'] = enum
    return prop

def openapi_schema(
    properties: Dict[str, EnhancedJSONSchema],
    required_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Creates a standard OpenAPI schema dictionary for an object.
    """
    schema = {
        'type': 'object',
        'properties': properties
    }
    if required_fields:
        schema['required'] = required_fields
    return schema 
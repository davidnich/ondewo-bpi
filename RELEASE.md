# Release History
*****************
## Release ONDEWO BPI v3.0.0
### Improvements
* Support of patterns to invoke intent callbacks

### Breaking Changes
This version holds small renaming and typing changes on the BPI Server:
  * `self.intent_handlers` is now a `List[IntentCallbackAssignor]` instead of a dictionary; custom code in the `register_handlers` function will need adaptation. 
  * The `intent_name` field of the `registered handlers` now supports patterns, therefore its name changed to `intent_pattern`.
  * The `handler` field of the `registered handlers` now contains a list of callables, therefore was renamed to `handlers`.

Below an example of how it should look after the update:

```python
    def register_handlers(self) -> None:
        self.register_intent_handler(
            intent_pattern=r"i.my_\.*", handlers=[self.reformat_text_in_intent],
        )
        self.register_intent_handler(
            intent_pattern="i.my_handled_intent", handlers=[self.reformat_text_in_intent],
        )
```

*****************
## Release ONDEWO BPI v2.0.4
### New Features
* Support NLU API 2.0.x

### Improvements
* Support streaming connections

*****************
## Release ONDEWO BPI v2.0.3
### New Features

* upload to pypi

*****************
## Release ONDEWO BPI v2.0.2
### Bug Fixes

* imrpoved log output for debugging
* updated to use ondewo-logging pip repo

*****************
## Release ONDEWO BPI v2.0.1
### Bug Fixes

* updated README
* updated sip example import path

*****************

## Release ONDEWO BPI v2.0.0
### New Features

* refactored
* updated all submodules and clients
* moved to github

### Improvements

* added examples, refactored the servers so they are consistent and more clear

### Breaking Changes

* the code for generating contexts has changed:
* * this version (currently compatible with the develop version of CAI):
```python
def create_parameter_dict(my_dict: Dict) -> Optional[Dict[str, context_pb2.Context.Parameter]]:
    assert isinstance(my_dict, dict) or my_dict is None, "parameter must be a dict or None"
    if my_dict is not None:
        return {
            key: context_pb2.Context.Parameter(
                display_name=key,
                value=my_dict[key]
            )
            for key in my_dict
        }
    return None
```
* * old version (compatible with the current production CAI):
```python
from google.protobuf.struct_pb2 import Struct

def get_protobuf_struct_from_dict(my_dict: Dict) -> Struct:
    assert isinstance(my_dict, dict) or my_dict is None, "parameter must be a dict or None"
    result: Struct = Struct()
    if my_dict is not None:
        for key, value in my_dict.items():
            result[key] = value
    return result
```

### Known issues not covered in this release

* sip-client-python not open source, therefore it needs to be added seperately for external customers to use it

### Migration Guide

* change your upstreams to github

*****************
## Release ONDEWO RELEASE Template
### New Features
### Improvements
### Bug fixes
### Breaking Changes
### Known issues not covered in this release
### Migration Guide

*****************

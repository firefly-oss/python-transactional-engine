"""
Fireflytx decorators for SAGA and TCC patterns.
"""

from .saga import (
    compensation_step,
    from_step,
    get_saga_config,
    get_saga_name,
    get_step_config,
    header_param,
    input_param,
    is_compensation_step,
    is_saga_class,
    is_saga_step,
    saga,
    saga_step,
    step_events,
    variable_param,
)
from .tcc import (
    cancel_method,
    confirm_method,
    from_try,
    get_participant_config,
    get_tcc_config,
    get_tcc_method_config,
    get_tcc_name,
    is_cancel_method,
    is_confirm_method,
    is_tcc_class,
    is_tcc_participant,
    is_try_method,
    tcc,
    tcc_header,
    tcc_input,
    tcc_participant,
    try_method,
)

__all__ = [
    # SAGA decorators
    "saga",
    "saga_step",
    "compensation_step",
    "step_events",
    "input_param",
    "header_param",
    "from_step",
    "variable_param",
    "get_saga_config",
    "get_saga_name",
    "get_step_config",
    "is_saga_class",
    "is_saga_step",
    "is_compensation_step",
    # TCC decorators
    "tcc",
    "tcc_participant",
    "try_method",
    "confirm_method",
    "cancel_method",
    "from_try",
    "tcc_input",
    "tcc_header",
    "get_tcc_config",
    "get_tcc_name",
    "get_participant_config",
    "get_tcc_method_config",
    "is_tcc_class",
    "is_tcc_participant",
    "is_try_method",
    "is_confirm_method",
    "is_cancel_method",
]

"""
Copyright (c) 2025 Firefly Software Solutions Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

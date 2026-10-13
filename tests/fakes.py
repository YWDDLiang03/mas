"""Deterministic fake providers for tests; no network."""

from mas.core.broker import ProviderResponse, ToolAbsent, ToolContract, ToolError


class FakeIdentity:
    contract = ToolContract(
        tool_id="tool_fake_identity", capability="identity_resolution", capability_kind="entity_resolution",
        question_kinds=("resolve_name",), contract_version="1", implementation_version="fake-1",
        purpose_statement="test identity", evidence_kind_produced="database_entry", claim_strength_ceiling="curated",
        required_inputs=("name",))

    def __init__(self, table):
        self.table = table  # name -> list of identity hits

    def invoke(self, question_kind, inputs):
        hits = self.table.get(inputs["name"], [])
        return ProviderResponse(values=[{"name": "identity", "value": h, "value_kind": "curated"} for h in hits],
                                data_version="fake")


class FakeProperty:
    contract = ToolContract(
        tool_id="tool_fake_property", capability="property_estimate", capability_kind="attribute_estimate",
        question_kinds=("computed_property",), contract_version="1", implementation_version="fake-1",
        purpose_statement="test property", evidence_kind_produced="database_entry", claim_strength_ceiling="curated",
        identity_inputs=("identifier",))

    def __init__(self, table, failures=None):
        self.table = table          # (identifier, property) -> value
        self.failures = failures or {}  # identifier -> list of error classes to raise first
        self.calls = 0

    def invoke(self, question_kind, inputs):
        self.calls += 1
        queue = self.failures.get(inputs["identifier"])
        if queue:
            raise ToolError(queue.pop(0), "scripted failure")
        key = (inputs["identifier"], inputs["property"])
        if key not in self.table:
            return ProviderResponse(values=[], data_version="fake")
        return ProviderResponse(
            values=[{"name": inputs["property"], "value": self.table[key], "unit": "g/mol", "value_kind": "derived",
                     "source_record_ref": f"fake:{inputs['identifier']}"}],
            records=[{"record_id": f"fake:{inputs['identifier']}", "field": inputs["property"], "value": self.table[key]}],
            data_version="fake", upstream_refs=[f"fake:{inputs['identifier']}"])


class AbsentProvider:
    contract = ToolContract(
        tool_id="tool_fake_absent", capability="interaction_estimate", capability_kind="relationship_estimate",
        question_kinds=("estimate",), contract_version="1", implementation_version="fake-1",
        purpose_statement="never installed", evidence_kind_produced="model_prediction", claim_strength_ceiling="predicted")

    def invoke(self, question_kind, inputs):
        raise ToolAbsent("not_installed", "no checkpoint")

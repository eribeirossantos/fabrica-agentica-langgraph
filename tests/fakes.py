"""Modelos de teste que estragam um passo do stub de propósito."""

from __future__ import annotations

from fabrica.schemas import DesignSpec, DevPlan
from fabrica.stub import StubModel


class ScriptedModel:
    """Encadeia o stub e deixa o teste quebrar design ou dev."""

    def __init__(self, *, break_design_once: bool = False, always_bad_dev: bool = False) -> None:
        self.inner = StubModel()
        self.break_design_once = break_design_once
        self.always_bad_dev = always_bad_dev
        self.design_calls = 0
        self.dev_calls = 0
        self.calls: list[str] = []

    def invoke(self, schema: type, system: str, user: str):
        self.calls.append(schema.__name__)
        result = self.inner.invoke(schema, system, user)
        if schema is DesignSpec:
            self.design_calls += 1
            if self.break_design_once and self.design_calls == 1:
                data = result.model_dump()
                data["accessibility"] = ["Contraste ainda não medido."]
                return DesignSpec.model_validate(data)
        if schema is DevPlan:
            self.dev_calls += 1
            if self.always_bad_dev:
                return DevPlan(
                    files_and_areas=["app/checkout/PayButton.tsx"],
                    test_plan=[],
                    pr_evidence=["log do CI"],
                    notes="incompleto de propósito",
                )
        return result

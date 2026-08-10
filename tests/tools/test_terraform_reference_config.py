"""The plan resource count degrades to a fixed number if the reference config is gone."""

from pathlib import Path

import pytest

from devops_learn.tools import terraform_tool
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.service import ToolService
from devops_learn.tools.terraform_tool import SimulatedTerraformTool


def test_plan_falls_back_when_the_reference_config_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        terraform_tool, "_reference_config_path", lambda: tmp_path / "main.tf.reference"
    )
    service = ToolService({"terraform": SimulatedTerraformTool()}, AutoApproveApprovalGate())

    result = service.invoke("terraform", "plan")

    assert result.details["create"] == terraform_tool._FALLBACK_RESOURCE_COUNT


def test_plan_counts_only_resource_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = tmp_path / "main.tf.reference"
    config.write_text(
        'variable "location" {}\n'
        'resource "azurerm_resource_group" "rg" {}\n'
        '# resource "azurerm_container_registry" "commented" {}\n'
        'resource "azurerm_container_app" "app" {}\n'
        'data "azurerm_client_config" "current" {}\n'
    )
    monkeypatch.setattr(terraform_tool, "_reference_config_path", lambda: config)
    service = ToolService({"terraform": SimulatedTerraformTool()}, AutoApproveApprovalGate())

    result = service.invoke("terraform", "plan")

    assert result.details["create"] == 2

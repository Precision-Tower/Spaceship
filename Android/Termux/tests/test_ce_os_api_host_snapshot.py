#!/usr/bin/env python3
import importlib.machinery
import importlib.util
from pathlib import Path

API_PATH = Path(__file__).parents[1] / "bin" / "ce-os-api"
loader = importlib.machinery.SourceFileLoader("ce_os_api_host", str(API_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
api = importlib.util.module_from_spec(spec)
loader.exec_module(api)


def healthy():
    return {
        "services": {
            "api": "ok",
            "live_sync": "ok",
            "guardian": "ok",
            "privileged_broker": "ok",
        },
        "network": {
            "hotspot_interface": "up",
            "ssh_listener": "listening",
            "ssh_firewall_rule": "present",
        },
        "security": {
            "selinux": "enforcing",
            "root_available": True,
            "verified_boot": "green",
            "bootloader": "locked",
        },
        "lifecycle": {
            "termux_suspended": "false",
            "magisk_suspended": "false",
        },
        "storage": {"data_percent": "22"},
    }


def test_healthy_snapshot_has_no_warnings():
    result = api.classify_host_snapshot(healthy())
    assert result["overall"] == "healthy"
    assert result["warnings"] == []
    assert result["read_only"] is True


def test_unlocked_development_boot_chain_is_attention_not_connectivity_failure():
    observed = healthy()
    observed["security"]["verified_boot"] = "orange"
    observed["security"]["bootloader"] = "unlocked"
    result = api.classify_host_snapshot(observed)
    assert result["overall"] == "attention"
    assert "verified_boot_orange" in result["warnings"]
    assert "bootloader_unlocked" in result["warnings"]


def test_network_or_service_loss_is_degraded():
    observed = healthy()
    observed["network"]["hotspot_interface"] = "absent"
    observed["services"]["guardian"] = "degraded"
    result = api.classify_host_snapshot(observed)
    assert result["overall"] == "degraded"
    assert "hotspot_absent" in result["warnings"]
    assert "service_guardian_degraded" in result["warnings"]


def test_lifecycle_suspension_is_degraded():
    observed = healthy()
    observed["lifecycle"]["termux_suspended"] = "true"
    result = api.classify_host_snapshot(observed)
    assert result["overall"] == "degraded"
    assert "termux_suspended" in result["warnings"]


def test_storage_pressure_is_attention():
    observed = healthy()
    observed["storage"]["data_percent"] = "94"
    result = api.classify_host_snapshot(observed)
    assert result["overall"] == "attention"
    assert "storage_pressure" in result["warnings"]

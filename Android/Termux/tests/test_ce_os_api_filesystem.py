#!/usr/bin/env python3
import importlib.machinery
import importlib.util
from pathlib import Path

API_PATH = Path(__file__).parents[1] / "bin" / "ce-os-api"
loader = importlib.machinery.SourceFileLoader("ce_os_api", str(API_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
api = importlib.util.module_from_spec(spec)
loader.exec_module(api)


def configured_root(tmp_path: Path) -> None:
    api.ROOT = tmp_path.resolve()


def test_root_and_nested_listing_are_sorted_and_virtualized(tmp_path: Path) -> None:
    configured_root(tmp_path)
    (tmp_path / "z-file.txt").write_text("z", encoding="utf-8")
    (tmp_path / "A-dir").mkdir()
    (tmp_path / "b-dir").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "A-dir" / "nested.txt").write_text("nested", encoding="utf-8")
    result = api.list_repo_entries("/")
    assert [(e["name"], e["type"]) for e in result["entries"]] == [(".git", "directory"), ("A-dir", "directory"), ("b-dir", "directory"), ("z-file.txt", "file")]
    assert api.list_repo_entries("/A-dir")["entries"][0]["path"] == "/A-dir/nested.txt"


def test_text_read_and_virtual_path_normalization(tmp_path: Path) -> None:
    configured_root(tmp_path)
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    assert api.read_repo_file("./hello.txt") == {"ok": True, "path": "/hello.txt", "content": "hello", "size": 5}
    assert api.resolve_authorized_path("~") == tmp_path.resolve()
    assert api.resolve_authorized_path("~/hello.txt") == (tmp_path / "hello.txt").resolve()


def test_traversal_and_symlink_escape_are_rejected(tmp_path: Path) -> None:
    configured_root(tmp_path)
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "escape"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    for value in ("../outside.txt", "/../outside.txt", "/escape"):
        try:
            api.resolve_authorized_path(value)
        except ValueError:
            pass
        else:
            raise AssertionError(value)


def test_missing_and_wrong_kinds_return_structured_errors(tmp_path: Path) -> None:
    configured_root(tmp_path)
    (tmp_path / "folder").mkdir()
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")
    assert api.list_repo_entries("/missing")["error"] == "not_found"
    assert api.read_repo_file("/missing")["error"] == "not_found"
    assert api.read_repo_file("/folder")["error"] == "not_regular_file"
    assert api.list_repo_entries("/file.txt")["error"] == "not_directory"


def test_binary_read_is_rejected(tmp_path: Path) -> None:
    configured_root(tmp_path)
    (tmp_path / "binary.dat").write_bytes(b"\xff\x00\x01")
    result = api.read_repo_file("/binary.dat")
    assert result["ok"] is False
    assert result["error"] == "binary_not_supported"
    assert "content" not in result

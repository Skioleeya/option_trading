from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from pathlib import Path


REDIS_AOF_TOTAL_CAP_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class RedisPreflightResult:
    conf_path: Path
    configured_dir: str
    data_dir: Path
    resolved_dir: Path
    fs_type: str
    appendonly_enabled: bool
    appendfilename: str
    aof_base_bytes: int
    aof_incr_bytes: int
    aof_total_bytes: int
    aof_total_cap_bytes: int


def describe_redis_preflight(result: RedisPreflightResult) -> str:
    total = _format_gib(result.aof_total_bytes)
    cap = _format_gib(result.aof_total_cap_bytes)
    return (
        f"dir={result.data_dir} resolved={result.resolved_dir} fs={result.fs_type} "
        f"appendonly={result.appendonly_enabled} aof_total={total} cap={cap}"
    )


def preflight_redis_runtime(
    repo: Path,
    conf_path: Path,
    *,
    aof_total_cap_bytes: int = REDIS_AOF_TOTAL_CAP_BYTES,
) -> RedisPreflightResult:
    config = _parse_redis_config(conf_path)
    configured_dir = config.get("dir", "").strip()
    if not configured_dir:
        raise RuntimeError(f"Redis config missing 'dir': {conf_path}")

    data_dir = _resolve_repo_path(repo, configured_dir)
    resolved_dir = data_dir.resolve(strict=False)
    fs_probe_target = _nearest_existing_path(resolved_dir)
    fs_type = _filesystem_type(fs_probe_target)
    appendonly_enabled = config.get("appendonly", "no").strip().lower() == "yes"
    appendfilename = config.get("appendfilename", "appendonly.aof").strip().strip('"')
    base_bytes, incr_bytes = _aof_sizes(resolved_dir, appendonly_enabled, appendfilename)
    total_bytes = base_bytes + incr_bytes

    result = RedisPreflightResult(
        conf_path=conf_path,
        configured_dir=configured_dir,
        data_dir=data_dir,
        resolved_dir=resolved_dir,
        fs_type=fs_type,
        appendonly_enabled=appendonly_enabled,
        appendfilename=appendfilename,
        aof_base_bytes=base_bytes,
        aof_incr_bytes=incr_bytes,
        aof_total_bytes=total_bytes,
        aof_total_cap_bytes=aof_total_cap_bytes,
    )
    _enforce_redis_owner_contract(result)
    return result


def _enforce_redis_owner_contract(result: RedisPreflightResult) -> None:
    if os.name != "nt":
        raise RuntimeError(
            "Redis data dir contract is Windows-only in this repository. "
            f"resolved_dir={result.resolved_dir} fs={result.fs_type}"
        )

    resolved_text = str(result.resolved_dir)
    if resolved_text.startswith("\\\\"):
        raise RuntimeError(
            "Redis data dir must not be UNC/network path; "
            f"resolved_dir={result.resolved_dir} fs={result.fs_type}"
        )
    if result.fs_type.lower() != "ntfs":
        raise RuntimeError(
            "Redis data dir must resolve to NTFS fixed drive; "
            f"resolved_dir={result.resolved_dir} fs={result.fs_type}"
        )
    if not _is_fixed_drive(result.resolved_dir):
        raise RuntimeError(
            "Redis data dir must live on local fixed drive; "
            f"resolved_dir={result.resolved_dir} fs={result.fs_type}"
        )
    if result.appendonly_enabled and result.aof_total_bytes > result.aof_total_cap_bytes:
        raise RuntimeError(
            "Redis AOF total exceeds strict startup cap; "
            f"resolved_dir={result.resolved_dir} "
            f"base={result.aof_base_bytes} incr={result.aof_incr_bytes} "
            f"total={result.aof_total_bytes} cap={result.aof_total_cap_bytes}"
        )


def _parse_redis_config(conf_path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    for raw_line in conf_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        key, value = parts
        config[key.strip().lower()] = value.strip()
    return config


def _resolve_repo_path(repo: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else repo / candidate


def _nearest_existing_path(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def _filesystem_type(path: Path) -> str:
    if os.name != "nt":
        raise RuntimeError(f"Unable to resolve filesystem type for {path}: Windows-only runtime contract")

    root = _drive_root(path)
    volume_name = ctypes.create_unicode_buffer(261)
    fs_name = ctypes.create_unicode_buffer(261)
    serial = ctypes.c_uint32()
    max_component = ctypes.c_uint32()
    flags = ctypes.c_uint32()

    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root),
        volume_name,
        len(volume_name),
        ctypes.byref(serial),
        ctypes.byref(max_component),
        ctypes.byref(flags),
        fs_name,
        len(fs_name),
    )
    if ok == 0:
        raise RuntimeError(f"Unable to resolve filesystem type for {path}: GetVolumeInformationW failed for {root}")
    return fs_name.value


def _drive_root(path: Path) -> str:
    resolved = Path(path).resolve(strict=False)
    drive = resolved.drive
    if not drive:
        raise RuntimeError(f"Unable to resolve drive root for {path}")
    return f"{drive}\\"


def _is_fixed_drive(path: Path) -> bool:
    root = _drive_root(path)
    drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
    return drive_type == 3


def _aof_sizes(data_dir: Path, appendonly_enabled: bool, appendfilename: str) -> tuple[int, int]:
    if not appendonly_enabled:
        return 0, 0

    appendonly_dir = data_dir / "appendonlydir"
    manifest_path = appendonly_dir / f"{appendfilename}.manifest"
    if manifest_path.exists():
        return _aof_sizes_from_manifest(appendonly_dir, manifest_path)
    if appendonly_dir.is_dir():
        return _aof_sizes_from_directory(appendonly_dir)

    single_file = data_dir / appendfilename
    if single_file.exists():
        return single_file.stat().st_size, 0
    return 0, 0


def _aof_sizes_from_manifest(appendonly_dir: Path, manifest_path: Path) -> tuple[int, int]:
    base_bytes = 0
    incr_bytes = 0
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("file "):
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        file_name = parts[1]
        file_type = parts[5]
        file_path = appendonly_dir / file_name
        if not file_path.exists():
            continue
        size = file_path.stat().st_size
        if file_type == "b":
            base_bytes += size
        elif file_type == "i":
            incr_bytes += size
    return base_bytes, incr_bytes


def _aof_sizes_from_directory(appendonly_dir: Path) -> tuple[int, int]:
    base_bytes = 0
    incr_bytes = 0
    for file_path in appendonly_dir.iterdir():
        if not file_path.is_file() or file_path.suffix == ".manifest":
            continue
        size = file_path.stat().st_size
        if ".incr." in file_path.name:
            incr_bytes += size
        else:
            base_bytes += size
    return base_bytes, incr_bytes


def _format_gib(size_bytes: int) -> str:
    return f"{size_bytes / (1024 ** 3):.3f}GiB"

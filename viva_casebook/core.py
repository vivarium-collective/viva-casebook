"""build_core() — the shared workspace core the casebook's studies run against.

The casebook's whole method is model *sourcing*: a study reuses / composes /
build-news from existing modules, and a **reused module is inherited into this
one shared core** rather than run on a parallel module-specific core. That
inheritance is what makes "reuse" real — `build_core()` imports each reused
module and folds its processes + custom types into the core every study builds
its `Composite` against.

`process_bigraph.allocate_core()` auto-discovers processes/types from *installed
distributions* that depend on bigraph-schema. That covers this package's own
Process/Step classes only in a non-editable install, so we also register them
explicitly (idempotent) — a fresh scaffold with none is a clean no-op.
"""
from __future__ import annotations

import importlib
import pkgutil

from process_bigraph import Process, Step, allocate_core


def _iter_own_process_classes():
    """Yield (name, cls) for each Process/Step subclass defined in THIS package."""
    package_name = __package__
    if not package_name:
        return
    try:
        package = importlib.import_module(package_name)
    except Exception:
        return
    search_paths = getattr(package, "__path__", None)
    if search_paths is None:
        return
    seen = set()
    for module_info in pkgutil.iter_modules(search_paths, package_name + "."):
        try:
            module = importlib.import_module(module_info.name)
        except Exception:
            continue
        for attr_name in dir(module):
            obj = getattr(module, attr_name, None)
            if not isinstance(obj, type):
                continue
            if not issubclass(obj, (Process, Step)) or obj is Process or obj is Step:
                continue
            if not getattr(obj, "__module__", "").startswith(package_name):
                continue
            if obj.__name__ in seen:
                continue
            seen.add(obj.__name__)
            yield obj.__name__, obj


def register_workspace_processes(core):
    """Register this package's own Process/Step classes (idempotent)."""
    for name, cls in _iter_own_process_classes():
        if name not in core.link_registry:
            core.register_link(name, cls)
    return core


# ── Reused modules inherited into the shared workspace core ──────────────────
# Each entry is (import_name, register) where register(core, module) folds that
# module's processes + types into `core`. An absent module is skipped (e.g.
# viva-cpm's Rust wheel may not be built everywhere) so the core still builds;
# a registration error on an installed module is allowed to surface.
def _inherit_viva_munk(core, mod):
    # core_import(core) registers viva_munk's processes + pymunk types AND (its
    # own dependency) spatio-flux's types into the passed-in core.
    mod.core_import(core)


def _inherit_spatio_flux(core, mod):
    # Processes (DynamicFBA, …) are discovered by allocate_core once imported;
    # register_types adds spatio-flux's custom types (fields, bounds, particle…).
    importlib.import_module("spatio_flux.visualizations")  # fire viz Step discovery
    mod.register_types(core)


def _inherit_cpm(core, mod):
    # viva-cpm (dist pbg-cpm, import `cpm`) exposes no register hook and its
    # Rust-backed CPMProcess is not auto-discovered, so register it explicitly.
    from cpm.processes.cpm_process import CPMProcess
    if "CPMProcess" not in core.link_registry:
        core.register_link("CPMProcess", CPMProcess)


_REUSED_MODULES = (
    ("viva_munk", _inherit_viva_munk),
    ("spatio_flux", _inherit_spatio_flux),
    ("cpm", _inherit_cpm),
)


def inherit_reused_modules(core):
    """Fold each installed reused module's processes + types into `core`.

    A module that isn't installed is skipped; registration is idempotent."""
    for import_name, register in _REUSED_MODULES:
        try:
            mod = importlib.import_module(import_name)
        except ImportError:
            continue
        register(core, mod)
    return core


def build_core(core=None):
    """Return a process-bigraph core with the reused modules + this package's
    own processes registered. Studies must build their `Composite` against a
    core from here, not a bare `allocate_core()`."""
    if core is None:
        core = allocate_core()
    inherit_reused_modules(core)
    register_workspace_processes(core)
    return core

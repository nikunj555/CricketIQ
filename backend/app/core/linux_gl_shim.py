"""
Linux OpenGL ES / EGL Shim Loader.
Preloads libGLdispatch.so.0, libGLESv2.so.2, and libEGL.so.1 into process memory
on Linux environments (such as Render Native Python) where system mesa/libgles2
packages are not installed by the host OS.
"""
import sys
import os
import ctypes
import logging
from pathlib import Path

logger = logging.getLogger("cricketiq.gl_shim")

_preloaded = False

def preload_linux_gl_libraries() -> bool:
    """Preloads bundled OpenGL ES / EGL shared libraries on Linux x86_64.
    Returns True if on Linux and libraries were loaded (or already loaded).
    """
    global _preloaded
    if _preloaded:
        return True

    if not sys.platform.startswith("linux"):
        return False

    lib_dir = Path(__file__).resolve().parent.parent / "lib" / "linux_x86_64"
    if not lib_dir.exists():
        logger.warning(f"Bundled Linux library directory not found at: {lib_dir}")
        return False

    # Add to LD_LIBRARY_PATH environment variable so child processes / dlopen see it
    lib_dir_str = str(lib_dir)
    cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if lib_dir_str not in cur_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{lib_dir_str}:{cur_ld}" if cur_ld else lib_dir_str

    load_order = [
        "libGLdispatch.so.0",
        "libGLESv2.so.2",
        "libEGL.so.1"
    ]
    loaded_count = 0
    for lib_name in load_order:
        lib_path = lib_dir / lib_name
        if lib_path.exists():
            try:
                ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)
                logger.info(f"Successfully preloaded bundled Linux shared library: {lib_name}")
                loaded_count += 1
            except Exception as e:
                logger.warning(f"Could not preload {lib_name} from {lib_path}: {e}")

    _preloaded = (loaded_count > 0)
    return _preloaded

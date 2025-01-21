# Modified from Guido van Rossum's xreload.py to work with python 3.12+
# completely ignores 'kind' variable in _extract_code function
# works for purpose of ScopeFoundry, does not work for all cases

"""Alternative to reload().

This works by executing the module in a scratch namespace, and then
patching classes, methods and functions in place.  This avoids the
need to patch instances.  New objects are copied into the target
namespace.

Some of the many limitiations include:

- Global mutable objects other than classes are simply replaced, not patched

- Code using metaclasses is not handled correctly

- Code creating global singletons is not handled correctly

- Functions and methods using decorators (other than classmethod and
  staticmethod) is not handled correctly

- Renamings are not handled correctly

- Dependent modules are not reloaded

- Frozen modules and modules loaded from zip files aren't handled
  correctly

- Classes involving __slots__ are not handled correctly
"""

import importlib
from importlib import reload
import importlib.util
import inspect
import sys


CLASS_STATICS = frozenset(("__dict__", "__doc__", "__module__", "__weakref__"))


def xreload(mod, new_annotations=None):
    """Reload a module in place, updating classes, methods and functions.

    Args:
      mod: a module object

    Returns:
      The (updated) input object itself.
    """
    # pylint: disable=exec-used
    code = _extract_code(mod)
    if code is None:
        # Fall back to built-in reload()
        return reload(mod)
    # Execute the code.  We copy the module dict to a temporary; then
    # clear the module dict; then execute the new code in the module
    # dict; then swap things back and around.  This trick (due to
    # Glyph Lefkowitz) ensures that the (readonly) __globals__
    # attribute of methods and functions is set to the correct dict
    # object.
    modns = mod.__dict__
    tmpns = {
        "__name__": modns["__name__"],
        "__file__": modns["__file__"],
        "__doc__": modns["__doc__"],
    }
    if new_annotations:
        tmpns["__annotations__"] = new_annotations
    exec(code, tmpns)
    # Now we get to the hard part
    _update_scope(modns, tmpns)
    # Update attributes in place
    for name in set(modns) & set(tmpns):
        modns[name] = _update(modns[name], tmpns[name], mod.__name__)
    # Done!
    return mod


def _extract_code(mod):
    modname = mod.__name__
    if modname == "__main__":
        # print(mod.__dict__)
        # filename = mod._dh[0]
        # stream = open(mod._dh[0])
        raise ImportError(
            "reloading module __main__ currently not supported. Move Measrument/Hardware class to a separate file"
        )
    else:
        pkgname = None
        i = modname.rfind(".")
        if i >= 0:
            pkgname, modname = modname[:i], modname[i + 1 :]
        # Compute the search path
        if pkgname:
            # We're not reloading the package, only the module in it
            path = sys.modules[pkgname].__path__  # Search inside the package
        else:
            # Search the top-level module path
            path = None  # Make find_module() uses the default search path
        # Find the module; may raise ImportError
        spec = importlib.util.find_spec(modname, path)
    # kind = importlib.util.PY
    filename = spec.name
    stream = open(spec.origin)

    # Turn it into a code object
    try:
        # Is it Python source code or byte code read from a file?
        # if kind not in (importlib.PY_COMPILED, importlib.PY_SOURCE):
        #     return None
        source = stream.read().strip() + "\n"
        code = compile(source, filename, "exec")
        return code
    finally:
        if stream:
            stream.close()


def _update_scope(oldscope, newscope):
    oldnames = set(oldscope)
    newnames = set(newscope)
    # Add newly introduced names
    for name in newnames - oldnames:
        oldscope[name] = newscope[name]
    # Delete names that are no longer current
    for name in oldnames - newnames:
        if not name.startswith("__"):
            del oldscope[name]


def _update(oldobj, newobj, modname):
    """Update oldobj, if possible in place, with newobj.

    If oldobj is immutable, this simply returns newobj.

    Args:
      oldobj: the object to be updated
      newobj: the object used as the source for the update

    Returns:
      either oldobj, updated in place, or newobj.
    """
    # pylint: disable=too-many-return-statements
    if not isinstance(oldobj, type(newobj)):
        # Cop-out: if the type changed, give up
        return newobj

    if getattr(newobj, "__module__", None) != modname:
        # Do not update objects in-place that have been imported.
        # Just update their references.
        return newobj

    if inspect.isclass(newobj):
        return _update_class(oldobj, newobj, modname)
    if inspect.isfunction(newobj):
        return _update_function(oldobj, newobj, modname)
    # Not something we recognize, just give up
    return newobj


def _closure_changed(oldcl, newcl):
    old = -1 if oldcl is None else len(oldcl)
    new = -1 if newcl is None else len(newcl)
    if old != new:
        return True
    if old > 0 and new > 0:
        for i in range(old):
            same = oldcl[i] == newcl[i]
            if not same:
                return True
    return False


# All of the following functions have the same signature as _update()


def _update_function(oldfunc, newfunc, _):
    """Update a function object."""
    if _closure_changed(oldfunc.__closure__, newfunc.__closure__):
        raise ClosureChanged()
    oldfunc.__code__ = newfunc.__code__
    oldfunc.__defaults__ = newfunc.__defaults__
    _update_scope(oldfunc.__globals__, newfunc.__globals__)
    return oldfunc


def _update_class(oldclass, newclass, modname):
    """Update a class object."""
    olddict = oldclass.__dict__
    newdict = newclass.__dict__
    oldnames = set(olddict)
    newnames = set(newdict)
    for name in newnames - oldnames:
        setattr(oldclass, name, newdict[name])
    for name in oldnames - newnames:
        delattr(oldclass, name)
    for name in oldnames & newnames - CLASS_STATICS:
        try:
            new = getattr(newclass, name)
            if inspect.isfunction(new):
                _update_function(getattr(oldclass, name, None), new, modname)
            else:
                setattr(oldclass, name, new)
        except ClosureChanged:
            # If the closure changed, we need to replace the entire function
            setattr(oldclass, name, new)
    return oldclass


class ClosureChanged(Exception):
    pass

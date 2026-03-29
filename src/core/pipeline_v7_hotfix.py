from __future__ import annotations


def apply_pipeline_hotfix(V7PipelineClass):
    if not hasattr(V7PipelineClass, "_force_immediate_processing"):
        setattr(V7PipelineClass, "_force_immediate_processing", False)
    orig_init = getattr(V7PipelineClass, "__init__", None)

    def __init__(self, *a, **k):
        if orig_init is not None:
            orig_init(self, *a, **k)
        if not hasattr(self, "_force_immediate_processing"):
            self._force_immediate_processing = False

    V7PipelineClass.__init__ = __init__

    def __getstate__(self):
        st = dict(getattr(self, "__dict__", {}))
        st.setdefault("_force_immediate_processing", False)
        return st

    def __setstate__(self, state):
        self.__dict__.update(state)
        if "_force_immediate_processing" not in self.__dict__:
            self._force_immediate_processing = False

    V7PipelineClass.__getstate__ = __getstate__
    V7PipelineClass.__setstate__ = __setstate__
    orig_getattr = getattr(V7PipelineClass, "__getattr__", None)

    def __getattr__(self, name):
        if name == "_force_immediate_processing":
            setattr(self, name, False)
            return False
        if orig_getattr:
            return orig_getattr(self, name)
        raise AttributeError(name)

    V7PipelineClass.__getattr__ = __getattr__
    return V7PipelineClass

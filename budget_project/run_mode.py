import os

class RunMode(object):
    """Convenience class for run-time mode configuration.

    If 'mode' is set, it must be one of 'dev' (development), 'stag' (staging), or 'prod'
    (production).

    If mode is not set, the constructor attempts to set the mode from the run-time path to
    this file. If the path contains any of the aforementioned mode strings, set the mode
    accordingly. Otherwise, raise an exception.

    If 'debug_toolbar' is set to a non-null value, set the debug_toolbar property to that
    value.  Otherwise, set the debug_toolbar property to be true only if in development
    mode.
    """
    def __init__(self, mode=None, debug_toolbar=None):
        self.debug_toolbar = debug_toolbar
        self._project_path = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                           os.path.pardir))

        valid_modes = ('dev', 'stag', 'prod')
        if mode is None:
            for m in valid_modes:
                if m in self._project_path:
                    self.mode = m
                    break
            if self.mode not in valid_modes:
                raise RuntimeError("Can't determine mode from '{0}'".format(self._project_path))
        else:
            if mode not in valid_modes:
                raise RuntimeError("Mode not in '{0}'".format(valid_modes))
            self.mode = mode

        if self.debug_toolbar is None:
            self.debug_toolbar = self.dev

    @property
    def project_path(self):
        "Return top-level project path."
        return self._project_path

    def path_to(self, partial_path):
        "Join partial_path to top-level path and return result."
        return os.path.join(self._project_path, partial_path)

    @property
    def dev(self):
        "Running in development mode?"
        return self.mode == 'dev'

    @property
    def stag(self):
        "Running in staging mode?"
        return self.mode == 'stag'

    @property
    def prod(self):
        "Running in production mode?"
        return self.mode == 'prod'

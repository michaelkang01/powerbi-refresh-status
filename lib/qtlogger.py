import logging
import traceback


class QTLogger(logging.Logger):
    def __init__(self, name='root'):
        super().__init__(name=name)
        self.version = '1.1.2'
        self._exception_enabled = True

    @property
    def exception_enabled(self):
        return self._exception_enabled

    @exception_enabled.setter
    def exception_enabled(self, is_exception_enabled):
        self._exception_enabled = is_exception_enabled

    def error(self, msg, *args, **kwargs):
        if isinstance(msg, Exception) and self._exception_enabled:
            exc = traceback.TracebackException.from_exception(msg)
            message = (''.join(exc.format())).replace('"', '').replace('\n', ' || ')
        else:
            message = msg
        self._log(40, message, args, **kwargs)


def set_basic_config(logger: QTLogger, **kwargs):
    source = kwargs.get('source', '')

    msgformat = '{"timestamp": "%(asctime)s",' \
                '"level": "%(levelname)s",' \
                '"module": "%(name)s",' \
                '"message": "%(message)s",' \
                '"file": "%(filename)s",' \
                '"class": "%(funcName)s",' \
                '"lineNo": %(lineno)s,' \
                '"source": "' + source + '"' \
                                         '}'
    hndlr = logging.StreamHandler()
    frmt = logging.Formatter(fmt=msgformat)
    hndlr.setFormatter(frmt)
    logger.addHandler(hndlr)


def getLogger(name='root', **kwargs):
    lg = QTLogger(name)
    set_basic_config(lg, **kwargs)

    return lg

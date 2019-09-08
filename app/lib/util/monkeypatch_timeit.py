"""
/!\
Old monkeypatch works for python up to 3.4 but not 3.5+ as the _template_func function appears to have been removed in 3.5
https://stackoverflow.com/questions/24812253/how-can-i-capture-return-value-with-python-timeit-module

Monkeypatch the timeit module so that it returns a function result as well
as the time it took to execute the function. This is used to profile ticks
in production.
"""
import timeit

# OLD GRYPHON MONKEYPATCH (for python<3.4)
# def _template_func(setup, func):
#     """Create a timer function. Used if the "statement" is a callable."""
#     def inner(_it, _timer, _func=func):
#         setup()
#         _t0 = _timer()
#         for _i in _it:
#             retval = _func()
#         _t1 = _timer()
#         return _t1 - _t0, retval
#     return inner

# def monkeypatch_timeit():
#     timeit._template_func = _template_func

# NEW MONKEYPATCH (for python>3.5)
timeit.template = """
def inner(_it, _timer{init}):
    {setup}
    _t0 = _timer()
    for _i in _it:
        retval = {stmt}
    _t1 = _timer()
    return _t1 - _t0, retval
"""
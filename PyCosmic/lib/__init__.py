from .image import *
from .detCosmic import *
import copyreg


def _pickle_method(method):
	func_name = method.__func__.__name__
	obj = method.__self__
	cls = method.__self__.__class__
	if func_name.startswith('__') and not func_name.endswith('__'):
		cls_name = cls.__name__.lstrip('_')
	if cls_name:
		func_name = '_' + cls_name + func_name
	return _unpickle_method, (func_name, obj, cls)
    
def _unpickle_method(func_name, obj, cls):
	for cls in cls.mro():
		try:
			func = cls.__dict__[func_name]
		except KeyError:
			pass
		else:
			break
	return func.__get__(obj, cls)

copyreg.pickle(MethodType,_pickle_method, _unpickle_method)

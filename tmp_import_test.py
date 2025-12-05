import importlib, traceback

try:
    m = importlib.import_module('app.stability')
    print('imported app.stability')
    print('has push_snapshot:', hasattr(m, 'push_snapshot'))
    print('has get_buffer_status:', hasattr(m, 'get_buffer_status'))
    print('dir:', [n for n in dir(m) if not n.startswith('_')])
except Exception:
    traceback.print_exc()

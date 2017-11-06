import re
import platform

import cffi


CPPLIB = 'MSVCRT' if platform.system() == 'Windows' else 'c++'
CPPARGS = {
    'Linux': ['-std=c++14', '-stdlib=libstdc++'],
    'Darwin': ['-std=c++14', '-stdlib=libc++'],
    'Windows': ['/std:c++14', '/TP']
}[platform.system()]


with open('include/calculate.h', 'r') as handler:
    header = handler.read()

header = re.sub(r'#ifdef __cplusplus(.|\n)*?(#else\n|#endif\n)', '', header)
header = re.sub(r'#.*\n', '', header)
header = re.sub(r'.*\\\n', '', header)
header = re.sub(r' +\)\(.*\)\n', '', header)
header = re.sub(r'\n\)\n', '\n', header)
header = re.sub(r'\n\)\n', '\n', header)
header = '\n'.join([
    re.sub(r'^((?:calculate|void|size_t|int|double).+)$', r'extern \1', line)
    for line in header.split('\n')
])

header += r'''
extern "Python+C" double _calculate_callback1(void*, double);
extern "Python+C" double _calculate_callback2(void*, double, double);
extern "Python+C" double _calculate_callback3(void*, double, double, double);
'''

ffi = cffi.FFI()
ffi.cdef(header)
ffi.set_source(
    'calculate._calculate',
    r'#include "calculate.h"',
    sources=[
        'source/expression.cpp',
        'source/handler.cpp',
        'source/lexer.cpp',
        'source/parser.cpp',
        'source/symbol.cpp'
    ],
    libraries=[CPPLIB],
    include_dirs=['include'],
    extra_compile_args=CPPARGS,
    source_extension='.cpp'
)


if __name__ == '__main__':
    ffi.compile(verbose=True)

# utils for OpenGL-based stuff (used for display of Map and Minimap)

# imports ###################################################################

import ctypes
import numpy as np

from OpenGL.GL import (
    GL_TRUE, GL_FALSE,
    glGetString, GL_VERSION,
    glCreateShader, glShaderSource, glCompileShader,
    glCreateProgram, glAttachShader, glLinkProgram,
    glGetShaderiv, glGetShaderInfoLog,
    glGetProgramiv, glGetProgramInfoLog,
    glGetUniformLocation, glUseProgram,
    GL_COMPILE_STATUS, GL_LINK_STATUS,
    glUniform1fv, glUniform2fv, glUniform3fv, glUniform4fv,
    glUniform1iv, glUniformMatrix3fv,
)


# utils #####################################################################

def get_opengl_version():
    """
    return opengl version.

    """
    version = glGetString(GL_VERSION).decode()
    version = version.split()[0]
    version = map(int, version.split("."))
    return tuple(version)


def create_shader(shader_type, source, **kwargs):
    """
    compile a shader.

    """
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)
    if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
        raise RuntimeError(glGetShaderInfoLog(shader))
    return shader


def create_program(*shaders):
    """
    link a program.

    """
    program = glCreateProgram()
    for shader in shaders:
        glAttachShader(program, shader)
    glLinkProgram(program)
    if glGetProgramiv(program, GL_LINK_STATUS) != GL_TRUE:
        raise RuntimeError(glGetProgramInfoLog(program))
    return program


_c_types = {
    float:      ctypes.c_float,
    np.float32: ctypes.c_float,
    np.float64: ctypes.c_float,
    int:        ctypes.c_int,
    bool:       ctypes.c_int,
}

_Uniforms = {
    (1, ctypes.c_float): glUniform1fv,
    (2, ctypes.c_float): glUniform2fv,
    (3, ctypes.c_float): glUniform3fv,
    (4, ctypes.c_float): glUniform4fv,
    (9, ctypes.c_float): lambda location, n, values:
        glUniformMatrix3fv(location, n, GL_FALSE, values),
    (1, ctypes.c_int):   glUniform1iv,
}


def set_uniform(program, uniform, *values):
    """
    dispatch uniform setting according to value type.

    """
    v0, n = values[0], len(values)
    if isinstance(v0, tuple):
        l, t = len(v0), _c_types[type(v0[0])]
        values = (t * (l*n))(*(u for value in values for u in value))
    else:
        l, t = 1, _c_types[type(v0)]
        values = (t * n)(*values)
    glUseProgram(program)
    _Uniforms[l, t](glGetUniformLocation(program, uniform), n, values)
    glUseProgram(0)


# exports ###################################################################

__all__ = [
    'get_opengl_version',
    'create_shader',
    'create_program',
    'set_uniform',
]

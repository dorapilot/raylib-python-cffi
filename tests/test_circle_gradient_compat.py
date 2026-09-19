"""Exercise pyray's gradient binding without opening a graphics device."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from cffi import FFI


class NativeFunctions(SimpleNamespace):
    def __dir__(self):
        return ['DrawCircleGradient']


def load_binding(signature):
    ffi = FFI()
    ffi.cdef("""
        typedef struct Vector2 { float x, y; } Vector2;
        typedef struct Color { unsigned char r, g, b, a; } Color;
    """)
    calls = []

    def record(*args):
        calls.append(tuple(
            (arg.r, arg.g, arg.b, arg.a) if hasattr(arg, 'r') else
            (arg.x, arg.y) if hasattr(arg, 'x') else arg
            for arg in args
        ))

    callback = ffi.callback(signature, record)
    native = ffi.cast(signature, callback)
    raylib = ModuleType('raylib')
    raylib.ffi = ffi
    raylib.rl = NativeFunctions(DrawCircleGradient=native)
    modules = {'raylib': raylib}
    for name in ('colors', 'defines', 'enums'):
        modules[f'raylib.{name}'] = ModuleType(f'raylib.{name}')
    spec = importlib.util.spec_from_file_location(
        'pyray_gradient_test', Path(__file__).parents[1] / 'pyray' / '__init__.py')
    module = importlib.util.module_from_spec(spec)
    modules[spec.name] = module
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    # Keep the callback alive for the lifetime of the binding.
    module._test_callback = callback
    return module, calls


class CircleGradientCompatibilityTest(unittest.TestCase):
    def test_vector_center_on_five_argument_native(self):
        pr, calls = load_binding('void(*)(int, int, float, Color, Color)')
        pr.draw_circle_gradient(pr.Vector2(12.75, -9.5), 81.5,
                                pr.Color(1, 2, 3, 128), pr.Color(4, 5, 6, 0))
        self.assertEqual(calls, [(12, -9, 81.5, (1, 2, 3, 128), (4, 5, 6, 0))])

    def test_integer_centers_keep_five_argument_behavior(self):
        pr, calls = load_binding('void(*)(int, int, float, Color, Color)')
        inner, outer = pr.Color(10, 20, 30, 40), pr.Color(50, 60, 70, 80)
        pr.draw_circle_gradient(-7, 19, 4.5, inner, outer)
        self.assertEqual(calls, [(-7, 19, 4.5, (10, 20, 30, 40), (50, 60, 70, 80))])
        with self.assertRaises(TypeError):
            pr.draw_circle_gradient(1.5, 19, 4.5, inner, outer)
        self.assertEqual(len(calls), 1)

    def test_four_argument_native_preserves_fractional_center(self):
        pr, calls = load_binding('void(*)(Vector2, float, Color, Color)')
        pr.draw_circle_gradient(pr.Vector2(12.75, -9.5), 81.5,
                                pr.Color(1, 2, 3, 128), pr.Color(4, 5, 6, 0))
        self.assertEqual(calls, [((12.75, -9.5), 81.5, (1, 2, 3, 128), (4, 5, 6, 0))])

    def test_malformed_arity_still_fails(self):
        pr, calls = load_binding('void(*)(int, int, float, Color, Color)')
        with self.assertRaisesRegex(RuntimeError, 'function requires 5 arguments but you supplied 3'):
            pr.draw_circle_gradient(1, 2, 3)
        with self.assertRaises(TypeError):
            pr.draw_circle_gradient(1, 2, 3, pr.Color(0, 0, 0, 0), pr.Color(0, 0, 0, 0), 6)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()

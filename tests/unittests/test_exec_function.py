import unittest

from sequencer.item_types.exec_function import (
    MAX_ARGUMENT_STRING_LENGTH,
    parse_arguments,
    resolve_function,
)


class ParseArgumentsTest(unittest.TestCase):

    def test_parses_positional_and_keyword_arguments(self):
        args, kwargs = parse_arguments("1, 'text', enabled=True, values=[2, 3]")

        self.assertEqual(args, (1, "text"))
        self.assertEqual(kwargs, {"enabled": True, "values": [2, 3]})

    def test_parses_argument_unpacking(self):
        args, kwargs = parse_arguments("*[1, 2], **{'enabled': True}")

        self.assertEqual(args, (1, 2))
        self.assertEqual(kwargs, {"enabled": True})

    def test_rejects_non_literal_values(self):
        with self.assertRaises(ValueError):
            parse_arguments("value")

    def test_rejects_duplicate_keyword_arguments(self):
        with self.assertRaises(TypeError):
            parse_arguments("value=1, **{'value': 2}")

    def test_rejects_argument_string_over_limit(self):
        argument_string = " " * (MAX_ARGUMENT_STRING_LENGTH + 1)

        with self.assertRaisesRegex(ValueError, "character limit"):
            parse_arguments(argument_string)

    def test_resolves_only_allowlisted_application_functions(self):
        class App:
            name = "test_app"

            def allowed(self):
                return "called"

            def not_allowed(self):
                return "not called"

        app = App()
        allowed = resolve_function(app, "test_app.allowed", ["test_app.allowed"])

        self.assertEqual(allowed(), "called")
        with self.assertRaisesRegex(ValueError, "allowed function list"):
            resolve_function(app, "test_app.not_allowed", ["test_app.allowed"])

    def test_resolves_allowlisted_measurement_functions(self):
        class Measurement:
            name = "test_measurement"

            def allowed(self):
                return "called"

        class App:
            measurements = {"test_measurement": Measurement()}
            hardware = {}

        function = resolve_function(
            App(),
            "measurements.test_measurement.allowed",
            ["measurements.test_measurement.allowed"],
        )

        self.assertEqual(function(), "called")


if __name__ == "__main__":
    unittest.main()

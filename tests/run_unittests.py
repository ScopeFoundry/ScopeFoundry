import unittest

from ScopeFoundry.tests.unittests.test_get_settings import GetSettingsTest
from ScopeFoundry.tests.unittests.test_lq_choice_list import ChoiceListTest
from ScopeFoundry.tests.unittests.test_settings_io import SettingsIOTest
from ScopeFoundry.tests.unittests.test_lq_connection import LQConnectionTest
from ScopeFoundry.tests.unittests.test_lq_range import LQRangeTest
from ScopeFoundry.tests.unittests.test_analyze_nb import AnalyzeNBTest
from ScopeFoundry.tests.unittests.test_operations import TestOperations


# following also require visual inspection - run individual files
from ScopeFoundry.tests.hw_connect_failure_test import AppTest
from ScopeFoundry.tests.nested_measurement_test import NestMeasureTestAppTest
from ScopeFoundry.tests.quickbar_test import QuickbarTest

if __name__ == "__main__":
    unittest.main()

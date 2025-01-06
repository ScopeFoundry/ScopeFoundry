import unittest

from ScopeFoundry.tests.unittests.get_settings import GetSettingsTest
from ScopeFoundry.tests.unittests.lq_choice_list_test import ChoiceListTest
from ScopeFoundry.tests.unittests.settings_io_test import SettingsIOTest
from ScopeFoundry.tests.unittests.lq_connection_test import LQConnectionTest
from ScopeFoundry.tests.unittests.lq_range_test import LQRangeTest
from ScopeFoundry.tests.unittests.analyze_nb_test import AnalyzeNBTest
from ScopeFoundry.tests.unittests.test_operations import TestOperations


# following also require visual inspection - run individual files
from ScopeFoundry.tests.hw_connect_failure_test import TestFailHW
from ScopeFoundry.tests.nested_measurement_test import NestMeasureTestAppTest
from ScopeFoundry.tests.quickbar_test import QuickbarTest

if __name__ == "__main__":
    unittest.main()

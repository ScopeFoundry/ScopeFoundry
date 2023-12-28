'''
Created on Sep 17, 2021

@author: Benedikt Ursprung
'''
import logging
import sys

from ScopeFoundry.base_app import BaseMicroscopeApp

level = logging.DEBUG
logging.basicConfig(level=level)


class App(BaseMicroscopeApp):

    name = 'sequencer_test_app'

    def setup(self):

        from ScopeFoundry.sequencer import Sequencer, SweepSequencer
        self.add_measurement(Sequencer(self))
        self.add_measurement(SweepSequencer(self))

if __name__ == '__main__':
    app = App(sys.argv)
    sys.exit(app.exec_())

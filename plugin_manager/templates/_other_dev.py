'''
Created on $DATE_PRETTY

@author: $AUTHORS
'''

# GOAL OF THIS FILE IS TO HANDLE LOW LEVEL COMMUNICATION
# SHOULD BE INDEPENDENT OF ANY SCOPEFOUNDRY FUNCTIONALITY.
# RUN THIS FILE TO TEST CONNECTION, TESTING COMMANDS WHILE CHECK main()




class $DEV_CLASS_NAME:

    def __init__(self, debug=False):
        self.debug = debug
        # TODO ESTABLISH CONNECTION HERE

    def write_property_x(self, value):
        raise NotImplementedError
        # USE CONNECTION TO WRITE A VALUE

    def read_property_x(self):
        raise NotImplementedError
        # USE CONNECTION TO READ A VALUE AND RETURN

    def read_data(self):
        # NOTE read_data is a too generic function name
        raise NotImplementedError
        # USE CONNECTION TO READ A VALUE AND RETURN



if __name__ == '__main__':
    print('start')
    dev = $DEV_CLASS_NAME(debug=True)
    print(dev.read_property_x())
    # print(dev.read_data())

    print('done')

import sys


def invalid_input():
    print("----------------------------------------------------------")
    print("Invalid command. Please use one of the following commands:")
    print("----------------------------------------------------------")
    print_cmds()


def print_cmds():
    print("python -m ScopeFoundry init")
    print("python -m ScopeFoundry ipynb")
    print("python -m ScopeFoundry tools")
    print("python -m ScopeFoundry new_hardware")
    print("python -m ScopeFoundry new_measurement")
    print("python -m ScopeFoundry publish_hardware")


if __name__ == "__main__":

    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if cmd is None:
        invalid_input()

    if cmd in ("init", "new_app"):
        from ScopeFoundry.tools.features.new_app import new_app

        run_str = new_app()

        print("")
        print("Or use one of the following commmands to extent your app")
        print("----------------------------------------------------------")
        print_cmds()
        print("----------------------------------------------------------")
        print("")
        print("To run your app, use the following command:")
        print(run_str)

    elif cmd in ("ipynb",):
        from ScopeFoundry.h5_analyze_with_ipynb import analyze_with_ipynb

        analyze_with_ipynb()
    elif cmd in ("tools",):
        from ScopeFoundry.tools.app import start_app

        start_app()
    elif cmd in ("new_hw", "new_hardware"):
        from ScopeFoundry.tools.app import start_app

        start_app("new hardware")
    elif cmd in ("new_mm", "new_measurement"):
        from ScopeFoundry.tools.features.new_measurement import main

        main()

    elif cmd in ("publish_hw", "publish_hardware"):
        from ScopeFoundry.tools.app import start_app

        start_app("publish HW on GitHub")

    else:
        invalid_input()

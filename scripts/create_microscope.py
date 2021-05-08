import argparse


def main():
    
    parser = argparse.ArgumentParser(description='Create a blank ScopeFoundry Microscope.')

    parser.add_argument('name', type=str,
                    help='name of microscope')
    
    parser.add_argument('--dir', required=False, help="Directory to create microscope, defaults to name")
    
    parser.add_argument('--git-init', action='store_true', 
                            required=False, help='Initialize a git repository inside microscope directory')
    

    args = parser.parse_args()
    print(args)
    print("-->", args['name'])
    
    
if __name__ == "__main__":
    main()

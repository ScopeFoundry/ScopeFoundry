import subprocess

import argparse


def main():
    
    parser = argparse.ArgumentParser(description='Grab a Hardware Component from GitHub and place it in ScopeFoundryHW using git subtree add/pull.')

    parser.add_argument('name', type=str,
                    help='name of hardware')
    
    parser.add_argument('action', help='add or pull')
        
    parser.add_argument('--squash', action='store_true', 
                            required=False, help='')
    

    args = parser.parse_args()
    print(args)
    print("-->", args['name'])
    
    
if __name__ == "__main__":
    main()

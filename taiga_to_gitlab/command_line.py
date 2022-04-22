import json
import argparse


def main():
    parser = argparse.ArgumentParser(description='Import a taiga export to gitlab')
    parser.add_argument("taiga_json_path")
    args = parser.parse_args()
    taiga_data = json.load(open(args.taiga_json_path, 'rb'))
    print(taiga_data["name"])

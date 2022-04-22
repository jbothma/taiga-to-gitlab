import json
import argparse

# project
#   user_stories:
#     - subject
#       description
#       history:
#         - diff - object of fields that changed


# class Member:
#     def __init__(self, object):
#         self.user = object["user"]
#         self.email = object["email"]
#
#
# class AttachedFile:
#     def __init__(self, object):
#         self.data = object["data"]
#         self.name = object["name"]
#
#
# class Attachment:
#     def __init__(self, object):
#         self.owner = object["owner"]
#         self.attached_file = AttachedFile(object["attached_file"])
#         self.name = object["name"]
#         self.created_date = object["created_date"]
#         self.modified_date = object["modified_date"]
#         self.sha1 = object["sha1"]
#         self.size = object["size"]
#
#
#
# class UserStory:
#     def __init__(self, object):
#         attachments = [Attachment(a) for a in object["attachments"]]
#         #history = [HistoryItem(h) for h in ovject["history"]]

# for each story
# - create issue
# - for each history item
#   - create issue note

def main():
    parser = argparse.ArgumentParser(description='Import a taiga export to gitlab')
    parser.add_argument("taiga_json_path")
    args = parser.parse_args()
    taiga_data = json.load(open(args.taiga_json_path, 'rb'))
    print(taiga_data["name"])

    for story in taiga_data["user_stories"]:
        print(f'  {story["subject"]}')

        for update in story["history"]:
            print(f'    {update["created_at"][:19]} [{", ".join(update["diff"].keys())}] {update["comment"]}')

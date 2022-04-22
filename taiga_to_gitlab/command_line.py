import json
import argparse
import requests
from urllib.parse import quote

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
    parser.add_argument("import_config_path")
    parser.add_argument("taiga_json_path")
    parser.add_argument("gitlab_token")
    args = parser.parse_args()

    import_config = json.load(open(args.import_config_path, 'rb'))
    taiga_data = json.load(open(args.taiga_json_path, 'rb'))

    session = requests.Session()
    session.headers.update({"PRIVATE-TOKEN": args.gitlab_token})

    project_path_encoded = quote(import_config["project_path"], safe="")
    for story in taiga_data["user_stories"]:
        print(f'  {story["subject"]}')
        description = story["description"]
        description = description.replace("\n", "\n\n")

        labels = import_config["status_mapping"][story["status"]]
        close = False
        if labels == "Closed":
            labels = ""
            close = True

        issue = {
            "description": description,
            "labels": labels,
            "title": story["subject"],
        }
        r = session.post(
            f"https://gitlab.com/api/v4/projects/{project_path_encoded}/issues",
            data=issue
        )
        r.raise_for_status()
        created_issue = r.json()
        iid = created_issue["iid"]
        print(f'   iid={iid}')

        if close:
            issue = {
                "state_event": "close",
                "updated_at": story["finish_date"],
            }
            r = session.put(
                f"https://gitlab.com/api/v4/projects/{project_path_encoded}/issues/{iid}",
                data=issue
            )
            if r.status_code != 200:
                print(r.text)
            r.raise_for_status()


        for update in story["history"]:
            print(f'    {update["created_at"][:19]} [{", ".join(update["diff"].keys())}] {update["comment"]}')

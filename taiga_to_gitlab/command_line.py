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
#     - replace #\d+ with # \1 to stop accidental references to stories
# - for each history item
#   - if it's a snapshot, skip
#     else:
#       - create issue note

# history items:
#   type 1: comment and or diff;
#   type 2: snapshot - always first history element - no comment, no diff


class Importer:
    def __init__(self, import_config_path, taiga_json_path, gitlab_token):
        self.import_config = json.load(open(import_config_path, 'rb'))
        self.taiga_data = json.load(open(taiga_json_path, 'rb'))

        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": gitlab_token})

        self.project_path_encoded = quote(self.import_config["project_path"], safe="")

    def get_issue(self, taiga_ref):
        url = (f"https://gitlab.com/api/v4"
               f"/projects/{self.project_path_encoded}/search"
               f"?scope=issues&search=\"taiga-story-ref-{taiga_ref}\"")
        r = self.session.get(url)
        r.raise_for_status()
        projects = r.json()
        if len(projects) > 1:
            raise Exception(f"Expected 0 or 1 but got {len(projects)} for {url}")
        elif len(projects) == 1:
            return projects[0]
        else:
            return None

    def create_issue(self, story, story_ref, labels):
        description = story["description"]
        description = description.replace("\n", "\n\n")
        description = f"{description}\n\ntaiga-story-ref-{story_ref}"

        issue = {
            "description": description,
            "labels": labels,
            "title": story["subject"],
        }
        r = self.session.post(
            f"https://gitlab.com/api/v4/projects/{self.project_path_encoded}/issues",
            data=issue
        )
        r.raise_for_status()
        return r.json()

    def close_issue(self, iid, finish_date):
        issue = {
            "state_event": "close",
            "updated_at": finish_date,
        }
        r = self.session.put(
            f"https://gitlab.com/api/v4/projects/{self.project_path_encoded}/issues/{iid}",
            data=issue
        )
        if r.status_code != 200:
            print(r.text)
            r.raise_for_status()

    def handle_user_story(self, story):
        story_ref = story["ref"]
        print(f'  {story_ref} {story["subject"]}')

        labels = self.import_config["status_mapping"][story["status"]]
        close = False
        if labels == "Closed":
            labels = ""
            close = True

        issue = self.get_issue(story_ref)
        created = False
        if issue:
            print("fStory {story_ref} exists as issue {issue['iid']}")
        else:
            created = True
            issue = self.create_issue(story, story_ref, labels)

        iid = issue["iid"]
        print(f'iid={iid}')

        if close and issue["state"] != "closed":
            self.close_issue(iid, story["finish_date"])

        for update in story["history"]:
            print(f'    {update["created_at"][:19]} [{", ".join(update["diff"].keys())}] {update["comment"]}')

    def import_project(self):
        for story in self.taiga_data["user_stories"]:
            self.handle_user_story(story)


def main():
    parser = argparse.ArgumentParser(description='Import a taiga export to gitlab')
    parser.add_argument("import_config_path")
    parser.add_argument("taiga_json_path")
    parser.add_argument("gitlab_token")
    args = parser.parse_args()

    importer = Importer(args.import_config_path, args.taiga_json_path, args.gitlab_token)
    importer.import_project()

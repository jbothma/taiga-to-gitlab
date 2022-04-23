import json
import argparse
import requests
from urllib.parse import quote
from csv import DictReader, DictWriter
from io import BytesIO
from base64 import b64decode
from difflib import unified_diff

# project
#   user_stories:
#     - subject
#       description
#       history:
#         - diff - object of fields that changed
#       attachments:
#         - created_date
#           modified_date
#           description
#           name
#           owner



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
    def __init__(self, import_config_path, taiga_json_path, progress_file_path, gitlab_token, only_ref):
        self.import_config = json.load(open(import_config_path, 'rb'))
        self.taiga_data = json.load(open(taiga_json_path, 'rb'))
        self.only_ref = only_ref

        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": gitlab_token})


        self.project_path_encoded = quote(self.import_config["project_path"], safe="")

        self.story_issue_mapping = dict()
        try:
            with open(progress_file_path, 'r') as self.progress_file:
                reader = DictReader(self.progress_file)
                for row in reader:
                    self.story_issue_mapping[int(row["taiga_ref"])] = int(row["gitlab_iid"])
            mapping_existed = True
        except FileNotFoundError:
            mapping_existed = False

        self.progress_file = open(progress_file_path, 'a')
        self.writer = DictWriter(self.progress_file, fieldnames=["taiga_ref", "gitlab_iid"])
        if not mapping_existed:
            self.writer.writeheader()
            self.progress_file.flush()

        self.user_cache = dict()

    def get_user_id(self, username):
        if username not in self.user_cache:
            print(f"Looking up uncached username {username}")
            url = f"https://gitlab.com/api/v4/users?username={username}"
            r = self.session.get(url)
            r.raise_for_status()
            users = r.json()
            if len(users) > 1:
                raise Exception(f"Expected 0 or 1 but found {len(users)} for {url}")
            elif len(users) == 1:
                self.user_cache[username] = users[0]["id"]
        return self.user_cache[username]

    def get_user_str_for_mentioning(self, taiga_email):
        gitlab_username = self.import_config["user_mapping"].get(taiga_email, None)
        if gitlab_username:
            return f"@{gitlab_username}"
        else:
            return taiga_email

    def create_issue(self, story, labels):
        description = story["description"]
        description = description.replace("\n", "\n\n")

        issue = {
            "description": description,
            "labels": labels,
            "title": story["subject"],
            "created_at": story["created_date"],
        }

        mapped_username = self.import_config["user_mapping"].get(story["assigned_to"], None)
        print(f"Mapped user {story['assigned_to']} to {mapped_username}")
        if mapped_username:
            issue["assignee_id"] = self.get_user_id(mapped_username)
            issue["assignee_ids"] = [issue["assignee_id"]]
            print(f"Found {issue['assignee_id']} for {mapped_username}")

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

    def handle_attachment(self, iid, attachment):
        upload_url = f"https://gitlab.com/api/v4/projects/{self.project_path_encoded}/uploads"
        file_bytes = b64decode(attachment["attached_file"]["data"])
        in_mem_file = BytesIO(file_bytes)
        files = {"file": (attachment["name"], in_mem_file)}
        r = self.session.post(upload_url, files=files)
        r.raise_for_status()
        gitlab_file = r.json()

        user_str = self.get_user_str_for_mentioning(attachment["owner"])

        body = (f"Attachment {attachment['name']} owned by {user_str}\n\n"
                f"{gitlab_file['markdown']}\n\n")
        if attachment["description"]:
            body += f"{attachment['description']}\n\n"
        body += (f"Created {attachment['created_date']}\n\n"
                 f"Last updated {attachment['modified_date']}")

        note = {
            "body": body,
            "creted_at": attachment["created_date"],
        }

        note_url = f"https://gitlab.com/api/v4/projects/{self.project_path_encoded}/issues/{iid}/notes"
        r = self.session.post(note_url, data=note)
        r.raise_for_status()


    def handle_event(self, iid, event):
        taiga_user = event["user"][0] or event["user"][1]
        user_str = self.get_user_str_for_mentioning(taiga_user)
        body = f"At {event['created_at']}, {user_str}:\n\n"
        if event['comment']:
            body += f"Commented: {event['comment']}\n\n"
        for key, value in event["diff"].items():
            if key == "description":
                description1 = value[0].split("\n")
                description2 = value[1].split("\n")
                diff = "\n\n".join(unified_diff(description1, description2, lineterm=""))
                body += f"Updated `description` with\n\n```\n{diff}\n```\n\n"
            elif key == "description_html":
                pass
            elif key == "attachments":
                body += "Updated attachments\n\n"
            else:
                body += f"Changed `{key}` from `{value[0]}` to `{value[1]}`\n\n"
        note = {
            "body": body,
            "creted_at": event["created_at"],
        }

        note_url = f"https://gitlab.com/api/v4/projects/{self.project_path_encoded}/issues/{iid}/notes"
        r = self.session.post(note_url, data=note)
        r.raise_for_status()

    def handle_user_story(self, story):
        story_ref = story["ref"]
        print(f'  {story_ref} {story["subject"]}')

        labels = self.import_config["status_mapping"][story["status"]]
        close = False
        if labels == "Closed":
            labels = ""
            close = True

        created = None
        if story_ref in self.story_issue_mapping:
            print(f"Story {story_ref} exists as issue {self.story_issue_mapping[story_ref]}")
            return

        issue = self.create_issue(story, labels)
        iid = issue["iid"]
        self.story_issue_mapping[story_ref] = iid
        self.writer.writerow({"taiga_ref": story_ref, "gitlab_iid": iid,})
        self.progress_file.flush()

        print(f'iid={iid}')

        if close and issue["state"] != "closed":
            self.close_issue(iid, story["finish_date"])

        for attachment in story["attachments"]:
            self.handle_attachment(iid, attachment)

        for event in story["history"]:
            self.handle_event(iid, event)

    def import_project(self):
        for story in self.taiga_data["user_stories"]:
            if not self.only_ref or story["ref"] == self.only_ref:
                self.handle_user_story(story)


def main():
    parser = argparse.ArgumentParser(description='Import a taiga export to gitlab')
    parser.add_argument("import_config_path")
    parser.add_argument("taiga_json_path")
    parser.add_argument("progress_file_path")
    parser.add_argument("gitlab_token")
    parser.add_argument(
        "--only-ref",
        default=None,
        type=int,
        help=("Specify a user story ref to skip all other user stories. Helpful "
              "for debugging using just one relevant story."),
    )
    args = parser.parse_args()

    importer = Importer(
        args.import_config_path,
        args.taiga_json_path,
        args.progress_file_path,
        args.gitlab_token,
        args.only_ref
    )
    importer.import_project()

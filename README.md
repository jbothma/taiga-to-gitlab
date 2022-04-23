# taiga-to-gitlab

Import a taiga.io dump to gitlab


## Running the importer

You'll need

- A taiga JSON dump file
- An import config file
- A gitlab project
- Members you'd like to map added to the gitlab project

- A gitlab personal authentication token

## Usage

Install dependencies:

    poetry install

Run the command:

    poetry run taiga2gitlab ../myproj.json ../taiga--myproj-123-456-789.json ../myproj.csv mytoken


## Handling errors

The gitlab API occasionally returns server errors without explanation. This importer stores a progress file to skip stories it has already imported, and resume importing where it left off.

For that reason, always use the same progress file for the same project until it is fully imported. Don't use the progress file from another project.

1. Delete the latest created issue - find its numeric gitlab Issue ID (iid) in the log
2. Delete the issue's row from the progress file
3. Rerun the script with the same arguments

The script will skip all the previously-completed stories and restart the one it probably only partially completed, which you had just deleted. It will usually continue successfully from there.


## Config file

- Project path is the gitlab username or group slug, and the project slug with a / in between as you'd see in your address bar when viewing your project pages in gitlab
- Status mapping maps status in Taiga to a label in gitlab, except for Closed which results in an issue being marked closed.
- User mapping maps email addresses of users in Taiga to gitlab usernames.

```json
{
  "project_path": "awesome-group52/myproj",
  "status_mapping": {
    "New": "New",
    "Ready": "Ready for Work",
    "In progress": "In progress",
    "Ready for test": "Review",
    "Done": "Closed",
    "Archived": "Closed"
  },
  "user_mapping": {
    "bob@dave.com": "bobdave",
    "fred@bloggs.com": "fredbloggs"
  }
}
```


## Help

```
usage: taiga2gitlab [-h] [--only-ref ONLY_REF] import_config_path taiga_json_path progress_file_path gitlab_token

Import a taiga export to gitlab

positional arguments:
  import_config_path
  taiga_json_path
  progress_file_path
  gitlab_token

options:
  -h, --help           show this help message and exit
  --only-ref ONLY_REF  Specify a user story ref to skip all other user stories. Helpful for debugging using just one relevant story.
```

-----

Initially built by [JD Bothma](https://github.com/jbothma) funded by [Digital Engineering](https://github.com/digital-engineering)